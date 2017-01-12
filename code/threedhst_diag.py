import numpy as np
import matplotlib.pyplot as plt
import corner, os, math, copy, threed_dutils
from prospect.io import read_results
import matplotlib.image as mpimg
import matplotlib as mpl
from astropy.cosmology import WMAP9
import fsps
from matplotlib.ticker import MaxNLocator
from prospect.models import model_setup
import copy
from magphys_plot_pref import jLogFormatter
from brown_io import load_prospector_data

plt.ioff() # don't pop up a window for each plot

obs_color = '#545454'

tiny_number = 1e-3
big_number = 1e90
dpi = 150

minorFormatter = jLogFormatter(base=10, labelOnlyBase=False)
majorFormatter = jLogFormatter(base=10, labelOnlyBase=True)

def subcorner(sample_results,  sps, model, extra_output,
                outname=None, showpars=None,
                truths=None, extents=None,
                powell_results=None,
                **kwargs):
    """
    Make a corner plot of the (thinned, latter) samples of the posterior
    parameter space.  Optionally make the plot only for a supplied subset
    of the parameters.
    """

    # pull out the parameter names and flatten the thinned chains
    parnames = np.array(sample_results['model'].theta_labels())
    flatchain = threed_dutils.chop_chain(sample_results['chain'])

    # restrict to parameters you want to show
    if showpars is not None:
        ind_show = np.array([p in showpars for p in parnames], dtype= bool)
        flatchain = flatchain[:,ind_show]
        truths = truths[ind_show]
        parnames= parnames[ind_show]

    # plot truths
    if truths is not None:
        ptruths = [truths['plot_truths'][truths['parnames'][ii] == parnames][0] if truths['parnames'][ii] in parnames \
                   else None \
                   for ii in xrange(len(truths['plot_truths']))]
    else:
        ptruths = None

    fig = corner.corner(flatchain, labels = parnames,
                        quantiles=[0.16, 0.5, 0.84], verbose = False,
                        truths = ptruths, range = extents, truth_color='red',
                        show_titles = True, **kwargs)

    fig = add_to_corner(fig, sample_results, extra_output, sps, model, truths=truths, powell_results=powell_results)
    if outname is not None:
        fig.savefig('{0}.corner.png'.format(outname))
        plt.close(fig)
    else:
        return fig


def add_to_corner(fig, sample_results, extra_output, sps, model,truths=None,maxprob=True,powell_results=None):

    '''
    adds in posterior distributions for 'select' parameters
    if we have truths, list them as text
    '''
	
    plotquant = extra_output['extras'].get('flatchain',None)
    plotname  = extra_output['extras'].get('parnames',None)

    to_show = ['half_time','ssfr_100','sfr_100','stellar_mass']
    ptitle = [r't$_{\mathrm{half}}$ [Gyr]',r'log(sSFR) (100 Myr) [yr$^{-1}$]',
              r'log(SFR) (100 Myr) [M$_{\odot}$ yr$^{-1}$]',r'log(M$_*$) [M$_{\odot}$]']

    showing = np.array([x in to_show for x in plotname])

    # extra text
    scale    = len(extra_output['quantiles']['parnames'])
    ttop     = 0.88-0.02*(12-scale)
    fs       = 24-(12-scale)
    
    if truths is not None:
        parnames = np.append(truths['parnames'],'lnprob')
        tvals    = np.append(truths['plot_truths'],truths['truthprob'])

        plt.figtext(0.73, ttop, 'truths',weight='bold',
                       horizontalalignment='right',fontsize=fs)
        for kk in xrange(len(tvals)):
            plt.figtext(0.73, ttop-0.02*(kk+1), parnames[kk]+'='+"{:.2f}".format(tvals[kk]),
                       horizontalalignment='right',fontsize=fs)

        # add in extras
        etruths = truths['extra_truths']
        eparnames = truths['extra_parnames']
        txtcounter = 1
        for nn in xrange(len(eparnames)):
            if eparnames[nn] in to_show:
                fmt = "{:.2f}"
                if 'sfr' in eparnames[nn]:
                    etruths[nn] = 10**etruths[nn]
                if 'ssfr' in eparnames[nn] or 'totmass' in eparnames[nn]:
                    fmt = '{0:.1e}'

                plt.figtext(0.73, ttop-0.02*(kk+txtcounter+1), eparnames[nn]+'='+fmt.format(etruths[nn]),
                           horizontalalignment='right',fontsize=fs)
                txtcounter+=1

        tvals    = np.append(tvals, etruths)
        parnames = np.append(parnames, eparnames)

    # show maximum probability
    if maxprob:
        maxprob_parnames = np.append(extra_output['quantiles']['parnames'],'lnprob')
        plt.figtext(0.75, ttop, 'pmax',weight='bold',
                       horizontalalignment='left',fontsize=fs)
        for kk in xrange(len(maxprob_parnames)):
            if maxprob_parnames[kk] == 'mass':
               yplot = np.log10(extra_output['bfit']['maxprob_params'][kk])
            elif maxprob_parnames[kk] == 'lnprob':
                yplot = float(extra_output['bfit']['maxprob'])
            else:
                yplot = extra_output['bfit']['maxprob_params'][kk]

            # add parameter names if not covered by truths
            if truths is None:
            	plt.figtext(0.8, ttop-0.02*(kk+1), maxprob_parnames[kk]+'='+"{:.2f}".format(yplot),
                       horizontalalignment='right',fontsize=fs)
            else:
           		plt.figtext(0.75, ttop-0.02*(kk+1), "{:.2f}".format(yplot),
                       horizontalalignment='left',fontsize=fs)

    # show burn-in results, if we have them
    try: 
	    burn_params = np.append(sample_results['post_burnin_center'],sample_results['post_burnin_prob'])
	    burn_names = np.append(sample_results['model'].theta_labels(), 'lnprobability')

	    plt.figtext(0.82, ttop, 'burn-in',weight='bold',
	                   horizontalalignment='left',fontsize=fs)

	    for kk in xrange(len(burn_names)):
	        if burn_names[kk] == 'mass':
	           yplot = np.log10(burn_params[kk])
	        else:
	            yplot = burn_params[kk]

	        plt.figtext(0.82, ttop-0.02*(kk+1), "{:.2f}".format(yplot),
	                   horizontalalignment='left',fontsize=fs)
    except KeyError:
    	pass

    # show powell results
    if powell_results:
        best = np.argmin([p.fun for p in powell_results])
        powell_params = np.append(powell_results[best].x,-1*powell_results[best]['fun'])
        powell_names = np.append(extra_output['quantiles']['parnames'],'lnprob')

        plt.figtext(0.89, ttop, 'powell',weight='bold',
                       horizontalalignment='left',fontsize=fs)

        for kk in xrange(len(powell_names)):
            if powell_names[kk] == 'mass':
               yplot = np.log10(powell_params[kk])
            else:
                yplot = powell_params[kk]

            plt.figtext(0.89, ttop-0.02*(kk+1), "{:.2f}".format(yplot),
                       horizontalalignment='left',fontsize=fs)


    #### create my own axes here
    # size them using size of other windows
    axis_size = fig.get_axes()[0].get_position().size
    xs, ys = 0.4, 0.82
    xdelta, ydelta = axis_size[0]*1.4, axis_size[1]*1.7
    plotloc = 0

    for jj in xrange(len(plotname)):

		if showing[jj] == 0:
		    continue

		ax = fig.add_axes([xs+(plotloc % 2)*xdelta, ys+(plotloc>1)*ydelta, axis_size[0], axis_size[1]])
		plotloc+=1

		if plotname[jj] == 'half_time':
			plot = plotquant[:,jj]
		else:
			plot = np.log10(plotquant[:,jj])

		# Plot the histograms.
		n, b, p = ax.hist(plot, bins=50,
		                  histtype="step",color='k',
		                  range=[np.min(plot),np.max(plot)])

		# plot quantiles
		qvalues = np.log10([extra_output['extras']['q16'][jj],
				            extra_output['extras']['q50'][jj],
				            extra_output['extras']['q84'][jj]])

		if plotname[jj] == 'half_time':
			qvalues = 10**qvalues

		for q in qvalues:
			ax.axvline(q, ls="dashed", color='k')

		# display quantiles
		q_m = qvalues[1]-qvalues[0]
		q_p = qvalues[2]-qvalues[1]

		# format quantile display
		fmt = "{{0:{0}}}".format(".2f").format
		title = r"${{{0}}}_{{-{1}}}^{{+{2}}}$"
		title = title.format(fmt(qvalues[1]), fmt(q_m), fmt(q_p))
		ax.set_title(title)
		ax.set_xlabel(ptitle[to_show.index(plotname[jj])])

		# axes
		# set min/max
		ax.set_xlim(np.percentile(plot,0.5),
					np.percentile(plot,99.5))
		ax.set_ylim(0, 1.1 * np.max(n))
		ax.set_yticklabels([])
		ax.xaxis.set_major_locator(MaxNLocator(5))
		[l.set_rotation(45) for l in ax.get_xticklabels()]

		# truths
		if truths is not None:
		    if plotname[jj] in parnames:
		        plottruth = tvals[parnames == plotname[jj]]
		        ax.axvline(x=plottruth,color='r')

    return fig

def add_sfh_plot(exout,fig,ax_loc=None,
				 main_color=None,tmin=0.01,
	             truths=None,text_size=1,
	             ax_inset=None):
	
	'''
	add a small SFH plot at ax_loc
	truths: also plot truths
	text_size: multiply font size by this, to accomodate larger/smaller figures
	'''

	# set up plotting
	if ax_inset is None:
		if fig is None:
			ax_inset = ax_loc
		else:
			ax_inset = fig.add_axes(ax_loc,zorder=32)
	axfontsize=4*text_size

	xmin, ymin = np.inf, np.inf
	xmax, ymax = -np.inf, -np.inf
	for i, extra_output in enumerate(exout):
		
		#### load SFH
		t = extra_output['extras']['t_sfh']
		perc = np.zeros(shape=(len(t),3))
		for jj in xrange(len(t)): perc[jj,:] = np.percentile(extra_output['extras']['sfh'][jj,:],[16.0,50.0,84.0])

		#### plot SFH
		ax_inset.plot(t, perc[:,1],'-',color=main_color[i])
		ax_inset.fill_between(t, perc[:,0], perc[:,2], color=main_color[i], alpha=0.3)

		#### update plot ranges
		xmin = np.min([xmin,t.min()])
		xmax = np.max([xmax,t.max()])
		ymin = np.min([ymin,perc.min()])
		ymax = np.max([ymax,perc.max()])

	##### truths (THIS IS TRASH RIGHT NOW)
	if truths is not None:
		
		# FIND A NEW WAY THAT DOESN'T REQUIRE AN SPS
		# sfh_params_truth = threed_dutils.find_sfh_params(sample_results['model'],truths['truths'],sample_results['obs'],sps)
		true_sfh = threed_dutils.return_full_sfh(t, sfh_params_truth)

		ax_inset.plot(t, true_sfh,'-',color='blue')
		ax_inset.text(0.92,0.32, 'truth',transform = ax_inset.transAxes,color='blue',fontsize=axfontsize*1.4,ha='right')

	#### labels, format, scales !
	if tmin:
		xmin = tmin

	axlim_sfh=[xmax, xmin, ymin*.7, ymax*1.4]
	ax_inset.axis(axlim_sfh)

	ax_inset.set_ylabel(r'SFR [M$_{\odot}$/yr]',fontsize=axfontsize,weight='bold',labelpad=3)
	ax_inset.set_xlabel('t [Gyr]',fontsize=axfontsize,weight='bold',labelpad=2)
	
	for tick in ax_inset.xaxis.get_major_ticks(): tick.label.set_fontsize(axfontsize) 
	ax_inset.set_xscale('log',nonposx='clip',subsx=([1]))

	for tick in ax_inset.yaxis.get_major_ticks(): tick.label.set_fontsize(axfontsize) 
	ax_inset.set_yscale('log',nonposy='clip',subsy=(1,3))

def plot_sfh_fast(tau,tage,mass,tuniv=None):

	'''
	version of plot_sfh, but only for FAST outputs
	this means no chain sampling, and simple tau rather than delayed tau models
	if we specify tuniv, return instead (tuniv-t)
	'''
	
	t=np.linspace(0,tage,num=50)
	sfr = np.exp(-t/tau)
	sfr_int = mass/np.sum(sfr * (t[1]-t[0])*1e9)  # poor man's integral, integrate f*yrs
	sfr = sfr * sfr_int

	if tuniv:
		t = tuniv-t
		t = t[::-1]

	return t,sfr

def return_extent(sample_results):    
    
	'''
	sets plot range for chain plot and corner plot for each parameter
	'''
    
	# set range
	extents = []
	parnames = np.array(sample_results['model'].theta_labels())
	for ii in xrange(len(parnames)):
		
		# set min/max
		extent = [np.percentile(sample_results['chain'][:,:,ii],0.5),
		          np.percentile(sample_results['chain'][:,:,ii],99.5)]

		# is the chain stuck at one point? if so, set the range equal to param*0.8,param*1.2
		# else check if we butting up against the prior? if so, extend by 10%
		priors = [f['prior_args'] for f in sample_results['model'].config_list if f['name'] == parnames[ii]]

		# check for multiple stellar populations
		if len(priors) == 0:
			priors = [f['prior_args'] for f in sample_results['model'].config_list if f['name'] == parnames[ii][:-2]][0]
			
			# separate priors for each component?
			if len(np.atleast_1d(priors['mini'])) > 1:
				mini = priors['mini'][int(parnames[ii][-1])-1]
				maxi = priors['maxi'][int(parnames[ii][-1])-1]
			else:
				mini = priors['mini']
				maxi = priors['maxi']
		
		elif len(priors) == 1:
			priors = priors[0]
			mini = priors['mini']
			maxi = priors['maxi']

		# extend with priors if necessary
		extend = (extent[1]-extent[0])*0.10
		if np.isclose(extent[0],mini):
			extent[0]=extent[0]-extend
		if np.isclose(extent[1],maxi):
			extent[1]=extent[1]+extend
    	
		extents.append((extent[0],extent[1]))
	
	return extents

def show_chain(sample_results,plotnames=None,chain=None,outname=None,alpha=0.6,truths=None,extents=None):
	
	'''
	plot the MCMC chain for all parameters
	'''
	
	# set + load variables
	parnames = np.array(sample_results['model'].theta_labels())
	nwalkers = chain.shape[0]
	nsteps = chain.shape[1]

	
	# plot geometry
	ndim = len(parnames)
	nwalkers_per_column = 128
	nx = int(math.ceil(nwalkers/float(nwalkers_per_column)))
	ny = ndim+1
	sz = np.array([nx,ny])
	factor = 3.0           # size of one side of one panel
	lbdim = 0.0 * factor   # size of margins
	whspace = 0.00*factor         # w/hspace size
	plotdim = factor * sz + factor *(sz-1)* whspace
	dim = 2*lbdim + plotdim

	fig, axarr = plt.subplots(ny, nx, figsize = (dim[0], dim[1]))
	fig.subplots_adjust(wspace=0.000,hspace=0.000)
	
	# plot chain in each parameter
	# sample_results['chain']: nwalkers, nsteps, nparams
	for ii in xrange(nx):
		walkerstart = nwalkers_per_column*ii
		walkerend   = np.clip(nwalkers_per_column*(ii+1),0,chain.shape[0])
		for jj in xrange(len(parnames)):
			for kk in xrange(walkerstart,walkerend):
				axarr[jj,ii].plot(chain[kk,:,jj],'-',
						   	      alpha=alpha)
				
			# fiddle with x-axis
			axarr[jj,ii].axis('tight')
			axarr[jj,ii].set_xticklabels([])
				
			# fiddle with y-axis
			if ii == 0:
				axarr[jj,ii].set_ylabel(plotnames[jj])
			else:
				axarr[jj,ii].set_yticklabels([])
			axarr[jj,ii].set_ylim(extents[jj])
			axarr[jj,ii].yaxis.get_major_ticks()[0].label1On = False # turn off bottom ticklabel

			# add truths
			if truths is not None and parnames[jj] == truths['parnames'][jj]:
				axarr[jj,ii].axhline(truths['plot_truths'][jj], linestyle='-',color='r')

		# plot lnprob
		for kk in xrange(walkerstart,walkerend): 
			axarr[jj+1,ii].plot(sample_results['lnprobability'][kk,:],'-',
						      color='black',
						      alpha=alpha)
		# axis
		axarr[jj+1,ii].axis('tight')
		axarr[jj+1,ii].set_xlabel('number of steps')
		# fiddle with y-axis
		if ii == 0:
			axarr[jj+1,ii].set_ylabel('lnprob')
		else:
			axarr[jj+1,ii].set_yticklabels([])

		finite = np.isfinite(sample_results['lnprobability'])
		max = np.max(sample_results['lnprobability'][finite])
		min = np.percentile(sample_results['lnprobability'][finite],10)
		axarr[jj+1,ii].set_ylim(min, max+np.abs(max)*0.01)
		
		axarr[jj+1,ii].yaxis.get_major_ticks()[0].label1On = False # turn off bottom ticklabel


	if outname is not None:
		plt.savefig(outname, bbox_inches='tight',dpi=100)
		plt.close()

def return_sedplot_vars(sample_results, extra_output, nufnu=True):

	'''
	if nufnu == True: return in units of nu * fnu. Else, return maggies.
	'''

	# observational information
	'''
	if 'truename' in sample_results['run_params']:
		from nonparametric_mocks_params import load_obs
		sample_results['obs'] = load_obs(os.getenv('APPS')+'/threed'+sample_results['run_params']['photname'].split('threed')[1], 
			                             sample_results['run_params']['objname'])
	'''
	mask = sample_results['obs']['phot_mask']
	wave_eff = sample_results['obs']['wave_effective'][mask]
	obs_maggies = sample_results['obs']['maggies'][mask]
	obs_maggies_unc = sample_results['obs']['maggies_unc'][mask]

	# model information
	spec = copy.copy(extra_output['bfit']['spec'])
	mu = extra_output['bfit']['mags'][mask]

	# output units
	if nufnu == True:
		c = 3e8
		factor = c*1e10
		mu *= factor/wave_eff
		spec *= factor/extra_output['observables']['lam_obs']
		obs_maggies *= factor/wave_eff
		obs_maggies_unc *= factor/wave_eff

	# here we want to return
	# effective wavelength of photometric bands, observed maggies, observed uncertainty, model maggies, observed_maggies-model_maggies / uncertainties
	# model maggies, observed_maggies-model_maggies/uncertainties
	return wave_eff/1e4, obs_maggies, obs_maggies_unc, mu, (obs_maggies-mu)/obs_maggies_unc, spec, extra_output['observables']['lam_obs']/1e4

def sed_figure(outname = None, truths = None,
			   colors = ['#1974D2'], sresults = None, extra_output = None,
			   labels = ['spectrum, best-fit'],
			   sfh_loc = [0.19,0.7,0.14,0.17],
			   model_photometry = True, main_color=['black'],
			   fir_extra = False, ml_spec=True,
               **kwargs):
	"""
	Plot the photometry for the model and data (with error bars), and
	plot residuals
	#sfh_loc = [0.32,0.35,0.12,0.14],
	good complimentary color for the default one is '#FF420E', a light red
	"""

	ms = 5
	alpha = 0.8
	
	from matplotlib import gridspec

	#### set up plot
	fig = plt.figure()
	gs = gridspec.GridSpec(2,1, height_ratios=[3,1])
	gs.update(hspace=0)
	phot, res = plt.Subplot(fig, gs[0]), plt.Subplot(fig, gs[1])
	sfh_ax = fig.add_axes(sfh_loc,zorder=32)

	### diagnostic text
	textx = 0.98
	texty = 0.04
	deltay = 0.035

	### if we have multiple parts, color ancillary data appropriately
	if len(colors) > 1:
		main_color = colors

	#### iterate over things to plot
	for i,sample_results in enumerate(sresults):

		#### grab data for maximum probability model
		wave_eff, obsmags, obsmags_unc, modmags, chi, modspec, modlam = return_sedplot_vars(sample_results,extra_output[i])

		#### plot maximum probability model
		if model_photometry:
			phot.plot(wave_eff, modmags, color=colors[i], 
				      marker='o', ms=ms, linestyle=' ', label = 'photometry, best-fit', alpha=alpha, 
				      markeredgewidth=0.7,**kwargs)
		
		res.plot(wave_eff, chi, color=colors[i],
		         marker='o', linestyle=' ', label=labels[i], 
			     ms=ms,alpha=alpha,markeredgewidth=0.7,**kwargs)		

		###### spectra for q50 + 5th, 95th percentile
		w = extra_output[i]['observables']['lam_obs']
		spec_pdf = np.zeros(shape=(len(w),3))

		for jj in xrange(len(w)): spec_pdf[jj,:] = np.percentile(extra_output[i]['observables']['spec'][jj,:],[5.0,50.0,95.0])
		
		sfactor = 3e18/w
		nz = modspec > 0
		if ml_spec:
			phot.plot(modlam[nz], modspec[nz], linestyle='-',
		              color=colors[i], alpha=0.9,zorder=-1,label = labels[i],**kwargs)
		else:
			phot.plot(modlam[nz], spec_pdf[nz,1]*sfactor[nz], linestyle='-',
		              color=colors[i], alpha=0.9,zorder=-1,label = labels[i],**kwargs)	

		nz = spec_pdf[:,1] > 0
		phot.fill_between(w/1e4, spec_pdf[:,0]*sfactor, 
			                     spec_pdf[:,2]*sfactor,
			                     color=colors[i],
			                     alpha=0.3,zorder=-1)
		### observations!
		if i == 0:
			xplot = wave_eff
			yplot = obsmags
			yerr = obsmags_unc

		    # PLOT OBSERVATIONS + ERRORS 
			phot.errorbar(xplot, yplot, yerr=yerr,
		                  color=obs_color, marker='o', label='observed', alpha=alpha, linestyle=' ',ms=ms,zorder=0)

		#### calculate and show reduced chi-squared
		chisq = np.sum(chi**2)
		ndof = np.sum(sample_results['obs']['phot_mask'])
		reduced_chisq = chisq/(ndof)

		phot.text(textx, texty+deltay*(i+1), r'best-fit $\chi^2$/N$_{\mathrm{phot}}$='+"{:.2f}".format(reduced_chisq),
			  fontsize=10, ha='right',transform = phot.transAxes,color=main_color[i])

	xlim = (min(xplot)*0.4,max(xplot)*1.5)

	### FIR extras
	if fir_extra:
		# FIR photometry for IC 4553 / Arp 220
		# from NED: http://ned.ipac.caltech.edu/cgi-bin/nph-objsearch?objname=IC%204553&extend=no&out_csys=Equatorial&out_equinox=J2000.0&obj_sort=RA+or+Longitude&of=pre_text&zv_breaker=30000.0&list_limit=5&img_stamp=YES
		# FILTER FLUX UNCERTAINTY (jansky)
		# 250 microns (SPIRE)	30.1 1.5
		# 350 microns (SPIRE)	11.7 0.6
		# 500 microns (SPIRE)	3.9 0.2
		lam = np.array([250,350,500])*1e4
		to_nufnu = 3e18/lam

		fir_obs_phot = np.array([30.1,11.7,3.9]) / 3631. * to_nufnu # in maggies
		fir_obs_err  = np.array([1.5,0.6,0.2]) / 3631. * to_nufnu # in maggies

		fir_model_phot = np.zeros(shape=(3,3))
		for i in range(3): fir_model_phot[i,:] = np.percentile(sample_results['hphot']['mags'][i,:],[50.0,84.0,16.0])*to_nufnu[i]
		fir_model_err = threed_dutils.asym_errors(fir_model_phot[:,0],fir_model_phot[:,1],fir_model_phot[:,2],log=False)

		#### plot points
		phot.errorbar(lam/1e4, fir_obs_phot, yerr=fir_obs_err,
	                  color='red', marker='o', label='observed [NOT FIT]', alpha=alpha, linestyle=' ',ms=ms,zorder=0)

		phot.errorbar(lam/1e4, fir_model_phot[:,0], yerr=fir_model_err,
	                  color=colors[0], 
				      marker='o', ms=ms, linestyle=' ', alpha=alpha, 
				      markeredgewidth=0.7,**kwargs)

		chi_hersch = (fir_obs_phot-fir_model_phot[:,0])/fir_obs_err
		res.plot(lam/1e4, chi_hersch, color='red',
		         marker='o', linestyle=' ',
			     ms=ms,alpha=alpha,markeredgewidth=0.7,**kwargs)

		xlim = (xlim[0],750)

	### apply plot limits
	phot.set_xlim(xlim)
	res.set_xlim(xlim)
	phot.set_ylim(min(yplot[np.isfinite(yplot)])*0.4,max(yplot[np.isfinite(yplot)])*5)

	#### add SFH plot
	add_sfh_plot(extra_output,fig,
				 main_color = main_color,
                 truths=truths, ax_inset=sfh_ax,
                 text_size=1.4)

	#### add RGB image
	try:
		imgname = os.getenv('APPS')+'/threedhst_bsfh/data/brownseds_data/rgb/'+sresults[0]['run_params']['objname'].replace(' ','_')+'.png'
		img = mpimg.imread(imgname)
		ax_inset2 = fig.add_axes([0.46,0.34,0.15,0.15],zorder=32)
		ax_inset2.imshow(img)
		ax_inset2.set_axis_off()
	except IOError:
		print 'no RGB image'

	### plot truths
	if truths is not None:
		
		# if truths are made with a different model than they are fit with,
		# then this will be passing parameters to the wrong model. pass.
		# in future, attach a model to the truths file!
		try:
			wave_eff_truth, _, _, _, chi_truth, _, _ = return_sedplot_vars(truths['truths'], sresults[0], sps)

			res.plot(np.log10(wave_eff_truth), chi_truth, 
				     color='blue', marker='o', linestyle=' ', label='truths', 
				     ms=ms,alpha=0.3,markeredgewidth=0.7,**kwargs)
		except AssertionError:
			pass

	#### TEXT, FORMATTING, LABELS
	z_txt = sresults[0]['model'].params['zred'][0]
	phot.text(textx, texty, 'z='+"{:.2f}".format(z_txt),
			  fontsize=10, ha='right',transform = phot.transAxes)

	# extra line
	res.axhline(0, linestyle=':', color='grey')
	res.yaxis.set_major_locator(MaxNLocator(5))

	# legend
	# make sure not to repeat labels
	from collections import OrderedDict
	handles, labels = phot.get_legend_handles_labels()
	by_label = OrderedDict(zip(labels, handles))
	phot.legend(by_label.values(), by_label.keys(), 
				loc=1, prop={'size':10},
			    scatterpoints=1)
			    
    # set labels
	res.set_ylabel( r'$\chi$')
	phot.set_ylabel(r'$\nu f_{\nu}$')
	res.set_xlabel(r'$\lambda_{\mathrm{obs}}$ [$\mu$m]')
	phot.set_yscale('log',nonposx='clip')
	phot.set_xscale('log',nonposx='clip')
	res.set_xscale('log',nonposx='clip',subsx=(2,5))
	res.xaxis.set_minor_formatter(minorFormatter)
	res.xaxis.set_major_formatter(majorFormatter)

	# clean up and output
	fig.add_subplot(phot)
	fig.add_subplot(res)
	
	'''
	# set second x-axis
	y1, y2=phot.get_ylim()
	x1, x2=phot.get_xlim()
	ax2=phot.twiny()
	ax2.set_xticks(np.arange(0,10,0.2))
	ax2.set_xlim(x1/(1+z_txt), x2/(1+z_txt))
	ax2.set_xlabel(r'log($\lambda_{rest}$) [$\mu$m]')
	ax2.set_ylim(y1, y2)
	ax2.set_xscale('log',nonposx='clip',subsx=(2,5))
	ax2.xaxis.set_minor_formatter(minorFormatter)
	ax2.xaxis.set_major_formatter(majorFormatter)
	'''
	# remove ticks
	phot.set_xticklabels([])
    
	if outname is not None:
		fig.savefig(outname, bbox_inches='tight', dpi=dpi)
		plt.close()

	#os.system('open '+outname)

def make_all_plots(filebase=None,
				   extra_output=None,
				   outfolder=os.getenv('APPS')+'/threedhst_bsfh/plots/',
				   sample_results=None,
				   param_name=None,
				   plt_chain=True,
				   plt_corner=True,
				   plt_sed=True):

	'''
	Driver. Loads output, makes all plots for a given galaxy.
	'''

	# make sure the output folder exists
	if not os.path.isdir(outfolder):
		os.makedirs(outfolder)

	if sample_results is None:
		try:
			sample_results, powell_results, model, extra_output = load_prospector_data(filebase, hdf5=True)
		except TypeError:
			return
	else: # if we already have sample results, but want powell results
		try:
			_, powell_results, model, extra_output = load_prospector_data(filebase,no_sample_results=True, hdf5=True)
		except TypeError:
			return	

	run_params = model_setup.get_run_params(param_file=param_name)
	sps = model_setup.load_sps(**run_params)

	# BEGIN PLOT ROUTINE
	print 'MAKING PLOTS FOR ' + filebase.split('/')[-1] + ' in ' + outfolder
	
	# do we know the truths?
	objname = sample_results['run_params']['objname']
	try:
		truths = threed_dutils.load_truths(os.getenv('APPS')+'/threed'+sample_results['run_params']['param_file'].split('/threed')[1],
			                               model=sample_results['model'],obs=sample_results['obs'], sps=sps)
	except KeyError:
		truths = None

    # chain plot
	extents = return_extent(sample_results)
	if plt_chain: 
		print 'MAKING CHAIN PLOT'

		show_chain(sample_results, plotnames=sample_results['model'].theta_labels(),chain=sample_results['chain'],
	               outname=outfolder+objname+'.chain.png', extents=extents,
			       alpha=0.3,truths=truths)

	# corner plot
	if plt_corner: 
		print 'MAKING CORNER PLOT'
		chopped_sample_results = copy.deepcopy(sample_results)

		subcorner(sample_results, sps, copy.deepcopy(sample_results['model']),
				  extra_output,outname=outfolder+objname,
				  extents=extents, truths=truths, powell_results=powell_results)

	# sed plot
	if plt_sed:
		print 'MAKING SED PLOT'
		
		# FAST fit?
		try:
			sample_results['run_params']['fastname']
			fast=1
		except:
			fast=0

 		# plot
 		pfig = sed_figure(sresults = [sample_results], extra_output=[extra_output],
 			              truths=truths, outname=outfolder+objname+'.sed.png')
 		
def plot_all_driver(runname=None,**extras):

	'''
	for a list of galaxies, make all plots
	'''
	if runname == None:
		runname = 'testsed_simha_truth'

	filebase, parm_basename, ancilname=threed_dutils.generate_basenames(runname)
	for jj in xrange(len(filebase)):
		print 'iteration '+str(jj) 
		make_all_plots(filebase=filebase[jj],\
		               outfolder=os.getenv('APPS')+'/threedhst_bsfh/plots/'+runname+'/',
		               param_name=parm_basename[jj],
		               **extras)
	