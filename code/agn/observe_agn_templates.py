import numpy as np
import os
from sedpy.observate import getSED,load_filters
import matplotlib.patheffects as pe

lightspeed = 2.998e18  # AA/s

def load_data():

    loc = os.getenv('SPS_HOME')+'/dust/Nenkova08_y010_torusg_n10_q2.0.dat'

    hdr = ['blank','lambda',5,10,20,30,40,60,80,100,150]
    dat = np.loadtxt(loc, comments = '#', delimiter='   ',skiprows=4,
                     dtype = {'names':([str(n) for n in hdr]),\
                              'formats':(np.concatenate((np.atleast_1d('S4'),np.repeat('float64',10))))})

    return dat

def get_cmap(N):

    import matplotlib.cm as cmx
    import matplotlib.colors as colors

    '''Returns a function that maps each index in 0, 1, ... N-1 to a distinct 
    RGB color.'''
    color_norm  = colors.Normalize(vmin=0, vmax=N-1)
    scalar_map = cmx.ScalarMappable(norm=color_norm, cmap='plasma') 
    def map_index_to_rgb_color(index):
        return scalar_map.to_rgba(index)
    return map_index_to_rgb_color

def plot(ax):

    import matplotlib.pyplot as plt
    import magphys_plot_pref

    minorFormatter = magphys_plot_pref.jLogFormatter(base=10, labelOnlyBase=False)
    majorFormatter = magphys_plot_pref.jLogFormatter(base=10, labelOnlyBase=True)

    dat = load_data()

    #fig, ax = plt.subplots(1,1, figsize=(6, 5))
    template_names = dat.dtype.names[2:]
    cmap = get_cmap(len(template_names))
    to_plot = ['5','10','20','40','150']

    for i,name in enumerate(template_names):

        if (name == 'blank') or (name == 'lambda') or (name not in to_plot):
            continue
        
        ### define plotting stuff
        good = dat[name] > 0
        xplot = dat['lambda'][good]/1e4 
        yplot = dat[name][good] * 3e18*3631*1e-23/dat['lambda'][good]

        ### normalize
        onemicron = np.abs(xplot-1.).argmin()
        yplot /= yplot[onemicron]

        ax.plot(xplot,yplot,
                label=name,lw=2.5,color=cmap(i),
                path_effects=[pe.Stroke(linewidth=4.5, foreground='k',alpha=0.7), pe.Normal()],zorder=-i)

    ax.legend(title=r'$\tau_{\mathrm{AGN}}$',loc=2,prop={'size':10},frameon=False,ncol=2)
    ax.set_ylabel(r'$\nu$f$_{\nu}$ [normalized]')
    ax.set_xlabel(r'wavelength [$\mu$m]')
    ax.text(0.95,0.93,'AGN only',weight='semibold',transform=ax.transAxes,ha='right',fontsize=16)

    ax.set_xscale('log',nonposx='clip',subsx=(1,3))
    ax.xaxis.set_minor_formatter(minorFormatter)
    ax.xaxis.set_major_formatter(majorFormatter)
    for tl in ax.get_xticklabels():tl.set_visible(False)

    ax.set_yscale('log',nonposy='clip',subsy=(1,2,4))
    ax.xaxis.set_minor_formatter(minorFormatter)
    ax.xaxis.set_major_formatter(majorFormatter)
    for tl in ax.get_yticklabels():tl.set_visible(False)
    ax.set_xlim(0.5,200)
    in_bounds = (xplot > 1) & (xplot < 200)
    ax.set_ylim(yplot[in_bounds].min()*0.9, yplot[in_bounds].max()*20)

    '''
    outname = '/Users/joel/code/python/prospector_alpha/plots/brownseds_agn/agn_plots/agn_templates.png'
    plt.tight_layout()
    plt.savefig(outname,dpi=150)
    import os
    os.system('open '+outname)
    plt.close()
    '''

def observe(fnames):

    #  units: lambda (A), flux: fnu normalized to unity
    dat = load_data()
    filters = load_filters(fnames)

    out = {}
    for name in dat.dtype.names:
        if name == 'blank' or name == 'lambda':
            continue

        # sourcewave: Spectrum wavelength (in AA), ndarray of shape (nwave).
        # sourceflux: Associated flux (assumed to be in erg/s/cm^2/AA), ndarray of shape (nsource,nwave).
        # filterlist: List of filter objects, of length nfilt.
        # array of AB broadband magnitudes, of shape (nsource, nfilter).
        out[name] = getSED(dat['lambda'], (lightspeed/dat['lambda']**2)*dat[name], filters)

    return out
