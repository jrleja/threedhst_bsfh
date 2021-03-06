from prospect.models import model_setup
import os, prosp_dutils, hickle, sys, time
import numpy as np
import argparse
from copy import deepcopy
from prospector_io import load_prospector_data, create_prosp_filename
import prosp_dynesty_plots
from dynesty.plotting import _quantile as weighted_quantile
from prospect.models import sedmodel

def set_sfh_time_vector(chain,model):
    """if parameterized, calculate linearly in 100 steps from t=0 to t=tage
    if nonparameterized, calculate at bin edges.
    """

    nt = 100
    if 'tage' in model.theta_labels():
        tage = chain[model.theta_index['tage'],:].max()
        t = np.linspace(0,tage,num=nt)
    elif 'agebins' in model.params:
        in_years = 10**model.params['agebins']/1e9
        t = np.concatenate((np.ravel(in_years)*0.9999, np.ravel(in_years)*1.001))
        t.sort()
        t = t[1:-1] # remove older than oldest bin, younger than youngest bin
        t = np.clip(t,1e-3,np.inf) # nothing younger than 1 Myr!
        t = np.unique(t)
    else:
        sys.exit('ERROR: not sure how to set up the time array here!')
    return t

def calc_extra_quantities(res, sps, obs, noise=None,ncalc=3000, shorten_spec=True, measure_abslines=False,
                          measure_herschel=False,measure_restframe_properties=True,**kwargs):
    """calculate extra quantities: star formation history, stellar mass, spectra, photometry, etc
    shorten_spec: if on, return only the 50th / 84th / 16th percentiles. else return all spectra.
    """

    # calculate maxprob
    # and ensure that maxprob stored is the same as calculated now 
    # don't recalculate lnprobability after we fix MassMet
    amax = res['lnprobability'].argmax()
    current_maxprob = prosp_dutils.test_likelihood(sps, res['model'], res['obs'], noise,
                                                   res['chain'][amax], 
                                                   res['run_params']['param_file'],
                                                   res['run_params'])
    print 'Best-fit lnprob currently: {0}'.format(float(current_maxprob))
    print 'Best-fit lnprob during sampling: {0}'.format(res['lnprobability'][amax])

    # randomly choose from the chain, weighted by dynesty weights
    # make sure the first one is the maximum probability model (so we're cheating a bit!)
    # don't do replacement, we can use weights to rebuild PDFs
    nsample = res['chain'].shape[0]
    #res['weights'][-2] = 0.000001
    #res['weights'] = res['weights']/res['weights'].sum()
    sample_idx = np.random.choice(np.arange(nsample), size=ncalc, p=res['weights'], replace=False)
    if amax in sample_idx:
        sample_idx[sample_idx == amax] = sample_idx[0]
    sample_idx[0] = amax
    print "we are measuring {0}% of the weights".format(res['weights'][sample_idx].sum()/res['weights'].sum()*100)

    # compact creation of outputs
    eout = {
            'thetas':{},
            'extras':{},
            'sfh':{},
            'obs':{},
            'sample_idx':sample_idx,
            'weights':res['weights'][sample_idx],
            'zred': float(res['model'].params['zred'])
            }
    fmt = {'chain':np.zeros(shape=ncalc),'q50':0.0,'q84':0.0,'q16':0.0}

    # thetas
    parnames = res['model'].theta_labels()
    for i, p in enumerate(parnames):  
        q50, q16, q84 = weighted_quantile(res['chain'][:,i], np.array([0.5, 0.16, 0.84]), weights=res['weights'])
        eout['thetas'][p] = {'q50': q50, 'q16': q16, 'q84': q84}

    # extras
    extra_parnames = ['avg_age','lwa_rband','lwa_lbol','half_time','sfr_100','ssfr_100','ssfr_30','sfr_30','sfr_300', 'ssfr_300',\
                      'stellar_mass','lir','luv','lmir','lbol','luv_young','lir_young']
    if 'fagn' in parnames:
        extra_parnames += ['l_agn', 'fmir', 'luv_agn', 'lir_agn']
    for p in extra_parnames: eout['extras'][p] = deepcopy(fmt)

    # sfh
    tvec = set_sfh_time_vector(res['chain'],res['model'])
    eout['sfh']['t'] = tvec
    eout['sfh']['sfh'] = np.zeros(shape=(ncalc,tvec.shape[0]))

    # observables
    eout['obs']['lam_obs'] = sps.wavelengths
    if res['obs'].get('wavelength',None) is not None:
        eout['obs']['lam_obs'] = res['obs']['wavelength']
    eout['obs']['spec'] = np.zeros(shape=(ncalc,eout['obs']['lam_obs'].shape[0]))
    eout['obs']['mags'] = np.zeros(shape=(ncalc,len(res['obs']['filters'])))
    eout['obs']['uvj'] = np.zeros(shape=(ncalc,3))
    eout['obs']['rf'] = np.zeros(shape=(ncalc,3))
    elines = ['H beta 4861', 'H alpha 6563','Br gamma 21657','Pa alpha 18752','Pa beta 12819']
    eout['obs']['elines'] = {key: {'ew': deepcopy(fmt), 'flux': deepcopy(fmt)} for key in elines}
    eout['obs']['dn4000'] = deepcopy(fmt)
    if not res['model'].params.get('marginalize_elines',False):
        res['model'].params['nebemlineinspec'] = True
    if measure_abslines:
        abslines = ['halpha_wide', 'halpha_narrow', 'hbeta', 'hdelta_wide', 'hdelta_narrow']
        eout['obs']['abslines'] = {key+'_ew': deepcopy(fmt) for key in abslines}

    if measure_herschel:
        hfilters = ['herschel_pacs_70','herschel_pacs_100','herschel_pacs_160','herschel_spire_250','herschel_spire_350','herschel_spire_500']
        eout['obs']['herschel'] = {'mags':np.zeros(shape=(ncalc,6)),'filter_names':hfilters}
        from sedpy.observate import load_filters
        fobs = {'filters': load_filters(hfilters), 'wavelength': None}

    # generate model w/o dependencies for young star contribution
    model_params = deepcopy(res['model'].config_list)
    for j in range(len(model_params)):
        if model_params[j]['name'] == 'mass':
            print model_params[j]['name']
            model_params[j].pop('depends_on', None)
    nodep_model = sedmodel.SedModel(model_params)

    '''
    # rohan special
    eout['obs']['lyc'] = {'mags':np.zeros(shape=(ncalc,3))} 
    eout['obs']['lyc_dusty'] = {'mags':np.zeros(shape=(ncalc,3))} #this one isolates the effect of IGM on L1500, L900 keeping dust+neb emission
    from sedpy.observate import load_filters
    filters = ['wfc3_uvis_f275w','wfc3_uvis_f336w','wfc3_uvis_f606w'] #throw in F275W because we have z~2.4 sources for whom LyC is in F275W
    fobs = {'filters': load_filters(filters), 'wavelength': None}
    '''
    # sample in the posterior
    for jj,sidx in enumerate(sample_idx):

        # bookkeepping
        t1 = time.time()

        thetas = res['chain'][sidx,:]
        eout['obs']['spec'][jj,:],eout['obs']['mags'][jj,:],sm = res['model'].mean_model(thetas, res['obs'], sps=sps, sigma=sigma)

        '''
        import matplotlib.pyplot as plt
        plt.plot(res['model']._outwave, res['obs']['spectrum'],color='red',lw=2)
        for i in range(1,5):

            # model call
            thetas = res['chain'][-i,:]

            # no bullshit here
            if noise is not None:
                res['model'].set_parameters(thetas)
                noise[0].update(**res['model'].params)
                vectors = {"unc": obs['unc']}
                sigma = noise[0].construct_covariance(**vectors)
            else:
                sigma = None
            print res['model']._ln_eline_penalty
            current_maxprob = prosp_dutils.test_likelihood(sps, res['model'], res['obs'], noise, thetas, 
                                                           res['run_params']['param_file'],
                                                           res['run_params'])
            print current_maxprob, res['lnlikelihood'][-i]
            plt.plot(res['model']._outwave, eout['obs']['spec'][jj,:])

        import pdb
        pdb.set_trace()
        '''

        # interpolate spectrum from rest-frame to observed wavelength, and add (1+z) factor
        #eout['obs']['spec'][jj,:] = np.interp(sps.wavelengths, sps.wavelengths*(1+res['model'].params['zred']), spec)

        # calculate SFH-based quantities
        sfh_params = prosp_dutils.find_sfh_params(res['model'],thetas,res['obs'],sps,sm=sm)
        eout['extras']['stellar_mass']['chain'][jj] = sfh_params['mass']
        eout['sfh']['sfh'][jj,:] = prosp_dutils.return_full_sfh(eout['sfh']['t'], sfh_params)
        eout['extras']['half_time']['chain'][jj] = prosp_dutils.halfmass_assembly_time(sfh_params)
        eout['extras']['sfr_100']['chain'][jj] = prosp_dutils.calculate_sfr(sfh_params, 0.1,  minsfr=-np.inf, maxsfr=np.inf)
        eout['extras']['ssfr_100']['chain'][jj] = eout['extras']['sfr_100']['chain'][jj].squeeze() / eout['extras']['stellar_mass']['chain'][jj].squeeze()
        eout['extras']['sfr_30']['chain'][jj] = prosp_dutils.calculate_sfr(sfh_params, 0.03,  minsfr=-np.inf, maxsfr=np.inf)
        eout['extras']['ssfr_30']['chain'][jj] = eout['extras']['sfr_30']['chain'][jj].squeeze() / eout['extras']['stellar_mass']['chain'][jj].squeeze()
        eout['extras']['sfr_300']['chain'][jj] = prosp_dutils.calculate_sfr(sfh_params, 0.3,  minsfr=-np.inf, maxsfr=np.inf)
        eout['extras']['ssfr_300']['chain'][jj] = eout['extras']['sfr_300']['chain'][jj].squeeze() / eout['extras']['stellar_mass']['chain'][jj].squeeze()

        # calculate AGN parameters if necessary
        if 'fagn' in parnames:
            eout['extras']['l_agn']['chain'][jj] = prosp_dutils.measure_agn_luminosity(thetas[parnames.index('fagn')],sps,sfh_params['mformed'])

        # lbol
        eout['extras']['lbol']['chain'][jj] = prosp_dutils.measure_lbol(sps,sfh_params['mformed'])

        # measure from rest-frame spectrum
        t2 = time.time()
        if measure_restframe_properties:
            props = prosp_dutils.measure_restframe_properties(sps, thetas=thetas, model=res['model'], measure_uvj=True, abslines=measure_abslines, 
                                                              measure_ir=True, measure_luv=True, measure_mir=True, emlines=elines,measure_rf=True,
                                                              obs=obs)
            eout['extras']['lir']['chain'][jj] = props['lir']
            eout['extras']['luv']['chain'][jj] = props['luv']
            eout['extras']['lmir']['chain'][jj] = props['lmir']
            eout['obs']['dn4000']['chain'][jj] = props['dn4000']
            eout['obs']['uvj'][jj,:] = props['uvj']
            eout['obs']['rf'][jj,:] = props['rf']

            for e in elines: 
                eout['obs']['elines'][e]['flux']['chain'][jj] = props['emlines'][e]['flux']
                eout['obs']['elines'][e]['ew']['chain'][jj] = props['emlines'][e]['eqw']

            if measure_abslines:
                for a in abslines: eout['obs']['abslines'][a+'_ew']['chain'][jj] = props['abslines'][a]['eqw']

            nagn_thetas = deepcopy(thetas)
            if 'fagn' in parnames:
                nagn_thetas[parnames.index('fagn')] = 0.0
                props = prosp_dutils.measure_restframe_properties(sps, thetas=nagn_thetas, model=res['model'], 
                                                                  measure_mir=True,measure_ir = True, measure_luv = True)
                eout['extras']['fmir']['chain'][jj] = (eout['extras']['lmir']['chain'][jj]-props['lmir'])/eout['extras']['lmir']['chain'][jj]
                eout['extras']['luv_agn']['chain'][jj] = props['luv']
                eout['extras']['lir_agn']['chain'][jj] = props['lir']

            # isolate young star contribution
            nodep_model.params['mass'] = np.zeros_like(res['model'].params['mass'])
            nodep_model.params['mass'][:2] = res['model'].params['mass'][:2]
            try:
                out = prosp_dutils.measure_restframe_properties(sps, model = nodep_model, thetas = nagn_thetas, measure_ir=True, measure_luv=True)
            except AssertionError: # this fails sometimes if SFR(0-100) Myr is near zero
                out = {'luv': 0.0, 'lir': 0.0}
            eout['extras']['luv_young']['chain'][jj] = out['luv']
            eout['extras']['lir_young']['chain'][jj] = out['lir']

        '''
        # rohan special
        # returns mags w/o IGM absorption keeping all else same
        ndust_thetas = deepcopy(thetas)
        res['model'].params['add_igm_absorption'] = np.array([False])
        _,eout['obs']['lyc_dusty']['mags'][jj,:],_ = res['model'].mean_model(ndust_thetas, fobs, sps=sps)
        ndust_thetas[parnames.index('dust1_fraction')] = 0.0 
        ndust_thetas[parnames.index('dust2')] = 0.0 
        res['model'].params['add_neb_emission'] = np.array([False])
        res['model'].params['add_neb_continuum'] = np.array([False])
        _,eout['obs']['lyc']['mags'][jj,:],_ = res['model'].mean_model(ndust_thetas, fobs, sps=sps)
        '''
        # ages
        eout['extras']['avg_age']['chain'][jj], eout['extras']['lwa_lbol']['chain'][jj], \
        eout['extras']['lwa_rband']['chain'][jj] = prosp_dutils.all_ages(thetas,res['model'],sps,obs)

        if measure_herschel:
            _,eout['obs']['herschel']['mags'][jj,:],__ = res['model'].mean_model(thetas, fobs, sps=sps)

        t3 = time.time()
        print('loop {0} took {1}s ({2}s for absorption+emission)'.format(jj,t3 - t1,t3 - t2))

    # calculate percentiles from chain
    for p in eout['extras'].keys():
        q50, q16, q84 = weighted_quantile(eout['extras'][p]['chain'], np.array([0.5, 0.16, 0.84]), weights=eout['weights'])
        for q,qstr in zip([q50,q16,q84],['q50','q16','q84']): eout['extras'][p][qstr] = q
    
    q50, q16, q84 = weighted_quantile(eout['obs']['dn4000']['chain'], np.array([0.5, 0.16, 0.84]), weights=eout['weights'])
    for q,qstr in zip([q50,q16,q84],['q50','q16','q84']): eout['obs']['dn4000'][qstr] = q

    for key1 in eout['obs']['elines'].keys():
        for key2 in ['ew','flux']:
            q50, q16, q84 = weighted_quantile(eout['obs']['elines'][key1][key2]['chain'], np.array([0.5, 0.16, 0.84]), weights=eout['weights'])
            for q,qstr in zip([q50,q16,q84],['q50','q16','q84']): eout['obs']['elines'][key1][key2][qstr] = q

    if measure_abslines:
        for key in eout['obs']['abslines'].keys():
            q50, q16, q84 = weighted_quantile(eout['obs']['abslines'][key]['chain'], np.array([0.5, 0.16, 0.84]), weights=eout['weights'])
            for q,qstr in zip([q50,q16,q84],['q50','q16','q84']): eout['obs']['abslines'][key][qstr] = q

    if measure_herschel:
        nfilts = eout['obs']['herschel']['mags'].shape[1]
        qtiles = ['q50','q16','q84','q02.5','q97.5']
        for quant in qtiles: eout['obs']['herschel'][quant] = np.zeros(nfilts)
        for i in range(nfilts):
            for q in qtiles: 
                eout['obs']['herschel'][q][i] = weighted_quantile(eout['obs']['herschel']['mags'][:,i], \
                                                    np.array([float(q[1:])/100]), weights=eout['weights'])[0]
    # for storage purposes
    if shorten_spec:
        spec_pdf = np.zeros(shape=(eout['obs']['lam_obs'].shape[0],3))
        for jj in xrange(spec_pdf.shape[0]): spec_pdf[jj,:] = weighted_quantile(eout['obs']['spec'][:,jj], np.array([0.5, 0.16, 0.84]), weights=eout['weights'])
        eout['obs']['spec'] = {'q50':spec_pdf[:,0],'q16':spec_pdf[:,1],'q84':spec_pdf[:,2]}

    return eout

def pprocessing_new(param_name, outfile, plot_outfolder=None, plot=True, sps=None, overwrite=True,
                    shorten_spec=False,**kwargs):
    
    # load parameter file, results
    pfile = model_setup.import_module_from_file(param_name)
    res, _, _, eout = load_prospector_data(outfile, postprocessing=True)

    # if we don't specify a plot destination, make one up
    if plot_outfolder is None:
        plot_outfolder = os.getenv('APPS')+'/prospector_alpha/plots/'+outfile.split('/')[-2]+'/'
    if not os.path.isdir(plot_outfolder):
        os.makedirs(plot_outfolder)

    # catch exceptions
    if res is None:
        print 'there are no sampling results! returning.'
        return
    if (not overwrite) & (eout is not None):
        print 'post-processing file already exists! returning.'
        return

    # make filenames local...
    objname = outfile.split('/')[-1]
    print 'Performing post-processing on ' + objname
    for key in res['run_params']:
        if type(res['run_params'][key]) == unicode:
            if 'prospector_alpha' in res['run_params'][key]:
                res['run_params'][key] = os.getenv('APPS')+'/prospector_alpha'+res['run_params'][key].split('prospector_alpha')[-1]
    if sps is None:
        sps = pfile.build_sps(**res['run_params'])
    obs = res['obs']
    res['model'] = pfile.build_model(**res['run_params'])
    noise = pfile.build_noise(**res['run_params'])

    # recast to float64
    for key in res.keys():
        if type(res[key]) == type(np.array([])):
            if res[key].dtype == np.dtype(np.float128):
                res[key] = res[key].astype(np.float64)

    # renormalize weights
    res['weights'] = res['weights'] / res['weights'].sum()

    # sample from chain
    extra_output = calc_extra_quantities(res,sps,obs,noise=noise,shorten_spec=shorten_spec,**kwargs)
    
    # create post-processing name, dump info
    _, postname = create_prosp_filename(outfile,postprocessing=True)
    hickle.dump(extra_output,open(postname, "w"))

    # make standard plots
    if plot:
        prosp_dynesty_plots.make_all_plots(filebase=outfile,outfolder=plot_outfolder)


def post_processing(param_name, objname=None, runname = None, overwrite=True, obj_outfile=None,
                    plot_outfolder=None, plot=True, sps=None, **kwargs):
    """Driver. Loads output, runs post-processing routine.
    overwrite=False will return immediately if post-processing file already exists.
    if runname is specified, we can pass in parameter file for run with outputs at location runname
    kwargs are passed to calc_extra_quantities
    """

    # bookkeeping: where are we coming from and where are we going?
    pfile = model_setup.import_module_from_file(param_name)
    run_outfile = pfile.run_params['outfile']

    if obj_outfile is None:
        if runname is None:
            runname = run_outfile.split('/')[-2]
            obj_outfile = "/".join(run_outfile.split('/')[:-1]) + '/' + objname
        else:
            obj_outfile = "/".join(run_outfile.split('/')[:-2]) + '/' + runname + '/' + objname

        # account for unique td_huge storage situation
        if (runname == 'td_huge') | (runname == 'td_new') | (runname == 'td_delta'):
            field = obj_outfile.split('/')[-1].split('_')[0]
            obj_outfile = "/".join(obj_outfile.split('/')[:-1])+'/'+field+'/'+obj_outfile.split('/')[-1]  

    if runname is None:
        runname = obj_outfile.split('/')[-2]

    if plot_outfolder is None:
        plot_outfolder = os.getenv('APPS')+'/prospector_alpha/plots/'+runname+'/'

    # check for output folder, create if necessary
    if not os.path.isdir(plot_outfolder):
        os.makedirs(plot_outfolder)

    # I/O
    res, powell_results, _, eout = load_prospector_data(obj_outfile,hdf5=True,postprocessing=True)

    if res is None:
        print 'there are no sampling results! returning.'
        return
    if (not overwrite) & (eout is not None):
        print 'post-processing file already exists! returning.'
        return

    # make filenames local...
    print 'Performing post-processing on ' + objname
    for key in res['run_params']:
        if type(res['run_params'][key]) == unicode:
            if 'prospector_alpha' in res['run_params'][key]:
                res['run_params'][key] = os.getenv('APPS')+'/prospector_alpha'+res['run_params'][key].split('prospector_alpha')[-1]
    if sps is None:
        sps = pfile.load_sps(**res['run_params'])
    obs = res['obs']
    res['model'] = pfile.load_model(**res['run_params'])

    # recast to float64
    for key in res.keys():
        if type(res[key]) == type(np.array([])):
            if res[key].dtype == np.dtype(np.float128):
                res[key] = res[key].astype(np.float64)

    # renormalize weights
    res['weights'] = res['weights'] / res['weights'].sum()

    # sample from chain
    extra_output = calc_extra_quantities(res,sps,obs,**kwargs)

    # create post-processing name, dump info
    _, extra_filename = create_prosp_filename(obj_outfile,postprocessing=True)
    hickle.dump(extra_output,open(extra_filename, "w"))

    # make standard plots
    if plot:
        prosp_dynesty_plots.make_all_plots(filebase=obj_outfile,outfolder=plot_outfolder)


def do_all(param_name=None,runname=None,ids=None,**kwargs):
    try:
        ids = np.genfromtxt('/Users/joel/code/python/prospector_alpha/data/3dhst/'+runname+'.ids',dtype=str)
    except:
        import glob
        ids = [f.split('/')[-1].split('_')[0] for f in glob.glob('/Users/joel/code/python/prospector_alpha/results/'+runname+'/*h5')]
    for id in ids:
        post_processing(param_name, objname=id, **kwargs)
        
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False

if __name__ == "__main__":

    ### don't create keyword if not passed in!
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument('parfile', type=str)
    parser.add_argument('--objname')
    parser.add_argument('--ncalc',type=int)
    parser.add_argument('--overwrite',type=str2bool)
    parser.add_argument('--shorten_spec',type=str2bool)
    parser.add_argument('--runname', type=str)
    parser.add_argument('--obj_outfile', type=str)
    parser.add_argument('--plot',type=str2bool)
    parser.add_argument('--measure_herschel',type=str2bool)
    parser.add_argument('--measure_abslines',type=str2bool)
    parser.add_argument('--new_prosp',type=str2bool)

    args = vars(parser.parse_args())
    kwargs = {}
    for key in args.keys(): kwargs[key] = args[key]

    print kwargs
    if kwargs.get('new_prosp',False):
        pprocessing_new(kwargs['parfile'], kwargs['obj_outfile'],**kwargs)
    else:
        post_processing(kwargs['parfile'],**kwargs)

