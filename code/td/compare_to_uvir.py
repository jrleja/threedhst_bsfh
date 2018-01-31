import numpy as np
import matplotlib.pyplot as plt
import os, hickle, td_io, prosp_dutils, copy
from prospector_io import load_prospector_data, load_prospector_extra
from astropy.cosmology import WMAP9
from prospect.models import sedmodel
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
from dynesty.plotting import _quantile as weighted_quantile
from fix_ir_sed import mips_to_lir
from scipy.stats import spearmanr

plt.ioff()

popts = {'fmt':'o', 'capthick':1.5,'elinewidth':1.5,'ms':9,'alpha':0.8,'color':'0.3'}
red = '#FF3D0D'
dpi = 160 # plot resolution
cmap = 'cool'
minsfr, minssfr = 0.01, 1e-13
ms, s = 0.5, 1 # symbol sizes
alpha, alpha_scat = 0.1, 0.3
medopts = {'marker':' ','alpha':0.95,'color':'red','ms': 7,'mec':'k','zorder':5}
popts = {'fmt':'o', 'capthick':.05,'elinewidth':.05,'alpha':0.2,'color':'0.3','ms':0.5}
nbin_min = 10

def collate_data(runname, filename=None, regenerate=False, nobj=None, **opts):
    """must rewrite this such that NO CHAINS are saved!
    want to return AGN_FRAC and OLD_FRAC
    which is (SFR_AGN) / (SFR_UVIR_LIR_PROSP), (SFR_OLD) / (SFR_UVIR_LIR_PROSP)
    also compare (SFR_UVIR_PROSP) to (SFR_PROSP)
    """

    ### if it's already made, load it and give it back
    # else, start with the making!
    if os.path.isfile(filename) and regenerate == False:
        with open(filename, "r") as f:
            outdict=hickle.load(f)

        return outdict

    ### define output containers
    out = {}
    qvals = ['q50','q84','q16']
    for par in ['sfr_uvir_truelir_prosp', 'sfr_uvir_lirfrommips_prosp', 'sfr_prosp', 'ssfr_prosp','avg_age', \
                'logzsol', 'fagn','agn_heating_fraction','old_star_heating_fraction', 'young_star_heating_fraction',
                'dust2', 'dust_index']:
        out[par] = {}
        for q in qvals: out[par][q] = []
    for par in ['sfr_uvir_obs','objname']: out[par] = []

    ### fill output containers
    basenames, _, _ = prosp_dutils.generate_basenames(runname)
    if nobj is not None:
        basenames = basenames[:nobj]
    field = [name.split('/')[-1].split('_')[0] for name in basenames]

    ### load necessary information
    uvirlist = []
    allfields = np.unique(field).tolist()
    for f in allfields:
        uvirlist.append(td_io.load_mips_data(f))

    ### iterate over items
    for i, name in enumerate(basenames):

        # load output from fit
        try:
            res, _, model, prosp = load_prospector_data(name)
        except:
            print name.split('/')[-1]+' failed to load. skipping.'
            continue
        if prosp is None:
            continue

        out['objname'] += [name.split('/')[-1]]
        print 'loaded ' + out['objname'][-1]

        # Variable model parameters

        # Variable + nonvariable model parameters ('extras')
        for q in qvals: 
            out['fagn'][q] += [prosp['thetas']['fagn'][q]]
            out['logzsol'][q] += [prosp['thetas']['massmet_2'][q]]
            out['dust2'][q] += [prosp['thetas']['dust2'][q]]
            out['dust_index'][q] += [prosp['thetas']['dust_index'][q]]
            out['sfr_prosp'][q] += [prosp['extras']['sfr_100'][q]]
            out['ssfr_prosp'][q] += [prosp['extras']['ssfr_100'][q]]
            out['avg_age'][q] += [prosp['extras']['avg_age'][q]]

        # observed UV+IR SFRs
        # find correct field, find ID match
        u_idx = uvirlist[allfields.index(field[i])]['id'].astype(int) == int(out['objname'][-1].split('_')[-1])
        out['sfr_uvir_obs'] += [uvirlist[allfields.index(field[i])]['sfr'][u_idx][0]]

        # pull out relevant quantities
        # "AGN" luminosities are old+young stars, NO AGN
        # "young" luminosities are young stars, NO AGN OR OLD STARS
        lir_agn, luv_agn = prosp['extras']['lir_agn']['chain'], prosp['extras']['luv_agn']['chain']
        lir_tot, luv_tot = prosp['extras']['lir']['chain'], prosp['extras']['luv']['chain']
        lir_young, luv_young = prosp['extras']['lir_young']['chain'], prosp['extras']['luv_young']['chain']

        # Ratios and calculations
        # here we calculate SFR(UV+IR) with LIR from:
        # (a) the 'true' L_IR in the model
        # (b) L_IR estimated from the model MIPS flux using DH02 templates
        sfr_uvir_truelir_prosp = prosp_dutils.sfr_uvir(lir_tot,luv_tot)

        midx = np.array(['mips' in u for u in res['obs']['filternames']],dtype=bool)
        mips_flux = prosp['obs']['mags'][:,midx].squeeze() * 3631 * 1e3 # input for this LIR must be in janskies
        lir = mips_to_lir(mips_flux, res['model'].params['zred'][0])
        sfr_uvir_lirfrommips_prosp = prosp_dutils.sfr_uvir(lir,prosp['extras']['luv']['chain'])

        # here we estimate LIR+LUV fractions for AGN, young stars, and old stars
        agn_heating_fraction = 1-(lir_agn+luv_agn) / (lir_tot+luv_tot)
        young_star_heating_fraction = (lir_young + luv_young) / (lir_tot+luv_tot)
        old_star_heating_fraction = 1- young_star_heating_fraction - agn_heating_fraction

        # turn all of these into percentiles
        pars = ['agn_heating_fraction', 'old_star_heating_fraction', 'young_star_heating_fraction', \
                'sfr_uvir_truelir_prosp','sfr_uvir_lirfrommips_prosp']
        vals = [agn_heating_fraction, old_star_heating_fraction, young_star_heating_fraction, \
                sfr_uvir_truelir_prosp, sfr_uvir_lirfrommips_prosp]
        for p, v in zip(pars,vals):
            mid, up, down = weighted_quantile(v, np.array([0.5, 0.84, 0.16]), weights=res['weights'][prosp['sample_idx']])
            out[p]['q50'] += [mid]
            out[p]['q84'] += [up]
            out[p]['q16'] += [down]

    for key in out.keys():
        if type(out[key]) == dict:
            for key2 in out[key].keys(): out[key][key2] = np.array(out[key][key2])
        else:
            out[key] = np.array(out[key])

    ### dump files and return
    hickle.dump(out,open(filename, "w"))
    return out

def do_all(runname='td_huge', outfolder=None,**opts):

    if outfolder is None:
        outfolder = os.getenv('APPS') + '/prospector_alpha/plots/'+runname+'/fast_plots/'
        if not os.path.isdir(outfolder):
            os.makedirs(outfolder)
            os.makedirs(outfolder+'data/')

    data = collate_data(runname,filename=outfolder+'data/uvircomp.h5',**opts)

    plot_uvir_comparison(data,outfolder)
    plot_heating_sources(data,outfolder)
    plot_heating_sources(data,outfolder,old_stars_only=True)
    plot_rankorder_correlations(data, outfolder+'deltasfr_spearman.png')

def plot_uvir_comparison(data, outfolder):
    """ Prospector internal UVIR SFR versus Kate's UVIR SFR
    calculated from observed MIPS magnitude and true LUV
    """

    fig, ax = plt.subplots(1, 1, figsize = (4.5,4.5))

    #### Plot Prospector UV+IR SFR versus the observed UV+IR SFR
    good = data['sfr_uvir_obs'] > 0
    xdat = np.clip(data['sfr_uvir_obs'][good],minsfr,np.inf)
    ydat = np.clip(data['sfr_uvir_lirfrommips_prosp']['q50'][good],minsfr,np.inf)

    ax.plot(xdat, ydat, 'o', color='0.4',markeredgecolor='k',ms=ms, alpha=alpha)
    min, max = xdat.min()*0.8, ydat.max()*1.2
    ax.plot([min, max], [min, max], '--', color='0.4',zorder=-1)
    ax.axis([min,max,min,max])

    # labels and scales
    ax.set_xlabel('SFR$_{\mathrm{UV+IR,classic}}$')
    ax.set_ylabel('SFR$_{\mathrm{UV+IR,Prospector}}$')

    ax.set_xscale('log',subsx=[3])
    ax.xaxis.set_minor_formatter(FormatStrFormatter('%2.4g'))
    ax.xaxis.set_major_formatter(FormatStrFormatter('%2.4g'))
    ax.tick_params('both', pad=3.5, size=8.0, width=1.0, which='both')

    ax.set_yscale('log',subsy=[3])
    ax.yaxis.set_minor_formatter(FormatStrFormatter('%2.4g'))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%2.4g'))

    # offset and scatter
    offset,scatter = prosp_dutils.offset_and_scatter(np.log10(xdat),np.log10(ydat),biweight=True)
    ax.text(0.01,0.94, 'biweight scatter='+"{:.2f}".format(scatter) +' dex',transform=ax.transAxes)
    ax.text(0.01,0.88, 'offset='+"{:.2f}".format(offset) +' dex',transform=ax.transAxes)

    # save and exit
    plt.tight_layout()
    plt.savefig(outfolder+'prosp_uvir_to_obs_uvir.png',dpi=dpi)
    plt.close()

def plot_heating_sources(data, outfolder, color_by_fagn=False, color_by_logzsol=True, old_stars_only=False):

    fig, ax = plt.subplots(1, 1, figsize = (5,4))

    # first plot SFR ratio versus heating by young stars
    # grab quantities
    x = data['young_star_heating_fraction']['q50']
    y = data['sfr_prosp']['q50'] / data['sfr_uvir_truelir_prosp']['q50']

    # add colored points and colorbar
    ax.axis([0,1,0,1.2])
    if color_by_fagn:
        colorvar = np.log10(data['fagn']['q50'])
        colorlabel = r'log(f$_{\mathrm{AGN}}$)'
        ax1_outstring = '_fagn'
    elif color_by_logzsol:
        colorvar = data['logzsol']['q50']
        colorlabel = r'log(Z/Z$_{\odot}$)'
        ax1_outstring = '_logzsol'
    else:
        colorvar = np.log10(np.clip(data['ssfr_prosp']['q50'],minssfr,np.inf))
        colorlabel = r'log(sSFR$_{\mathrm{SED}}$)'
        ax1_outstring = '_ssfr'

    pts = ax.scatter(x, y, s=s, cmap=cmap, c=colorvar, vmin=colorvar.min(), vmax=colorvar.max(),alpha=alpha_scat)
    cb = fig.colorbar(pts, ax=ax, aspect=10)
    cb.set_label(colorlabel)
    cb.solids.set_rasterized(True)
    cb.solids.set_edgecolor("face")

    # labels
    ax.set_ylabel('SFR$_{\mathrm{Prosp}}$/SFR$_{\mathrm{UV+IR}}$')
    ax.set_xlabel('fraction of heating from young stars')

    # next plot the sources of the heating
    if old_stars_only:
        fig2, ax2 = plt.subplots(1, 1, figsize = (4,4))
        ax2 = np.atleast_1d(ax2)
        yvars = [data['old_star_heating_fraction']['q50']]
        ylabels = [r'(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{old\/stars}}$/(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{total}}$']
        ax2_outname = 'heating_fraction_vs_ssfr.png'
    else:
        fig2, ax2 = plt.subplots(1, 3, figsize = (9,3))
        yvars = [data[x+'_heating_fraction']['q50'] for x in ['young_star', 'old_star', 'agn']]
        ylabels = [r'(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{young\/stars}}$/(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{total}}$',
                   r'(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{old\/stars}}$/(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{total}}$',
                   r'(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{AGN}}$/(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{total}}$']
        ax2_outname = 'heating_fraction_vs_ssfr_all.png'
    xvar = np.log10(np.clip(data['ssfr_prosp']['q50'],minssfr,np.inf))
    for i,yvar in enumerate(yvars): 
        ax2[i].errorbar(xvar, yvar, **popts)
        x, y, bincount = prosp_dutils.running_median(xvar,yvar,avg=False,return_bincount=True,nbins=20)
        x, y = x[bincount > nbin_min], y[bincount > nbin_min]
        ax2[i].plot(x,y, **medopts)

    # labels and limits
    for a in ax2: 
        a.set_xlabel('log(sSFR$_{\mathrm{Prosp}}$)')
        a.set_ylim(0,1)
        a.set_ylabel(ylabels[i])

    # clean up
    fig.tight_layout()
    fig2.tight_layout()

    fig.savefig(outfolder+'uvir_frac'+ax1_outstring+'.png',dpi=dpi)
    fig2.savefig(outfolder+ax2_outname,dpi=dpi)
    plt.close()
    plt.close()

def plot_rankorder_correlations(data, outname):
    """delta(sSFR) versus log(Z/Zsun), stellar age, fagn
    more interpreted: AGN heating, young star heating, old star heating etc
    """

    # define variables of interest
    xvars = [data['old_star_heating_fraction']['q50'], data['agn_heating_fraction']['q50'],
             data['logzsol']['q50']]#, data['dust2']['q50'], data['dust_index']['q50'] ]
    xlabels = [r'(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{old\/stars}}$/(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{total}}$',
               r'(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{AGN}}$/(L$_{\mathrm{IR}}$+L$_{\mathrm{UV}}$)$_{\mathrm{total}}$',
               r'log(Z/Z$_{\odot}$)']#, 'dust2', 'dustindex']
    xlim = [(-0.02,1.02),(-0.02,1.02),(-2,0.2)]#,(0,3.1),(-2.3,0.5)]
    yvar = np.log10(data['sfr_prosp']['q50'] / data['sfr_uvir_obs'])
    ylim = (-3.0, 3.0)
    idx = data['sfr_uvir_obs'] > 0

    # plot geometry
    fig, ax = plt.subplots(1, 3, figsize = (9,3))
    ax = ax.ravel()

    for i, (xvar,xlabel) in enumerate(zip(xvars,xlabels)):

        ax[i].errorbar(xvar[idx],yvar[idx],**popts)
        ax[i].set_xlabel(xlabel)
        ax[i].set_ylabel(r'log(SFR$_{\mathrm{Prosp}}$/SFR$_{\mathrm{UV+IR}}$)')

        ax[i].set_xlim(xlim[i])
        ax[i].set_ylim(ylim)

        rho_spear = spearmanr(xvar[idx],yvar[idx])[0]
        ax[i].text(0.02,0.92,r'$\rho_{\mathrm{S}}$='+'{:1.2f}'.format(rho_spear),transform=ax[i].transAxes)

        ax[i].axhline(0, linestyle='--', color='k',lw=1,zorder=10)

        # running median
        in_plot = (yvar > ylim[0]) & (yvar < ylim[1]) & idx
        x, y, bincount = prosp_dutils.running_median(xvar[in_plot],yvar[in_plot],avg=False,return_bincount=True,nbins=20)
        x, y = x[bincount > nbin_min], y[bincount > nbin_min]
        ax[i].plot(x,y, **medopts)

    plt.tight_layout()
    plt.savefig(outname,dpi=dpi)
    plt.close()
