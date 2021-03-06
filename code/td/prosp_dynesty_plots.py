import numpy as np
import matplotlib.pyplot as plt
import os
from prosp_dutils import generate_basenames, smooth_spectrum, transform_zfraction_to_sfrfraction
from dynesty import plotting as dyplot
from matplotlib.ticker import MaxNLocator, FormatStrFormatter, FuncFormatter
from prospector_io import load_prospector_data, find_all_prospector_results
from scipy.ndimage import gaussian_filter as norm_kde
from matplotlib import gridspec

plt.ioff() # don't pop up a window for each plot

# plotting variables
fs, tick_fs = 28, 22
obs_color = '#545454'
truth_color = 'blue'

def subcorner(res, eout, parnames, outname=None, maxprob=False, truth_dict=None, truths=None, **opts):
    """ wrapper around dyplot.cornerplot()
    adds in a star formation history and marginalized parameters
    for some key outputs (stellar mass, SFR, sSFR, half-mass time)
    """

    # write down some keywords
    title_kwargs = {'fontsize':fs*.7}
    label_kwargs = {'fontsize':fs*.7}

    if truth_dict is not None:
        truths = []
        for par in parnames:
            if par in truth_dict.keys():
                truths += [truth_dict[par]]
            else:
                truths += [np.nan]

    if (maxprob) & (truths is None):
        truths = res['samples'][eout['sample_idx'][0],:]

    # create dynesty plot
    # maximum probability solution in red
    fig, axes = dyplot.cornerplot(res, show_titles=True, labels=parnames, truths=truths,
                                  truth_color=truth_color,
                                  label_kwargs=label_kwargs, title_kwargs=title_kwargs)

    for ax in axes.ravel():
        ax.xaxis.set_tick_params(labelsize=tick_fs*.7)
        ax.yaxis.set_tick_params(labelsize=tick_fs*.7)

    # extra parameters
    eout_toplot = ['stellar_mass','sfr_100', 'ssfr_100', 'avg_age', 'H alpha 6563', 'H alpha/H beta']
    not_log = ['half_time','H alpha/H beta']
    ptitle = [r'log(M$_*$)',r'log(SFR$_{\mathrm{100 Myr}}$)',
              r'log(sSFR$_{\mathrm{100 Myr}}$)',r'log(t$_{\mathrm{avg}}$) [Gyr]',
              r'log(EW$_{\mathrm{H \alpha}}$)',r'Balmer decrement']

    # either we create a new figure for extra parameters
    # or add to old figure
    # depending on dimensionality of model (and thus of the plot)
    if (axes.shape[0] <= 6):

        # only plot a subset of parameters
        eout_toplot, ptitle = eout_toplot[:4], ptitle[:4]

        # generate fake results file for dynesty
        nsamp, nvar = eout['weights'].shape[0], len(eout_toplot)
        fres = {'samples': np.empty(shape=(nsamp,nvar)), 'weights': eout['weights']}
        for i in range(nvar): 
            the_chain = eout['extras'][eout_toplot[i]]['chain']
            if eout_toplot[i] in not_log:
                fres['samples'][:,i] = the_chain
            else:
                fres['samples'][:,i] = np.log10(the_chain)

        fig2, axes2 = dyplot.cornerplot(fres, show_titles=True, labels=ptitle, label_kwargs=label_kwargs, title_kwargs=title_kwargs)
       
        # add SFH plot
        sfh_ax = fig2.add_axes([0.7,0.7,0.25,0.25],zorder=32)
        add_sfh_plot([eout], fig2,
                     main_color = ['black'],
                     ax_inset=sfh_ax,
                     text_size=1.5,lw=2,truth_dict=truth_dict)
        fig2.savefig('{0}.corner.extra.pdf'.format(outname))
        plt.close(fig2)

    else:

        # add SFH plot
        sfh_ax = fig.add_axes([0.75,0.435,0.22,0.22],zorder=32)
        add_sfh_plot([eout], fig, main_color = ['black'], ax_inset=sfh_ax, text_size=2,lw=4,truth_dict=truth_dict)

        # create extra parameters
        axis_size = fig.get_axes()[0].get_position().size
        xs, ys = 0.4, 1.0-axis_size[1]*1.3
        xdelta, ydelta = axis_size[0]*1.2, axis_size[1]*1.8
        plotloc = 0
        for jj, ename in enumerate(eout_toplot):

            # pull out chain, quantiles
            weights = eout['weights']
            if 'H alpha' not in ename:
                pchain = eout['extras'][ename]['chain']
                qvalues = [eout['extras'][ename]['q16'],
                           eout['extras'][ename]['q50'],
                           eout['extras'][ename]['q84']]
            elif '6563' in ename:
                pchain = eout['obs']['elines'][ename]['ew']['chain']
                qvalues = [eout['obs']['elines'][ename]['ew']['q16'],
                           eout['obs']['elines'][ename]['ew']['q50'],
                           eout['obs']['elines'][ename]['ew']['q84']]
            else:
                pchain = eout['obs']['elines']['H alpha 6563']['flux']['chain'] / eout['obs']['elines']['H beta 4861']['flux']['chain']
                qvalues = dyplot._quantile(pchain,np.array([0.16, 0.50, 0.84]),weights=weights)

            # logify. 
            if ename not in not_log:
                pchain = np.log10(pchain)
                qvalues = np.log10(qvalues)

            # make sure we're not producing infinities.
            # if we are, replace them with minimum.
            # if everything is infinity, skip and don't add the axis!
            # one failure mode here: if qvalues include an infinity!
            infty = ~np.isfinite(pchain)
            if infty.sum() == pchain.shape[0]:
                continue
            if infty.sum():
                pchain[infty] = pchain[~infty].min()

            # total obfuscated way to add in axis
            ax = fig.add_axes([xs+(jj%4)*xdelta, ys-int(jj/4)*ydelta, axis_size[0], axis_size[1]])

            # complex smoothing routine to match dynesty
            bins = int(round(10. / 0.02))
            n, b = np.histogram(pchain, bins=bins, weights=weights,
                                range=[pchain.min(),pchain.max()])
            n = norm_kde(n, 10.)
            x0 = 0.5 * (b[1:] + b[:-1])
            y0 = n
            ax.fill_between(x0, y0, color='k', alpha = 0.6)

            # plot and show quantiles
            for q in qvalues: ax.axvline(q, ls="dashed", color='red')

            q_m = qvalues[1]-qvalues[0]
            q_p = qvalues[2]-qvalues[1]
            fmt = "{{0:{0}}}".format(".2f").format
            title = r"${{{0}}}_{{-{1}}}^{{+{2}}}$"
            title = title.format(fmt(float(qvalues[1])), fmt(float(q_m)), fmt(float(q_p)))
            #title = "{0}\n={1}".format(ptitle[jj], title)
            ax.set_title(title, va='bottom',**title_kwargs)
            ax.set_xlabel(ptitle[jj],**label_kwargs)

            # look for truth
            min, max = np.percentile(pchain,0.5), np.percentile(pchain,99.5)
            if truth_dict is not None:
                if ename in truth_dict.keys():
                    if ename not in not_log:
                        tplt = np.log10(truth_dict[ename])
                    else:
                        tplt = truth_dict[ename]
                    ax.axvline(tplt, ls=":", color=truth_color,lw=1.5)

                    min = np.min([min,tplt.min()])
                    max = np.max([max,tplt.max()])

            if ename in not_log:
                min, max = min*0.99, max*1.01
            else:
                min = min - 0.02
                max = max + 0.02

            # set range
            ax.set_xlim(min,max)
            ax.set_ylim(0, 1.1 * np.max(n))
            ax.set_yticklabels([])
            ax.xaxis.set_major_locator(MaxNLocator(5))
            [l.set_rotation(45) for l in ax.get_xticklabels()]
            ax.xaxis.set_tick_params(labelsize=label_kwargs['fontsize'])

    fig.savefig('{0}.corner.pdf'.format(outname))
    plt.close(fig)

def transform_chain(flatchain, model):

    parnames = np.array(model.theta_labels())
    if flatchain.ndim == 1:
        flatchain = np.atleast_2d(flatchain)

    # turn fractional_dust1 into dust1
    if 'dust1_fraction' in model.free_params:
        d1idx, d2idx = model.theta_index['dust1_fraction'], model.theta_index['dust2']
        flatchain[:,d1idx] *= flatchain[:,d2idx]
        parnames[d1idx] = 'dust1'

    # turn z_fraction into sfr_fraction
    if 'z_fraction' in model.free_params:
        zidx = model.theta_index['z_fraction']
        flatchain[:,zidx] = transform_zfraction_to_sfrfraction(flatchain[:,zidx]) 
        parnames = np.core.defchararray.replace(parnames,'z_fraction','sfr_fraction')

    # rename mass_met
    if 'massmet' in model.free_params:
        midx = model.theta_index['massmet']
        parnames[midx.start] = 'logmass'
        parnames[midx.start+1] = 'logzsol'

    return flatchain.squeeze(), parnames

def add_sfh_plot(eout,fig,ax_loc=None,
                 main_color=None,tmin=0.01,smooth_sfh=False,
                 text_size=1,ax_inset=None,lw=1,truth_dict=None):
    """add a small SFH plot at ax_loc
    text_size: multiply font size by this, to accomodate larger/smaller figures
    """

    # set up plotting
    if ax_inset is None:
        if fig is None:
            ax_inset = ax_loc
        else:
            ax_inset = fig.add_axes(ax_loc,zorder=32)
    axfontsize=4*text_size

    xmin, ymin = np.inf, np.inf
    xmax, ymax = -np.inf, -np.inf

    for i, eout in enumerate(eout):
        
        # create master time bin
        min_time = np.max([eout['sfh']['t'].min(),0.01])
        max_time = eout['sfh']['t'].max()
        tvec = 10**np.linspace(np.log10(min_time),np.log10(max_time),num=50)

        # create median SFH
        perc = np.zeros(shape=(len(tvec),3))
        for jj in range(len(tvec)): 
            # nearest-neighbor 'interpolation'
            # exact answer for binned SFHs
            if len(eout['sfh']['t'].shape) == 2:
                idx = np.abs(eout['sfh']['t'][0,:] - tvec[jj]).argmin(axis=-1)
            else:
                idx = np.abs(eout['sfh']['t'] - tvec[jj]).argmin(axis=-1)
            perc[jj,:] = dyplot._quantile(eout['sfh']['sfh'][:,idx],[0.16,0.50,0.84],weights=eout['weights'])

        if smooth_sfh:
            for j in range(3):
                perc[:,j] = norm_kde(perc[:,j],1)

        #### plot SFH
        ax_inset.plot(tvec, perc[:,1],'-',color=main_color[i],lw=lw)
        ax_inset.fill_between(tvec, perc[:,0], perc[:,2], color=main_color[i], alpha=0.3)
        ax_inset.plot(tvec, perc[:,0],'-',color=main_color[i],alpha=0.3,lw=lw)
        ax_inset.plot(tvec, perc[:,2],'-',color=main_color[i],alpha=0.3,lw=lw)

        #### update plot ranges
        if 'tage' in eout['thetas'].keys():
            xmin = np.min([xmin,tvec.min()])
            xmax = np.max([xmax,tvec.max()])
            ymax = np.max([ymax,perc.max()])
            ymin = ymax*1e-4
        else:
            xmin = np.min([xmin,tvec.min()])
            xmax = np.max([xmax,tvec.max()])
            ymin = np.min([ymin,perc[perc>0].min()])
            ymax = np.max([ymax,perc.max()])

    if truth_dict is not None:
        ax_inset.plot(truth_dict['t'],truth_dict['sfh'],':',color=truth_color,lw=lw)

    #### labels, format, scales !
    xmin = np.min(tvec[tvec>0.01])
    ymin = np.clip(ymin,ymax*1e-5,np.inf)

    axlim_sfh=[xmax*1.01, xmin*1.0001, ymin*.7, ymax*1.4]
    ax_inset.axis(axlim_sfh)
    ax_inset.set_ylabel(r'SFR [M$_{\odot}$/yr]',fontsize=axfontsize*3,labelpad=1.5*text_size)
    ax_inset.set_xlabel(r't$_{\mathrm{lookback}}$ [Gyr]',fontsize=axfontsize*3,labelpad=1.5*text_size)
    
    ax_inset.xaxis.set_minor_formatter(FormatStrFormatter('%2.5g'))
    ax_inset.xaxis.set_major_formatter(FormatStrFormatter('%2.5g'))
    ax_inset.set_xscale('log',subsx=([3]))
    ax_inset.set_yscale('log',subsy=([3]))
    ax_inset.tick_params('both', length=lw*3, width=lw*.6, which='both',labelsize=axfontsize*3)
    for axis in ['top','bottom','left','right']: ax_inset.spines[axis].set_linewidth(lw*.6)

    ax_inset.xaxis.set_minor_formatter(FormatStrFormatter('%2.5g'))
    ax_inset.xaxis.set_major_formatter(FormatStrFormatter('%2.5g'))
    ax_inset.yaxis.set_major_formatter(FormatStrFormatter('%2.5g'))

def spec_figure(sresults = None, eout = None,
                labels = ['model spectrum'],
                plot_maxprob=True,
                fig=None, spec=None, resid=None,
                **kwargs):
    """Plot the spectroscopy for the model and data (with error bars), and
    plot residuals
        -- pass in a list of [res], can iterate over them to plot multiple results
    good complimentary color for the default one is '#FF420E', a light red
    """

    # set up plot
    lw, alpha, fs, ticksize = 0.5, 0.8, kwargs.get('fs',16), kwargs.get('ticksize',12)
    textx, texty, deltay = kwargs.get('textx',0.02), kwargs.get('texty',.95), .05
    maxprob_color = 'red'
    posterior_median_color = '#1974D2'

    # iterate over results to plot
    for i,res in enumerate(sresults):

        # pull out data
        mask = res['obs']['mask']
        wave = res['obs']['wavelength'][mask] / 1e4
        specobs = res['obs']['spectrum'][mask]
        specobs_unc = res['obs']['unc'][mask]

        # model information
        modspec_lam = eout[i]['obs']['lam_obs'] / 1e4
        spec_pdf = np.zeros(shape=(modspec_lam.shape[0],3))
        for jj in range(spec_pdf.shape[0]): spec_pdf[jj,:] = np.percentile(eout[i]['obs']['spec'][:,jj],[16.0,50.0,84.0])
        modspec_lam = modspec_lam[mask]
        spec_pdf = spec_pdf[mask,:]

        # plot observations
        if i == 0:
            spec.errorbar(wave, specobs, #yerr=specobs_unc,
                         color=obs_color, label='observed', alpha=alpha, linestyle='-',lw=lw)

        # posterior median spectra
        spec.plot(modspec_lam, spec_pdf[:,1], linestyle='-',
                  color=posterior_median_color, alpha=alpha,label = 'posterior median', lw=lw)  
        spec.fill_between(modspec_lam, spec_pdf[:,0], spec_pdf[:,2],
                          color=posterior_median_color, alpha=0.3)
        resid.fill_between(modspec_lam, (specobs - spec_pdf[:,0]) / specobs_unc, (specobs - spec_pdf[:,2]) / specobs_unc,
                          color=posterior_median_color, alpha=0.3)

        # plot maximum probability model
        if plot_maxprob:
            spec_bfit = eout[i]['obs']['spec'][0,mask]
            spec.plot(modspec_lam, spec_bfit, color=maxprob_color, 
                      linestyle='-', label = 'best-fit', alpha=alpha, lw=lw)
            specchi = (specobs - spec_bfit) / specobs_unc
            resid.plot(modspec_lam, specchi, color=maxprob_color,
                       linestyle='-', lw=lw, alpha=alpha)        

        # calculate and show reduced chi-squared
        chisq = np.sum(specchi**2)
        ndof = mask.sum()
        reduced_chisq = chisq/(ndof)

        spec.text(textx, texty-deltay*(i+1), r'best-fit $\chi^2$/N$_{\mathrm{spec}}$='+"{:.2f}".format(reduced_chisq),
                  fontsize=10, ha='left',transform = spec.transAxes,color='black')

    # limits
    xlim = (wave.min()*0.95,wave.max()*1.05)
    for ax in [spec,resid]: ax.set_xlim(xlim)
    ymin, ymax = specobs.min()*0.9, specobs.max()*1.1
    spec.set_ylim(ymin, ymax)
    resid_ymax = np.min([np.abs(resid.get_ylim()).max(),5])
    resid.set_ylim(-resid_ymax,resid_ymax)

    # extra line
    resid.axhline(0, linestyle=':', color='grey')
    resid.yaxis.set_major_locator(MaxNLocator(5))

    # legend
    spec.legend(loc=4, prop={'size':8},
                scatterpoints=1,fancybox=True)
                
    # set labels
    resid.set_ylabel( r'$\chi$',fontsize=fs)
    spec.set_ylabel(r'$f_{\nu}$ [maggies]',fontsize=fs)
    resid.set_xlabel(r'$\lambda_{\mathrm{obs}}$ [$\mu$m]',fontsize=fs)
    resid.tick_params('both', pad=3.5, size=3.5, width=1.0, which='both',labelsize=ticksize)
    spec.tick_params('y', which='major', labelsize=ticksize)
    
    # set second x-axis (rest-frame wavelength)
    zred = eout[0]['thetas']['zred']['q50']
    y1, y2 = spec.get_ylim()
    x1, x2 = spec.get_xlim()
    ax2 = spec.twiny()
    ax2.set_xlim(x1/(1+zred), x2/(1+zred))
    ax2.set_xlabel(r'$\lambda_{\mathrm{rest}}$ [$\mu$m]',fontsize=fs)
    ax2.set_ylim(y1, y2)
    ax2.tick_params('both', pad=2.5, size=3.5, width=1.0, which='both',labelsize=ticksize)

    # remove ticks
    spec.set_xticklabels([])

def sed_figure(outname = None,
               colors = ['#1974D2'], sresults = None, eout = None,
               labels = ['model spectrum'],
               model_photometry = True, main_color=['black'],
               transcurves=False,
               ergs_s_cm=True, add_sfh=False,
               fig=None, phot=None, resid=None,
               **kwargs):
    """Plot the photometry for the model and data (with error bars), and
    plot residuals
        -- nondetections are plotted as downwards-pointing arrows
        -- pass in a list of [res], can iterate over them to plot multiple results
    good complimentary color for the default one is '#FF420E', a light red
    """

    # set up plot
    ms, alpha, fs, ticksize = 5, 0.8, kwargs.get('fs',16), kwargs.get('ticksize',12)
    textx, texty, deltay = kwargs.get('textx',0.02), kwargs.get('texty',.925), .05

    # if we have multiple parts, color ancillary data appropriately
    if len(colors) > 1:
        main_color = colors

    # iterate over results to plot
    for i,res in enumerate(sresults):

        # pull out data
        mask = res['obs']['phot_mask']
        phot_wave_eff = res['obs']['wave_effective'][mask]
        obsmags = res['obs']['maggies'][mask]
        obsmags_unc = res['obs']['maggies_unc'][mask]

        # model information
        zred = res['model'].params['zred'][0]
        modmags_bfit = eout[i]['obs']['mags'][0,mask]
        modspec_lam = eout[i]['obs']['lam_obs']
        if (res['obs'].get('spectrum',None) != None):
            modspec_lam /= (1+zred)
        nspec = modspec_lam.shape[0]
        try:
            spec_pdf = np.zeros(shape=(nspec,3))
            if 'zred' in res['theta_labels']: # renormalize if we're fitting redshift
                zred_draw = res['chain'][eout[i]['sample_idx'],res['theta_labels'].index('zred')]
                #eout[i]['obs']['spec'] *= (1+zred_draw)[:,None]
            for jj in range(spec_pdf.shape[0]): spec_pdf[jj,:] = np.percentile(eout[i]['obs']['spec'][:,jj],[16.0,50.0,84.0])
        except:
            spec_pdf = np.stack((eout[i]['obs']['spec']['q16'],eout[i]['obs']['spec']['q50'],eout[i]['obs']['spec']['q84']),axis=1)

        # units
        factor = 3e18
        if ergs_s_cm:
            factor *= 3631*1e-23

        # photometry
        modmags_bfit *= factor/phot_wave_eff
        obsmags *= factor/phot_wave_eff
        obsmags_unc *= factor/phot_wave_eff
        photchi = (obsmags-modmags_bfit)/obsmags_unc
        phot_wave_eff /= 1e4

        # spectra
        spec_pdf *= (factor/modspec_lam/(1+zred)).reshape(nspec,1)
        modspec_lam = modspec_lam*(1+zred)/1e4
        spec_pdf /= (1+zred) # added for special case
        modspec_lam *= (1+zred) # added for special case

        # plot maximum probability model
        if model_photometry:
            phot.plot(phot_wave_eff, modmags_bfit, color=colors[i], 
                      marker='o', ms=ms, linestyle=' ', label = 'model photometry', alpha=alpha, 
                      markeredgecolor='k')
        
        resid.plot(phot_wave_eff, photchi, color=colors[i],
                 marker='o', linestyle=' ', label=labels[i], 
                 ms=ms,alpha=alpha,markeredgewidth=0.7,markeredgecolor='k')        

        # model spectra
        yplt = spec_pdf[:,1]
        pspec = smooth_spectrum(modspec_lam*1e4,yplt,200,minlam=1e3,maxlam=1e5)
        nz = pspec > 0
        phot.plot(modspec_lam[nz], pspec[nz], linestyle='-',
                  color=colors[i], alpha=0.9,zorder=-1,label = labels[i])  
        phot.fill_between(modspec_lam[nz], spec_pdf[nz,0], spec_pdf[nz,2],
                          color=colors[i], alpha=0.3,zorder=-1)

        # calculate and show reduced chi-squared
        chisq = np.sum(photchi**2)
        ndof = mask.sum()
        reduced_chisq = chisq/(ndof)

        phot.text(textx, texty-deltay*i, r'best-fit $\chi^2$/N$_{\mathrm{phot}}$='+"{:.2f}".format(reduced_chisq),
                  fontsize=10, ha='left',transform = phot.transAxes,color=main_color[i])

    # plot observations
    pflux = obsmags > 0
    phot.errorbar(phot_wave_eff[pflux], obsmags[pflux], yerr=obsmags_unc[pflux],
                  color=obs_color, marker='o', label='observed', alpha=alpha, linestyle=' ',ms=ms,
                  zorder=0,markeredgecolor='k')

    # limits
    xlim = (phot_wave_eff[pflux].min()*0.5,phot_wave_eff[pflux].max()*3)
    phot.set_xlim(xlim)
    resid.set_xlim(xlim)
    ymin, ymax = obsmags[pflux].min()*0.5, obsmags[pflux].max()*2

    # add transmission curves
    if transcurves:
        dyn = 10**(np.log10(ymin)+(np.log10(ymax)-np.log10(ymin))*0.2)
        for f in res['obs']['filters']: phot.plot(f.wavelength/1e4, f.transmission/f.transmission.max()*dyn+ymin,lw=1.5,color='0.3',alpha=0.7)

    # add in arrows for negative fluxes
    if pflux.sum() != len(obsmags):
        downarrow = [u'\u2193']
        y0 = 10**((np.log10(ymax) - np.log10(ymin))/20.)*ymin
        for x0 in phot_wave_eff[~pflux]: phot.plot(x0, y0, linestyle='none',marker=u'$\u2193$',markersize=16,alpha=alpha,mew=0.5,mec='k',color=obs_color)
    phot.set_ylim(ymin, ymax)
    resid_ymax = np.abs(resid.get_ylim()).max()
    resid.set_ylim(-resid_ymax,resid_ymax)

    # redshift text
    if 'zred' not in sresults[0]['theta_labels']:
        phot.text(textx, texty-deltay, 'z='+"{:.2f}".format(zred),
                  fontsize=10, ha='left',transform = phot.transAxes)
    
    # extra line
    resid.axhline(0, linestyle=':', color='grey')
    resid.yaxis.set_major_locator(MaxNLocator(5))

    # legend
    leg = phot.legend(loc=kwargs.get('legend_loc',0), prop={'size':8},
                      scatterpoints=1,fancybox=True)

    # set labels
    resid.set_ylabel( r'$\chi$',fontsize=fs)
    if ergs_s_cm:
        phot.set_ylabel(r'$\nu f_{\nu}$ [erg/s/cm$^2$]',fontsize=fs)
    else:
        phot.set_ylabel(r'$\nu f_{\nu}$ [maggie Hz]',fontsize=fs)
    resid.set_xlabel(r'$\lambda_{\mathrm{obs}}$ [$\mu$m]',fontsize=fs)
    phot.set_yscale('log',nonposy='clip')
    phot.set_xscale('log',nonposx='clip')
    resid.set_xscale('log',nonposx='clip',subsx=(2,5))
    resid.xaxis.set_minor_formatter(FormatStrFormatter('%2.4g'))
    resid.xaxis.set_major_formatter(FormatStrFormatter('%2.4g'))
    resid.tick_params('both', pad=3.5, size=3.5, width=1.0, which='both',labelsize=ticksize)
    phot.tick_params('y', which='major', labelsize=ticksize)
    
    # set second x-axis (rest-frame wavelength)
    if 'zred' not in sresults[0]['theta_labels']:
        y1, y2=phot.get_ylim()
        x1, x2=phot.get_xlim()
        ax2=phot.twiny()
        ax2.set_xticks(np.arange(0,10,0.2))
        ax2.set_xlim(x1/(1+zred), x2/(1+zred))
        ax2.set_xlabel(r'$\lambda_{\mathrm{rest}}$ [$\mu$m]',fontsize=fs)
        ax2.set_ylim(y1, y2)
        ax2.set_xscale('log',nonposx='clip',subsx=(2,5))
        ax2.xaxis.set_minor_formatter(FormatStrFormatter('%2.4g'))
        ax2.xaxis.set_major_formatter(FormatStrFormatter('%2.4g'))
        ax2.tick_params('both', pad=2.5, size=3.5, width=1.0, which='both',labelsize=ticksize)

    # remove ticks
    phot.set_xticklabels([])
    
    # add SFH 
    if add_sfh:
        sfh_ax = fig.add_axes([0.425,0.4,0.15,0.2],zorder=32)
        add_sfh_plot(eout, fig,
                     main_color = ['black'],
                     ax_inset=sfh_ax,
                     text_size=0.45,lw=1.13)

    if outname is not None:
        fig.savefig(outname, bbox_inches='tight', dpi=180)
        plt.close()

def plt_chisq_comp(res,eout):

    # pull out information
    spec_jitter = res['chain'][eout['sample_idx'],res['theta_labels'].index('spec_jitter')]
    obsspec = res['obs']['spectrum']
    obsunc = spec_jitter[:,None] * res['obs']['unc'][None,:]
    obsunc = res['obs']['unc']
    obslam = res['obs']['wavelength']
    modspec = eout['obs']['spec']

    # pull out photometric information
    mask = res['obs']['phot_mask']
    obsmags = res['obs']['maggies'][mask]
    obsmags_unc = res['obs']['maggies_unc'][mask]
    modmags = eout['obs']['mags'][:,mask]
    photchi = (((obsmags-modmags)/obsmags_unc)**2).sum(axis=1)


    # calculate chi^2_spec, chi^2_phot
    chi2 = (((obsspec-modspec)/obsunc)**2)
    print 1/0

def make_all_plots(filebase=None,
                   outfolder=os.getenv('APPS')+'/prospector_alpha/plots/',
                   plt_summary=False,
                   plt_trace=False,
                   plt_corner=True,
                   plt_sed=True,
                   **opts):
    """Makes basic dynesty diagnostic plots for a single galaxy.
    """

    # make sure the output folder exists
    if not os.path.isdir(outfolder):
        os.makedirs(outfolder)

    # load galaxy output.
    objname = filebase.split('/')[-1]
    try:
        res, powell_results, model, eout = load_prospector_data(filebase, hdf5=True)
    except IOError,TypeError:
        print 'failed to load results for {0}'.format(objname)
        return

    if (res is None) or (eout is None):
        return

    # restore model
    if res['model'] is None:
        from prospect.models import model_setup
        # make filenames local
        for key in res['run_params']:
            if type(res['run_params'][key]) == unicode:
                if 'prospector_alpha' in res['run_params'][key]:
                    res['run_params'][key] = os.getenv('APPS')+'/prospector_alpha'+res['run_params'][key].split('prospector_alpha')[-1]
        pfile = model_setup.import_module_from_file(res['run_params']['param_file'])
        res['model'] = pfile.load_model(**res['run_params'])
        pfile = None

    for key in res['obs'].keys(): res['obs'][key] = np.array(res['obs'][key])
    
    # transform to preferred model variables
    res['chain'], parnames = transform_chain(res['chain'],res['model'])

    # mimic dynesty outputs
    res['logwt'] = (np.log(res['weights'])+res['logz'][-1]).astype(np.float64)
    res['logl'] = (res['lnlikelihood']).astype(np.float64)
    res['samples'] = (res['chain']).astype(np.float64)
    res['nlive'] = res['run_params']['nested_nlive_init']
    font_kwargs = {'fontsize': fs}

    if False:
        plt_chisq_comp(res,eout)

    # Plot a summary of the run.
    if plt_summary:
        print 'making SUMMARY plot'
        rfig, raxes = dyplot.runplot(res, mark_final_live=False, label_kwargs=font_kwargs, span=[0.00001,0.00001,0.00001,(1e7,1e8)])
        for ax in raxes:
            ax.xaxis.set_tick_params(labelsize=tick_fs)
            ax.yaxis.set_tick_params(labelsize=tick_fs)
            ax.yaxis.get_offset_text().set_size(fs)
        rfig.tight_layout()
        rfig.savefig(outfolder+objname+'_dynesty_summary.pdf',dpi=100)

    # Plot traces and 1-D marginalized posteriors.
    if plt_trace:
        print 'making TRACE plot'
        tfig, taxes = dyplot.traceplot(res, labels=parnames,label_kwargs=font_kwargs)
        for ax in taxes.ravel():
            ax.xaxis.set_tick_params(labelsize=tick_fs)
            ax.yaxis.set_tick_params(labelsize=tick_fs)
        tfig.tight_layout()
        tfig.savefig(outfolder+objname+'_dynesty_trace.pdf',dpi=100)

    # corner plot
    if plt_corner: 
        print 'making CORNER plot'
        subcorner(res, eout, parnames,outname=outfolder+objname, **opts)

    # sed plot
    if plt_sed:
        print 'making SED plot'

        # plot geometry based on whether
        # spectra are being fit or not
        if (res['obs'].get('spectrum',None) != None):
            fig = plt.figure(figsize=(15,5))
            gs = gridspec.GridSpec(2,2, height_ratios=[3,1],width_ratios=[1,2])
            gs.update(hspace=0)
            phot, spec, resid, sresid = [plt.Subplot(fig, gs[i]) for i in range(4)]
            for ax in [phot, spec, resid, sresid]: fig.add_subplot(ax)

            spec_figure(sresults = [res], eout=[eout],
                        fig=fig, spec=spec, resid=sresid, **opts)

        else:
            fig = plt.figure()
            gs = gridspec.GridSpec(2,1, height_ratios=[3,1])
            gs.update(hspace=0)
            phot, resid = plt.Subplot(fig, gs[0]), plt.Subplot(fig, gs[1])
            fig.add_subplot(phot)
            fig.add_subplot(resid)

        _ = sed_figure(sresults = [res], eout=[eout],
                       outname=outfolder+objname+'.sed.pdf',
                       fig=fig, phot=phot, resid=resid, **opts)
        
def do_all(runname=None,nobase=True,**extras):
    """for a list of galaxies, make all plots
    the runname has to be accepted by generate_basenames
    extra arguments go to make_all_plots
    """
    if nobase:
        filebase = find_all_prospector_results(runname)
    else:
        filebase, _, _ = prosp_dutils.generate_basenames(runname)
    for jj in range(len(filebase)):
        print 'iteration '+str(jj) 

        make_all_plots(filebase=filebase[jj],\
                       outfolder=os.getenv('APPS')+'/prospector_alpha/plots/'+runname+'/',
                       **extras)
    