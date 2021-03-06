import numpy as np
import os
from prospect.models import priors, sedmodel
from prospect.sources import FastStepBasis
from sedpy import observate
from astropy.cosmology import WMAP9
from astropy import constants
from scipy.stats import truncnorm
from astropy.io import ascii
from astropy.io import fits

#############
# RUN_PARAMS
#############
APPS = os.getenv('APPS')
run_params = {'verbose':True,
              'debug': False,
              'outfile': os.getenv('APPS')+'/prospector_alpha/results/brownseds_highz/brownseds_highz',
              'nofork': True,
              # dynesty params
              'nested_bound': 'multi', # bounding method
              'nested_sample': 'rwalk', # sampling method
              'nested_walks': 50, # MC walks
              'nested_nlive_batch': 200, # size of live point "batches"
              'nested_nlive_init': 200, # number of initial live points
              'nested_weight_kwargs': {'pfrac': 1.0}, # weight posterior over evidence by 100%
              'nested_dlogz_init': 0.01,
              # Model info
              'zcontinuous': 2,
              'compute_vega_mags': False,
              'initial_disp':0.1,
              'interp_type': 'logarithmic',
              'agelims': [0.0,8.0,8.5,9.0,9.5,9.8,10.0],
              # Data info
              'datname':os.getenv('APPS')+'/prospector_alpha/data/brownseds_data/photometry/table1.fits',
              'photname':os.getenv('APPS')+'/prospector_alpha/data/brownseds_data/photometry/table3.txt',
              'extinctname':os.getenv('APPS')+'/prospector_alpha/data/brownseds_data/photometry/table4.fits',
              'herschname':os.getenv('APPS')+'/prospector_alpha/data/brownseds_data/photometry/kingfish.brownapertures.flux.fits',
              'objname':'Arp 256 N',
              }

############
# OBS
#############

def translate_filters(bfilters, full_list = False):
    """translate filter names to FSPS standard
    """

    # this is necessary for my code
    # to calculate effective wavelength
    translate = {
    'FUV': 'GALEX FUV',
    'UVW2': 'UVOT w2',
    'UVM2': 'UVOT m2',
    'NUV': 'GALEX NUV',
    'UVW1': 'UVOT w1',
    'Umag': np.nan,    # [11.9/15.7]? Swift/UVOT U AB band magnitude
    'umag': 'SDSS Camera u Response Function, airmass = 1.3 (June 2001)',
    'gmag': 'SDSS Camera g Response Function, airmass = 1.3 (June 2001)',
    'Vmag': np.nan,    # [10.8/15.6]? Swift/UVOT V AB band magnitude
    'rmag': 'SDSS Camera r Response Function, airmass = 1.3 (June 2001)',
    'imag': 'SDSS Camera i Response Function, airmass = 1.3 (June 2001)',
    'zmag': 'SDSS Camera z Response Function, airmass = 1.3 (June 2001)',
    'Jmag': '2MASS J filter (total response w/atm)',
    'Hmag': '2MASS H filter (total response w/atm)',
    'Ksmag': '2MASS Ks filter (total response w/atm)',
    'W1mag': 'WISE W1',
    '[3.6]': 'IRAC Channel 1',
    '[4.5]': 'IRAC Channel 2',
    'W2mag': 'WISE W2',
    '[5.8]': 'IRAC Channel 3',
    '[8.0]': 'IRAC CH4',
    'W3mag': 'WISE W3',
    'PUIB': np.nan,    # [8.2/15.6]? Spitzer/IRS Blue Peak Up Imaging channel (13.3-18.7um) AB magnitude
    'W4mag': np.nan,    # two WISE4 magnitudes, what is the correction?
    "W4'mag": 'WISE W4',
    'PUIR': np.nan,    # Spitzer/IRS Red Peak Up Imaging channel (18.5-26.0um) AB magnitude
    '[24]': 'MIPS 24um',
    'pacs70': 'Herschel PACS 70um',
    'pacs100': 'Herschel PACS 100um',
    'pacs160': 'Herschel PACS 160um',
    'spire250': 'Herschel SPIRE 250um',
    'spire350': 'Herschel SPIRE 350um',
    'spire500': 'Herschel SPIRE 500um'
    }

    # this translates filter names
    # to names that FSPS recognizes
    translate_pfsps = {
    'FUV': 'galex_FUV',
    'UVW2': 'uvot_w2',
    'UVM2': 'uvot_m2',
    'NUV': 'galex_NUV',
    'UVW1': 'uvot_w1',
    'Umag': np.nan,    # [11.9/15.7]? Swift/UVOT U AB band magnitude
    'umag': 'sdss_u0',
    'gmag': 'sdss_g0',
    'Vmag': np.nan,    # [10.8/15.6]? Swift/UVOT V AB band magnitude
    'rmag': 'sdss_r0',
    'imag': 'sdss_i0',
    'zmag': 'sdss_z0',
    'Jmag': 'twomass_J',
    'Hmag': 'twomass_H',
    'Ksmag': 'twomass_Ks',
    'W1mag': 'wise_w1',
    '[3.6]': 'spitzer_irac_ch1',
    '[4.5]': 'spitzer_irac_ch2',
    'W2mag': 'wise_w2',
    '[5.8]': 'spitzer_irac_ch3',
    '[8.0]': 'spitzer_irac_ch4',
    'W3mag': 'wise_w3',
    'PUIB': np.nan,    # [8.2/15.6]? Spitzer/IRS Blue Peak Up Imaging channel (13.3-18.7um) AB magnitude
    'W4mag': np.nan,    # two WISE4 magnitudes, this one is "native" and must be corrected
    "W4'mag": 'wise_w4',
    'PUIR': np.nan,    # Spitzer/IRS Red Peak Up Imaging channel (18.5-26.0um) AB magnitude
    '[24]': 'spitzer_mips_24',
    'pacs70': 'herschel_pacs_70',
    'pacs100': 'herschel_pacs_100',
    'pacs160': 'herschel_pacs_160',
    'spire250': 'herschel_spire_250',
    'spire350': 'herschel_spire_350',
    'spire500': 'herschel_spire_500'
    }

    if full_list:
        return translate_pfsps.values()
    else:
        return np.array([translate[f] for f in bfilters]), np.array([translate_pfsps[f] for f in bfilters])


def load_obs(photname='', extinctname='', herschname='', objname='', mask_ir=True, 
             elines=False, errfloor=0.05, **extras):
    """
    let's do this
    """
    obs ={}

    with open(photname, 'r') as f:
        hdr = f.readline().split()
    dtype = np.dtype([(hdr[1],'S20')] + [(n, np.float) for n in hdr[2:]])
    dat = np.loadtxt(photname, comments = '#', delimiter='\t',
                     dtype = dtype)
    obj_ind = np.where(dat['id'] == objname)[0][0]

    # extract fluxes+uncertainties for all objects and all filters
    mag_fields = [f for f in dat.dtype.names if f[0:2] != 'e_' and (f != 'id')]
    magunc_fields = [f for f in dat.dtype.names if f[0:2] == 'e_']

    # extract fluxes for particular object, converting from record array to numpy array
    mag = np.array([f for f in dat[mag_fields][obj_ind]])
    magunc  = np.array([f for f in dat[magunc_fields][obj_ind]])

    # extinctions
    extinct = fits.open(extinctname)
    extinctions = np.array([np.squeeze(extinct[1].data[f][obj_ind]) for f in extinct[1].columns.names if f != 'Name'])

    # adjust fluxes for extinction
    mag_adj = mag - extinctions

    # add correction to MIPS magnitudes (only MIPS 24 right now!)
    mips_corr = np.array([-0.03542,-0.07669,-0.03807]) # 24, 70, 160
    mag_adj[mag_fields.index('[24]') ] += mips_corr[0]

    # then convert to maggies
    flux = 10**((-2./5)*mag_adj)

    # convert uncertainty to maggies
    unc = magunc*flux/1.086

    #### Herschel photometry
    # find fluxes + errors
    herschel = fits.open(herschname)
    hflux_fields = [f for f in herschel[1].columns.names if (('pacs' in f) or ('spire' in f)) and f[-3:] != 'unc']
    hunc_fields = [f for f in herschel[1].columns.names if (('pacs' in f) or ('spire' in f)) and f[-3:] == 'unc']

    # different versions if objname is passed or no
    if objname is not None:
        match = herschel[1].data['Name'] == objname.lower().replace(' ','')
        
        hflux = np.array([np.squeeze(herschel[1].data[match][hflux_fields[i]]) for i in xrange(len(hflux_fields))])
        hunc = np.array([np.squeeze(herschel[1].data[match][f]) for f in hunc_fields])
    else:
        optnames = hdulist[1].data['Name']
        hnames   = herschel[1].data['Name']

        # non-pythonic, but why change if it works?
        hflux,hunc = np.zeros(shape=(len(hflux_fields),len(hnames))), np.zeros(shape=(len(hflux_fields),len(hnames)))
        for ii in xrange(len(optnames)):
            match = hnames == optnames[ii].lower().replace(' ','')
            for kk in xrange(len(hflux_fields)):
                hflux[kk,ii] = herschel[1].data[match][hflux_fields[kk]]
                hunc[kk,ii]  = herschel[1].data[match][hunc_fields[kk]]

    #### combine with brown catalog
    # convert from Jy to maggies
    flux = np.concatenate((flux,hflux/3631.))   
    unc = np.concatenate((unc, hunc/3631.))
    mag_fields = np.append(mag_fields,hflux_fields)   

    # phot mask
    phot_mask_brown = mag != 0
    phot_mask_hersch = hflux != 0
    phot_mask = np.concatenate((phot_mask_brown,phot_mask_hersch))

    # map brown filters to FSPS filters
    # and remove fluxes where we don't have filter definitions
    filters,fsps_filters = translate_filters(mag_fields)
    have_definition = np.array(filters) != 'nan'

    fsps_filters = fsps_filters[have_definition]
    flux = flux[have_definition]
    unc = unc[have_definition]
    phot_mask = phot_mask[have_definition]

    # implement error floor
    unc = np.clip(unc, flux*errfloor, np.inf)
    w3_idx = fsps_filters == 'wise_w3'
    unc[w3_idx] = np.clip(unc[w3_idx], flux[w3_idx]*0.3, np.inf) # for the silicate feature

    # mask filters redwards of 12 um
    filters = observate.load_filters(fsps_filters)
    wave_effective = np.array([filt.wave_effective for filt in filters])
    if mask_ir:
        print 'masking IR data'
        phot_mask[wave_effective > 12e4] = False

    # add elines
    # load fsps emission line list for index
    if elines:
        loc = os.getenv('SPS_HOME')+'/data/emlines_info.dat'
        dat = np.loadtxt(loc, delimiter=',', dtype = {'names':('lam','name'),'formats':('f16','S40')})
        obs['elines_idx'] = dat['name'] == 'H alpha 6563'

        # load h-alpha luminosity list
        loc = os.getenv('APPS')+'/prospector_alpha/data/brown_optical_info.dat'
        dat = np.loadtxt(loc, delimiter=' ', comments='#',
                         dtype = {'names':('name', 'ha_lum', 'ha_lum_errup', 'ha_lum_errdown', 'hb_lum', 'hb_lum_errup', 'hb_lum_errdown', 'dn4000'),
                                  'formats':('S40','f16','f16','f16','f16','f16','f16','f16')})
        idx = dat['name'] == objname.replace(' ','_')
        obs['elines_lum'] = np.atleast_1d(dat['ha_lum'][idx]) / constants.L_sun.cgs.value
        obs['elines_unc'] = np.atleast_1d((dat['ha_lum_errup'][idx]-dat['ha_lum_errdown'][idx])/2.) / constants.L_sun.cgs.value
        obs['elines_unc'] = np.clip(obs['elines_unc'] , obs['elines_lum'] *errfloor, np.inf)

    # build output dictionary
    obs['filters'] = filters
    obs['wave_effective'] = wave_effective
    obs['phot_mask'] = phot_mask
    obs['maggies'] = flux
    obs['maggies_unc'] =  unc
    obs['wavelength'] = None
    obs['spectrum'] = None
    obs['logify_spectrum'] = False

    if objname is None:
        obs['hnames'] = herschel[1].data['Name']
        obs['names'] = hdulist[1].data['Name']

    # tidy up
    extinct.close()
    herschel.close()
    return obs

##########################
# TRANSFORMATION FUNCTIONS
##########################
def load_gp(**extras):
    return None, None

def tie_gas_logz(logzsol=None, **extras):
    return logzsol

def to_dust1(dust1_fraction=None, dust1=None, dust2=None, **extras):
    return dust1_fraction*dust2

def massmet_to_logmass(massmet=None,**extras):
    return massmet[0]

def massmet_to_logzsol(massmet=None,**extras):
    return massmet[1]

def logmass_to_masses(massmet=None, logsfr_ratios=None, agebins=None, **extras):
    logsfr_ratios = np.clip(logsfr_ratios,-10,10) # numerical issues...
    nbins = agebins.shape[0]
    sratios = 10**logsfr_ratios
    dt = (10**agebins[:,1]-10**agebins[:,0])
    coeffs = np.array([ (1./np.prod(sratios[:i])) * (np.prod(dt[1:i+1]) / np.prod(dt[:i])) for i in range(nbins)])
    m1 = (10**massmet[0]) / coeffs.sum()

    return m1 * coeffs


#############
# MODEL_PARAMS
#############
model_params = []

###### BASIC PARAMETERS ##########
model_params.append({'name': 'zred', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'units': '',
                        'prior': priors.TopHat(mini=0.0, maxi=4.0)})

model_params.append({'name': 'lumdist', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'units': 'Mpc',
                        'prior_function': None,
                        'prior_args': None})

model_params.append({'name': 'add_igm_absorption', 'N': 1,
                        'isfree': False,
                        'init': 1,
                        'units': None,
                        'prior_function': None,
                        'prior_args': None})

model_params.append({'name': 'add_agb_dust_model', 'N': 1,
                        'isfree': False,
                        'init': True,
                        'units': None,
                        'prior_function': None,
                        'prior_args': None})

model_params.append({'name': 'pmetals', 'N': 1,
                        'isfree': False,
                        'init': -99,
                        'units': '',
                        'prior_function': None,
                        'prior_args': {'mini':-3, 'maxi':-1}})

model_params.append({'name': 'massmet', 'N': 2,
                        'isfree': True,
                        'init': np.array([10,-0.5]),
                        'prior': None})

model_params.append({'name': 'logmass', 'N': 1,
                        'isfree': False,
                        'depends_on': massmet_to_logmass,
                        'init': 10.0,
                        'units': 'Msun',
                        'prior': None})

model_params.append({'name': 'logzsol', 'N': 1,
                        'isfree': False,
                        'init': -0.5,
                        'depends_on': massmet_to_logzsol,
                        'units': r'$\log (Z/Z_\odot)$',
                        'prior': None})
                        
###### SFH   ########
model_params.append({'name': 'sfh', 'N':1,
                        'isfree': False,
                        'init': 0,
                        'units': None})

model_params.append({'name': 'mass', 'N': 1,
                     'isfree': False,
                     'depends_on': logmass_to_masses,
                     'init': 1.,
                     'units': r'M$_\odot$',})

model_params.append({'name': 'agebins', 'N': 1,
                        'isfree': False,
                        'init': [],
                        'units': 'log(yr)',
                        'prior': None})

model_params.append({'name': 'logsfr_ratios', 'N': 7,
                        'isfree': True,
                        'init': [],
                        'units': '',
                        'prior': None})

########    IMF  ##############
model_params.append({'name': 'imf_type', 'N': 1,
                             'isfree': False,
                             'init': 1, #1 = chabrier
                             'units': None,
                             'prior': None})

######## Dust Absorption ##############
model_params.append({'name': 'dust_type', 'N': 1,
                        'isfree': False,
                        'init': 4,
                        'units': 'index',
                        'prior_function_name': None,
                        'prior_args': None})
                        
model_params.append({'name': 'dust1', 'N': 1,
                        'isfree': False,
                        'depends_on': to_dust1,
                        'init': 1.0,
                        'units': '',
                        'prior': None})

model_params.append({'name': 'dust1_fraction', 'N': 1,
                        'isfree': True,
                        'init': 1.0,
                        'init_disp': 0.8,
                        'disp_floor': 0.8,
                        'units': '',
                        'prior': priors.ClippedNormal(mini=0.0, maxi=2.0, mean=1.0, sigma=0.3)})

model_params.append({'name': 'dust2', 'N': 1,
                        'isfree': True,
                        'init': 1.0,
                        'init_disp': 0.25,
                        'disp_floor': 0.15,
                        'units': '',
                        'prior': priors.ClippedNormal(mini=0.0, maxi=4.0, mean=0.3, sigma=1)})

model_params.append({'name': 'dust_index', 'N': 1,
                        'isfree': True,
                        'init': 0.0,
                        'init_disp': 0.25,
                        'disp_floor': 0.15,
                        'units': '',
                        'prior': priors.TopHat(mini=-1.0, maxi=0.4)})

model_params.append({'name': 'dust1_index', 'N': 1,
                        'isfree': False,
                        'init': -1.0,
                        'units': '',
                        'prior': None})

model_params.append({'name': 'dust_tesc', 'N': 1,
                        'isfree': False,
                        'init': 7.0,
                        'units': 'log(Gyr)',
                        'prior_function_name': None,
                        'prior_args': None})

###### Dust Emission ##############
model_params.append({'name': 'add_dust_emission', 'N': 1,
                        'isfree': False,
                        'init': 1,
                        'units': None,
                        'prior': None})

model_params.append({'name': 'duste_gamma', 'N': 1,
                        'isfree': False,
                        'init': 0.01,
                        'units': None,
                        'prior': priors.TopHat(mini=0.0, maxi=0.15)})

model_params.append({'name': 'duste_umin', 'N': 1,
                        'isfree': False,
                        'init': 1.0,
                        'units': None,
                        'prior': priors.TopHat(mini=0.1, maxi=15.0)})

model_params.append({'name': 'duste_qpah', 'N': 1,
                        'isfree': False,
                        'init': 2.0,
                        'units': 'percent',
                        'prior': priors.TopHat(mini=0.0, maxi=7.0)})

###### Nebular Emission ###########
model_params.append({'name': 'add_neb_emission', 'N': 1,
                        'isfree': False,
                        'init': True,
                        'units': r'log Z/Z_\odot',
                        'prior': None})

model_params.append({'name': 'add_neb_continuum', 'N': 1,
                        'isfree': False,
                        'init': True,
                        'units': r'log Z/Z_\odot',
                        'prior': None})

model_params.append({'name': 'nebemlineinspec', 'N': 1,
                        'isfree': False,
                        'init': False,
                        'prior': None})

model_params.append({'name': 'gas_logz', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'units': r'log Z/Z_\odot',
                        'prior': priors.TopHat(mini=-2.0, maxi=0.5)})

model_params.append({'name': 'gas_logu', 'N': 1, # scale with sSFR?
                        'isfree': False,
                        'init': -2.0,
                        'units': '',
                        'prior': priors.TopHat(mini=-4.0, maxi=-1.0)})

##### AGN dust ##############
model_params.append({'name': 'add_agn_dust', 'N': 1,
                        'isfree': False,
                        'init': True,
                        'units': '',
                        'prior': None})

model_params.append({'name': 'fagn', 'N': 1,
                        'isfree': True,
                        'init': 0.01,
                        'init_disp': 0.03,
                        'disp_floor': 0.02,
                        'units': '',
                        'prior': priors.LogUniform(mini=1e-5, maxi=3.0)})

model_params.append({'name': 'agn_tau', 'N': 1,
                        'isfree': True,
                        'init': 20.0,
                        'init_disp': 5,
                        'disp_floor': 2,
                        'units': '',
                        'prior': priors.LogUniform(mini=5.0, maxi=150.0)})

####### Calibration ##########
model_params.append({'name': 'phot_jitter', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'init_disp': 0.5,
                        'units': 'fractional maggies (mags/1.086)',
                        'prior': priors.TopHat(mini=0.0, maxi=0.5)})

####### Units ##########
model_params.append({'name': 'peraa', 'N': 1,
                     'isfree': False,
                     'init': False})

model_params.append({'name': 'mass_units', 'N': 1,
                     'isfree': False,
                     'init': 'mformed'})

#### resort list of parameters 
# because we can
parnames = [m['name'] for m in model_params]
fit_order = ['massmet','logsfr_ratios', 'dust2', 'dust_index', 'dust1_fraction', 'fagn', 'agn_tau']
tparams = [model_params[parnames.index(i)] for i in fit_order]
for param in model_params: 
    if param['name'] not in fit_order:
        tparams.append(param)
model_params = tparams

##### Mass-metallicity prior ######
class MassMet(priors.Prior):
    """A Gaussian prior designed to approximate the Gallazzi et al. 2005 
    stellar mass--stellar metallicity relationship.

    Must be updated to have relevant functions of `distribution` in `priors.py`
    in order to be run with a nested sampler.
    """

    prior_params = ['mass_mini', 'mass_maxi', 'z_mini', 'z_maxi']
    distribution = truncnorm
    massmet = np.loadtxt(os.getenv('APPS')+'/prospector_alpha/data/gallazzi_05_massmet.txt')

    def __len__(self):
        """ Hack to work with Prospector 0.3
        """
        return 2

    def scale(self,mass):
        upper_84 = np.interp(mass, self.massmet[:,0], self.massmet[:,3]) 
        lower_16 = np.interp(mass, self.massmet[:,0], self.massmet[:,2])
        return (upper_84-lower_16)

    def loc(self,mass):
        return np.interp(mass, self.massmet[:,0], self.massmet[:,1])

    def get_args(self,mass):
        a = (self.params['z_mini'] - self.loc(mass)) / self.scale(mass)
        b = (self.params['z_maxi'] - self.loc(mass)) / self.scale(mass)
        return [a, b]

    @property
    def range(self):
        return ((self.params['mass_mini'], self.params['mass_maxi']),\
                (self.params['z_mini'], self.params['z_maxi']))

    def bounds(self, **kwargs):
        if len(kwargs) > 0:
            self.update(**kwargs)
        return self.range

    def __call__(self, x, **kwargs):
        """Compute the value of the probability density function at x and
        return the ln of that.

        :params x:
            x[0] = mass, x[1] = metallicity. Used to calculate the prior

        :param kwargs: optional
            All extra keyword arguments are used to update the `prior_params`.

        :returns lnp:
            The natural log of the prior probability at x, scalar or ndarray of
            same length as the prior object.
        """
        if len(kwargs) > 0:
            self.update(**kwargs)
        p = np.atleast_2d(np.zeros_like(x))
        a, b = self.get_args(x[...,0])
        p[...,1] = self.distribution.pdf(x[...,1], a, b, loc=self.loc(x[...,0]), scale=self.scale(x[...,0]))
        with np.errstate(invalid='ignore'):
            p[...,1] = np.log(p[...,1])
        return p

    def sample(self, nsample=None, **kwargs):
        """Draw a sample from the prior distribution.

        :param nsample: (optional)
            Unused
        """
        if len(kwargs) > 0:
            self.update(**kwargs)
        mass = np.random.uniform(low=self.params['mass_mini'],high=self.params['mass_maxi'])
        a, b = self.get_args(mass)
        met = self.distribution.rvs(a, b, loc=self.loc(mass), scale=self.scale(mass))
        return np.array([mass, met])

    def unit_transform(self, x, **kwargs):
        """Go from a value of the CDF (between 0 and 1) to the corresponding
        parameter value.

        :param x:
            A scalar or vector of same length as the Prior with values between
            zero and one corresponding to the value of the CDF.

        :returns theta:
            The parameter value corresponding to the value of the CDF given by
            `x`.
        """
        if len(kwargs) > 0:
            self.update(**kwargs)
        mass = x[0]*(self.params['mass_maxi'] - self.params['mass_mini']) + self.params['mass_mini']
        a, b = self.get_args(mass)
        met = self.distribution.ppf(x[1], a, b, loc=self.loc(mass), scale=self.scale(mass))
        return np.array([mass,met])

###### Redefine SPS ######
class NebSFH(FastStepBasis):
    
    @property
    def emline_wavelengths(self):
        return self.ssp.emline_wavelengths

    @property
    def get_nebline_luminosity(self):
        """Emission line luminosities in units of Lsun per solar mass formed
        """
        return self.ssp.emline_luminosity/self.params['mass'].sum()

    def nebline_photometry(self,filters,z):
        """analytically calculate emission line contribution to photometry
        """
        emlams = self.emline_wavelengths * (1+z)
        elums = self.get_nebline_luminosity # Lsun / solar mass formed
        flux = np.empty(len(filters))
        for i,filt in enumerate(filters):
            # calculate transmission at nebular emission
            trans = np.interp(emlams, filt.wavelength, filt.transmission, left=0., right=0.)
            idx = (trans > 0)
            if True in idx:
                flux[i] = (trans[idx]*emlams[idx]*elums[idx]).sum()/filt.ab_zero_counts
            else:
                flux[i] = 0.0
        return flux

    def get_spectrum(self, outwave=None, filters=None, peraa=False, **params):
        """Get a spectrum and SED for the given params.
        ripped from SSPBasis
        addition: check for flag nebeminspec. if not true,
        add emission lines directly to photometry
        """

        lsun = 3.846e33
        pc = 3.085677581467192e18  # in cm

        lightspeed = 2.998e18  # AA/s
        to_cgs = lsun/(4.0 * np.pi * (pc*10)**2)
        jansky_mks = 1e-26

        # Spectrum in Lsun/Hz per solar mass formed, restframe
        wave, spectrum, mfrac = self.get_galaxy_spectrum(**params)

        # Redshifting + Wavelength solution
        # We do it ourselves.
        a = 1 + self.params.get('zred', 0)
        af = a
        b = 0.0

        if 'wavecal_coeffs' in self.params:
            x = wave - wave.min()
            x = 2.0 * (x / x.max()) - 1.0
            c = np.insert(self.params['wavecal_coeffs'], 0, 0)
            # assume coeeficients give shifts in km/s
            b = chebval(x, c) / (lightspeed*1e-13)

        wa, sa = wave * (a + b), spectrum * af  # Observed Frame
        if outwave is None:
            outwave = wa

        spec_aa = lightspeed/wa**2 * sa # convert to perAA
        # Observed frame photometry, as absolute maggies
        if filters is not None:
            mags = observate.getSED(wa, spec_aa * to_cgs, filters)
            phot = np.atleast_1d(10**(-0.4 * mags))
        else:
            phot = 0.0

        ### if we don't have emission lines, add them
        if (not self.params['nebemlineinspec']) and self.params['add_neb_emission']:
            phot += self.nebline_photometry(filters,a-1)*to_cgs

        # Spectral smoothing.
        do_smooth = (('sigma_smooth' in self.params) and
                     ('sigma_smooth' in self.reserved_params))
        if do_smooth:
            # We do it ourselves.
            smspec = self.smoothspec(wa, sa, self.params['sigma_smooth'],
                                     outwave=outwave, **self.params)
        elif outwave is not wa:
            # Just interpolate
            smspec = np.interp(outwave, wa, sa, left=0, right=0)
        else:
            # no interpolation necessary
            smspec = sa

        # Distance dimming and unit conversion
        zred = self.params.get('zred', 0.0)
        if (zred == 0) or ('lumdist' in self.params):
            # Use 10pc for the luminosity distance (or a number
            # provided in the dist key in units of Mpc)
            dfactor = (self.params.get('lumdist', 1e-5) * 1e5)**2
        else:
            lumdist = WMAP9.luminosity_distance(zred).value
            dfactor = (lumdist * 1e5)**2
        if peraa:
            # spectrum will be in erg/s/cm^2/AA
            smspec *= to_cgs / dfactor * lightspeed / outwave**2
        else:
            # Spectrum will be in maggies
            smspec *= to_cgs / dfactor / 1e3 / (3631*jansky_mks)

        # Convert from absolute maggies to apparent maggies
        phot /= dfactor

        # Mass normalization
        mass = np.sum(self.params.get('mass', 1.0))
        if np.all(self.params.get('mass_units', 'mstar') == 'mstar'):
            # Convert from current stellar mass to mass formed
            mass /= mfrac

        return smspec * mass, phot * mass, mfrac

def load_sps(**extras):

    sps = NebSFH(**extras)
    return sps

def load_model(objname='',datname='', agelims=[], nbins_sfh=7, sigma=0.3, df=2, free_ir_sed=False, **extras):

    # we'll need this to access specific model parameters
    n = [p['name'] for p in model_params]

    # set redshift, tuniv
    hdulist = fits.open(datname)
    idx = hdulist[1].data['Name'] == objname
    zred =  hdulist[1].data['cz'][idx][0] / 3e5
    tuniv = WMAP9.age(zred).value*1e9
    lumdist = hdulist[1].data['Dist'][idx][0]
    hdulist.close()

    # now construct the nonparametric SFH
    # current scheme:  last bin is 15% age of the Universe, first two are 0-30, 30-100
    # remaining N-3 bins spaced equally in logarithmic space
    tbinmax = (tuniv*0.85)
    agelims = agelims[:2] + np.linspace(agelims[2],np.log10(tbinmax),nbins_sfh-2).tolist() + [np.log10(tuniv)]
    agebins = np.array([agelims[:-1], agelims[1:]])

    # load nvariables and agebins
    model_params[n.index('agebins')]['N'] = nbins_sfh
    model_params[n.index('agebins')]['init'] = agebins.T
    model_params[n.index('mass')]['N'] = nbins_sfh
    model_params[n.index('logsfr_ratios')]['N'] = nbins_sfh-1
    model_params[n.index('logsfr_ratios')]['init'] = np.full(nbins_sfh-1,0.0) # constant SFH
    model_params[n.index('logsfr_ratios')]['prior'] = priors.StudentT(mean=np.full(nbins_sfh-1,0.0),
                                                                      scale=np.full(nbins_sfh-1,sigma),
                                                                      df=np.full(nbins_sfh-1,df))

    if free_ir_sed:
        model_params[n.index('duste_gamma')]['isfree'] = True
        model_params[n.index('duste_qpah')]['isfree'] = True
        model_params[n.index('duste_umin')]['isfree'] = True

    # set mass-metallicity prior
    # insert redshift into model dictionary
    model_params[n.index('massmet')]['prior'] = MassMet(z_mini=-1.98, z_maxi=0.19, mass_mini=7, mass_maxi=12.5)
    model_params[n.index('zred')]['init'] = zred
    model_params[n.index('lumdist')]['init'] = lumdist

    return sedmodel.SedModel(model_params)

