import numpy as np
import matplotlib.pyplot as plt
from select_td_sample import load_master_sample
import os, hickle
from matplotlib.ticker import FormatStrFormatter
import matplotlib.gridspec as gridspec

plt.ioff()

def setup_gridspec():
    """ function written to HIDE THIS UGLY CODE
    """
    fig = plt.figure(figsize=(10.5,3))

    left, top = 0.08,0.98 # margins

    sedax, resax = [], []
    axwid, axheight, delx = 0.21, 0.8, 0.0

    left = [left, left+axwid, left+axwid*2, left+axwid*3]
    right = [left[0]+axwid, left[1]+axwid, left[2]+axwid, left[3]+axwid]
    top = np.repeat(top,4)
    bot = np.repeat(top-axheight,4)
    for i in xrange(4):
        gs = gridspec.GridSpec(2,1, height_ratios=[2,1])
        gs.update(left=left[i],right=right[i],bottom=bot[i],top=top[i],hspace=0)
        ax_sed, ax_res = plt.Subplot(fig, gs[0]), plt.Subplot(fig, gs[1])
        fig.add_subplot(ax_sed)
        fig.add_subplot(ax_res)

        sedax.append(ax_sed)
        resax.append(ax_res)

    sedax, resax = np.array(sedax), np.array(resax)
    return fig, sedax, resax

def load_master(filename=None,regenerate=False,sids=None):
    """ we try to load it first because it's big
    """
    if os.path.isfile(filename) and regenerate == False:
        with open(filename, "r") as f:
            outdict = hickle.load(f)
    else:
        outdict = load_master_sample()
        outdict['sidx'] = np.array([outdict['id'].index(name) for name in sids])
        hickle.dump(outdict,open(filename, "w"))

    return outdict

def select_huge(dat):
    idx = np.where(((dat['z_best_u68'] - dat['z_best_l68'])/2. < 0.1) & \
                   (dat['f_F160W'] / dat['e_F160W'] > 10) & \
                   (dat['zbest'] - dat['fast_z'] < 0.01)) # this SHOULDN'T matter but some of the FAST z's are not zbest!
    return idx

def select_huge_supp(dat):
    idx = np.where(((dat['z_best_u68'] - dat['z_best_l68'])/2. < 0.25) & \
                   (dat['f_F160W'] / dat['e_F160W'] > 10) & \
                   (dat['zbest'] >= 0.5) & (dat['zbest'] <= 2.5))
    return idx

def do_all(runname='td_huge',outfolder=None,regenerate=False,**opts):
    """compare sample selection to parent 3D-HST sample
    this is defined as (parent = phot_flag == 1)
    """

    # folder maintenance
    if outfolder is None:
        outfolder = os.getenv('APPS') + '/prospector_alpha/plots/'+runname+'/fast_plots/'
        if not os.path.isdir(outfolder):
            os.makedirs(outfolder)
            os.makedirs(outfolder+'data/')

    # load master sample + sample IDs
    sids = np.genfromtxt('/Users/joel/code/python/prospector_alpha/data/3dhst/'+runname+'.ids',
                         dtype=[('objnames', '|S40')])['objnames'].tolist()
    data = load_master(filename=outfolder+'data/master.hickle',regenerate=regenerate,sids=sids)

    for key in data: data[key] = np.array(data[key])
    # plot
    plot(data, outfolder=outfolder,**opts)

def plot(data, outfolder=None, density_plot=False, verbose=False, reselect_sample=True, completeness_plot=True):
    """density_plot: bool
        include (x*N) where x is the parameter of interest

    verbose: bool
        print mass completeness for each redshift

    reselect_sample: bool
        redo the sample selection within this program
        useful for designing new samples
    """

    ### physics choices
    zbins = [(0.5,1.),(1.,1.5),(1.5,2.),(2.,2.5)]
    basename = ''
    if density_plot:
        basename = '_with_density'
    mass_options = {
                    'data': data['fast_logmass'],
                    'xlim': (8,11.8),
                    'ylim': (30,6000),
                    'ylabel': r'N*M$_{\mathrm{stellar}}$',
                    'xlabel': r'log(M$_*$/M$_{\odot}$)',
                    'norm': 1e13, # this is arbitrary, to remove power from matplotlib y-axis
                    'name': 'rhomass_selection'+basename+'.png'
                   }

    sfr_options = {
                    'data': np.log10(np.clip(data['uvir_sfr'],0.001,np.inf)),
                    'xlim': (-2,5),
                    'ylim': (30,6000),
                    'ylabel': r'N*SFR',
                    'xlabel': r'log(SFR) [M$_{\odot}$/yr]',
                    'norm': 1e4, # this is arbitrary, to remove power from matplotlib y-axis
                    'name': 'rhosfr_selection'+basename+'.png'
                   }

    ### plot choices
    nbins = 20
    histopts = {'drawstyle':'steps-mid','alpha':1.0, 'lw':1, 'linestyle': '-'}
    fontopts = {'fontsize':10}

    # plot mass + mass density distribution
    for opt in [mass_options,sfr_options]:
        if density_plot:
            fig, ax = plt.subplots(2,4,figsize=(5,9))
        elif completeness_plot:
            fig, ax, axcomp = setup_gridspec()
            ax = np.atleast_2d(ax).T
        else:
            fig, ax = plt.subplots(1,4,figsize=(10.5,3))
            ax = np.atleast_2d(ax).T
        for i,zbin in enumerate(zbins):

            # define sample
            if reselect_sample:
                #sample_idx = select_huge(data)
                sample_idx = select_huge_supp(data)
            else:
                sample_idx = [data['sidx']]

            # define indexes
            idx = (data['zbest'] > zbin[0]) & \
                  (data['zbest'] < zbin[1]) & \
                  (opt['data'] > opt['xlim'][0]) & \
                  (opt['data'] < opt['xlim'][1])
            sidx = (data['zbest'][sample_idx] >= zbin[0]) & \
                   (data['zbest'][sample_idx] <= zbin[1]) & \
                   (opt['data'][sample_idx] > opt['xlim'][0]) & \
                   (opt['data'][sample_idx] < opt['xlim'][1])

            # pull out mass or SFR
            master_dat = opt['data'][idx]
            sample_dat = opt['data'][sample_idx][sidx]

            # histograms. get bins from master histogram
            hist_master, bins = np.histogram(master_dat,bins=nbins,density=False)
            hist_sample, bins = np.histogram(sample_dat,bins=bins,density=False)
            bins_mid = (bins[1:]+bins[:-1])/2.

            # distribution
            ax[i,0].plot(bins_mid,hist_master,color='0.4', **histopts)
            ax[i,0].plot(bins_mid,hist_sample,color='red', **histopts)

            # axis labels
            for a in ax[i,:]: 
                a.set_ylim(opt['ylim'])
                a.set_xlim(opt['xlim'])
                a.set_yscale('log',nonposy='clip',subsy=([3]))
                a.yaxis.set_minor_formatter(FormatStrFormatter('%2.4g'))
                a.yaxis.set_major_formatter(FormatStrFormatter('%2.4g'))
            if i > 0:
                for a in ax[i,:]: 
                    a.set_yticklabels([])
                    plt.setp(a.get_yminorticklabels(), visible=False)

            # text labels
            rhofrac = (10**sample_dat).sum() / (10**master_dat).sum()
            ax[i,0].text(0.98, 0.9,'{:1.1f} < z < {:1.1f}'.format(zbin[0],zbin[1]), transform=ax[i,0].transAxes,ha='right',**fontopts)

            # density distribution
            if density_plot:
                ax[i,1].plot(bins_mid,hist_master*10**bins_mid/opt['norm'],color='0.4', **histopts)
                ax[i,1].plot(bins_mid,hist_sample*10**bins_mid/opt['norm'],color='red', **histopts)
                ax[i,1].set_ylabel(opt['ylabel'])
                ax[i,1].text(0.01, 0.925,r'$\rho_{\mathrm{sample}}/\rho_{\mathrm{total}}$='+'{:1.2f}'.format(rhofrac),
                             transform=ax[i,1].transAxes,ha='left',**fontopts)
            else:
                ax[i,0].text(0.98, 0.82,r'$\rho_{\mathrm{sample}}/\rho_{\mathrm{total}}$='+'{:1.2f}'.format(rhofrac),
                             transform=ax[i,0].transAxes,ha='right',**fontopts)

            # completeness distribution
            if completeness_plot:
                axcomp[i].plot(bins_mid, hist_sample / hist_master.astype(float), lw=1.5,color='k')
                axcomp[i].axhline(0.9,linestyle='--',color='0.5',zorder=-1,alpha=0.8)
                axcomp[i].set_xlabel(opt['xlabel'])
                axcomp[i].set_xlim(opt['xlim'])
                axcomp[i].set_ylim(0.5,1.1)
                
                # y-labels
                if i > 0:
                    axcomp[i].set_yticklabels([])
                    plt.setp(axcomp[i].get_yminorticklabels(), visible=False)
                else: 
                    axcomp[i].set_ylabel('completeness')

                # turn off xticks in above plot
                for a in ax[i,:]: a.set_xticklabels([])

            else:
                for a in ax[i,:]: a.set_xlabel(opt['xlabel'])

            if (verbose):
                if i == 0:
                    count = len(sample_dat)
                else:
                    count += len(sample_dat)

        if (verbose):
            print '{0} extra galaxies to fit'.format(count-39334)

        ax[0,0].set_ylabel(r'N$_{\mathrm{galaxies}}$')

        if not completeness_plot:
            fig.tight_layout()
            fig.subplots_adjust(wspace=0.0)
        fig.savefig(outfolder+opt['name'],dpi=150)
        plt.close()