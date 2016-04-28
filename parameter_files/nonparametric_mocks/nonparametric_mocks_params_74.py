import numpy as np
import os
from prospect.models import priors, sedmodel
from prospect.sources import StepSFHBasis
from sedpy import observate
from astropy.cosmology import WMAP9
from astropy.io import fits
tophat = priors.tophat
logarithmic = priors.logarithmic

#############
# RUN_PARAMS
#############

run_params = {'verbose':True,
              'debug': False,
              'outfile': os.getenv('APPS')+'/threedhst_bsfh/results/nonparametric_mocks/nonparametric_mocks',
              'nofork': True,
              # Optimizer params
              'ftol':0.5e-5, 
              'maxfev':5000,
              # MCMC params
              'nwalkers':507,
              'nburn':[150,200], 
              'niter': 5000,
              # Model info
              'zcontinuous': 2,
              'compute_vega_mags': False,
              'initial_disp':0.1,
              'interp_type': 'logarithmic',
              'agelims': [6.0,7.0,8.0,8.5,9.0,9.5,10.0],
              # Data info
              'photname':os.getenv('APPS')+'/threedhst_bsfh/data/nonparametric_mocks.cat',
              'truename':os.getenv('APPS')+'/threedhst_bsfh/data/nonparametric_mocks.dat',
              'objname':'74'
              }
run_params['outfile'] = run_params['outfile']+'_'+run_params['objname']

############
# OBS
#############

def translate_filters(bfilters, full_list = False):
    '''
    translate filter names to FSPS standard
    this is ALREADY a mess, clean up soon!
    suspect there are smarter routines to do this in python-fsps
    '''

    # this is necessary for my code
    # to calculate effective wavelength
    # in threed_dutils
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
    'W2mag': 'WISE_W2',
    '[5.8]': 'spitzer_irac_ch3',
    '[8.0]': 'spitzer_irac_ch4',
    'W3mag': 'WISE_W3',
    'PUIB': np.nan,    # [8.2/15.6]? Spitzer/IRS Blue Peak Up Imaging channel (13.3-18.7um) AB magnitude
    'W4mag': np.nan,    # two WISE4 magnitudes, this one is "native" and must be corrected
    "W4'mag": 'WISE_W4',
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
        return translate.values()
    else:
        return np.array([translate[f] for f in bfilters]), np.array([translate_pfsps[f] for f in bfilters])


def load_obs(photname='', objname='', **extras):
    """
    Custom-built because the photometric files are actually generated by the model
    """
    obs ={}

    # if the photometric files exist
    with open(photname, 'r') as f:
        hdr = f.readline().split()
    dat = np.loadtxt(photname, comments = '#',
                     dtype = np.dtype([(n, np.float) for n in hdr[1:]]))
    obj_ind = np.where(dat['id'] == int(objname))[0][0]
    
    # extract fluxes+uncertainties for all objects and all filters
    flux_fields = [f for f in dat.dtype.names if f[0:2] == 'f_']
    unc_fields = [f for f in dat.dtype.names if f[0:2] == 'e_']
    filters = [f[2:] for f in flux_fields]

    # extract fluxes for particular object, converting from record array to numpy array
    flux = dat[flux_fields].view(float).reshape(len(dat),-1)[obj_ind]
    unc  = dat[unc_fields].view(float).reshape(len(dat),-1)[obj_ind]

    # build output dictionary
    obs['filters'] = observate.load_filters(filters)
    obs['wave_effective'] = np.array([filt.wave_effective for filt in obs['filters']])
    obs['phot_mask'] = np.ones_like(flux,dtype=bool)
    obs['maggies'] = flux
    obs['maggies_unc'] =  unc
    obs['wavelength'] = None
    obs['spectrum'] = None
    obs['logify_spectrum'] = False

    return obs

def expsfh(agelims, tau=1e5, power=1, **extras):
    """
    Calculate the mass in a set of step functions that is equivalent to an
    exponential SFH.  That is, \int_amin^amax \, dt \, e^(-t/\tau) where
    amin,amax are the age limits of the bins making up the step function.
    """
    from scipy.special import gamma, gammainc
    tage = 10**np.max(agelims) / 1e9
    t = tage - 10**np.array(agelims)/1e9
    nb = len(t)
    mformed = np.zeros(nb-1)
    t = np.insert(t, 0, tage)
    for i in range(nb-1):
        t1, t2 = t[i+1], t[i]
        normalized_times = (np.array([t1, t2, tage])[:, None]) / tau
        mass = gammainc(power, normalized_times)
        intsfr = (mass[1,...] - mass[0,...]) / mass[2,...]
        mformed[i] = intsfr
    return mformed * 1e3
        

#################
# NEW SPS BASIS #
#################
class NPBasis(StepSFHBasis):

    @property
    def all_ssp_weights(self):
        ages = self.params['agebins']
        masses = self.params['sfh_logmass']

        w = np.zeros(len(self.logage)+1)
        # Loop over age bins
        # Should cache the bin weights when agebins not changing.  But this is
        # not very time consuming for few enough bins.
        for (t1, t2), mass in zip(ages, masses):
            w += 10**mass * self.bin_weights(t1, t2)

        # convert to surviving stellar mass
        weight = w/np.insert(self.ssp.stellar_mass, 0, 1.0)
        return weight


######################
# GENERATING FUNCTIONS
######################
def load_gp(**extras):
    return None, None

def load_sps(**extras):

    sps = NPBasis(**extras)
    return sps

def add_dust1(dust2=None, **extras):

    return 0.86*dust2

def tie_gas_logz(logzsol=None, **extras):

    return logzsol

#############
# MODEL_PARAMS
#############

model_params = []

###### BASIC PARAMETERS ##########
model_params.append({'name': 'zred', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':4.0}})

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

model_params.append({'name': 'logzsol', 'N': 1,
                        'isfree': True,
                        'init': -0.5,
                        'init_disp': 0.25,
                        'disp_floor': 0.2,
                        'units': r'$\log (Z/Z_\odot)$',
                        'prior_function': tophat,
                        'prior_args': {'mini':-1.98, 'maxi':0.19}})
                        
###### SFH   ########
model_params.append({'name': 'sfh', 'N':1,
                        'isfree': False,
                        'init': 0,
                        'units': None})

model_params.append({'name': 'sfh_logmass', 'N': 1,
                        'isfree': True,
                        'init': [],
                        'units': 'Msun',
                        'prior_function': priors.tophat,
                        'prior_args':{'mini':0.0, 'maxi':1.0}})

model_params.append({'name': 'agebins', 'N': 1,
                        'isfree': False,
                        'init': [],
                        'units': 'log(yr)',
                        'prior_function': priors.tophat,
                        'prior_args':{'mini':0.1, 'maxi':15.0}})

########    IMF  ##############
model_params.append({'name': 'imf_type', 'N': 1,
                             'isfree': False,
                             'init': 1, #1 = chabrier
                             'units': None,
                             'prior_function_name': None,
                             'prior_args': None})

######## Dust Absorption ##############
model_params.append({'name': 'dust_type', 'N': 1,
                        'isfree': False,
                        'init': 4,
                        'units': 'index',
                        'prior_function_name': None,
                        'prior_args': None})
                        
model_params.append({'name': 'dust1', 'N': 1,
                        'isfree': True,
                        'init': 1.0,
                        'init_disp': 0.8,
                        'disp_floor': 0.5,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':4.0}})

model_params.append({'name': 'dust2', 'N': 1,
                        'isfree': True,
                        'init': 1.0,
                        'init_disp': 0.25,
                        'disp_floor': 0.15,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0,'maxi':4.0}})

model_params.append({'name': 'dust_index', 'N': 1,
                        'isfree': True,
                        'init': 0.0,
                        'init_disp': 0.25,
                        'disp_floor': 0.15,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':-2.2, 'maxi': 0.4}})

model_params.append({'name': 'dust1_index', 'N': 1,
                        'isfree': False,
                        'init': -1.0,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':-1.5, 'maxi':-0.5}})

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
                        'prior_function': None,
                        'prior_args': None})

model_params.append({'name': 'duste_gamma', 'N': 1,
                        'isfree': True,
                        'init': 0.01,
                        'init_disp': 0.2,
                        'disp_floor': 0.15,
                        'units': None,
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':1.0}})

model_params.append({'name': 'duste_umin', 'N': 1,
                        'isfree': True,
                        'init': 1.0,
                        'init_disp': 5.0,
                        'disp_floor': 4.5,
                        'units': None,
                        'prior_function': tophat,
                        'prior_args': {'mini':0.1, 'maxi':25.0}})

model_params.append({'name': 'duste_qpah', 'N': 1,
                        'isfree': True,
                        'init': 3.0,
                        'init_disp': 3.0,
                        'disp_floor': 3.0,
                        'units': 'percent',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':10.0}})

###### Nebular Emission ###########
model_params.append({'name': 'add_neb_emission', 'N': 1,
                        'isfree': False,
                        'init': 2,
                        'units': r'log Z/Z_\odot',
                        'prior_function_name': None,
                        'prior_args': None})

model_params.append({'name': 'add_neb_continuum', 'N': 1,
                        'isfree': False,
                        'init': True,
                        'units': r'log Z/Z_\odot',
                        'prior_function_name': None,
                        'prior_args': None})
                        
model_params.append({'name': 'gas_logz', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'depends_on': tie_gas_logz,
                        'units': r'log Z/Z_\odot',
                        'prior_function': tophat,
                        'prior_args': {'mini':-2.0, 'maxi':0.5}})

model_params.append({'name': 'gas_logu', 'N': 1,
                        'isfree': False,
                        'init': -2.0,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':-4, 'maxi':-1}})


####### Calibration ##########
model_params.append({'name': 'phot_jitter', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'init_disp': 0.5,
                        'units': 'fractional maggies (mags/1.086)',
                        'prior_function':tophat,
                        'prior_args': {'mini':0.0, 'maxi':0.5}})


#### resort list of parameters 
#### so that major ones are fit first
parnames = [m['name'] for m in model_params]
fit_order = ['sfh_logmass','dust2', 'logzsol', 'dust_index', 'dust1', 'duste_qpah', 'duste_gamma', 'duste_umin']
tparams = [model_params[parnames.index(i)] for i in fit_order]
for param in model_params: 
    if param['name'] not in fit_order:
        tparams.append(param)
model_params = tparams

###### REDEFINE MODEL FOR MY OWN NEFARIOUS PURPOSES ######
class BurstyModel(sedmodel.SedModel):

    def prior_product(self, theta):
        """
        Return a scalar which is the ln of the product of the prior
        probabilities for each element of theta.  Requires that the
        prior functions are defined in the theta descriptor.

        :param theta:
            Iterable containing the free model parameter values.

        :returns lnp_prior:
            The log of the product of the prior probabilities for
            these parameter values.
        """  
        lnp_prior = 0

        # implement uniqueness of outliers
        if 'gp_outlier_locs' in self.theta_index:
            start,end = self.theta_index['gp_outlier_locs']
            outlier_locs = theta[start:end]
            if len(np.unique(np.round(outlier_locs))) != len(outlier_locs):
                return -np.inf

        if 'dust1' in self.theta_index:
            if 'dust2' in self.theta_index:
                start,end = self.theta_index['dust1']
                dust1 = theta[start:end]
                start,end = self.theta_index['dust2']
                dust2 = theta[start:end]
                if dust1/1.5 > dust2:
                    return -np.inf
                '''
                if dust1 < 0.5*dust2:
                    return -np.inf
                '''

        for k, v in self.theta_index.iteritems():
            start, end = v
            this_prior = np.sum(self._config_dict[k]['prior_function']
                                (theta[start:end], **self._config_dict[k]['prior_args']))

            if (not np.isfinite(this_prior)):
                print('WARNING: ' + k + ' is out of bounds')
            lnp_prior += this_prior
        return lnp_prior

def load_model(objname='', agelims=[], **extras):

    ###### LOAD REDSHIFT ######
    zred = 0.0

    #### CALCULATE TUNIV #####
    tuniv = WMAP9.age(zred).value

    #### NONPARAMETRIC SFH ######
    agelims[-1] = np.log10(tuniv*1e9)
    agebins = np.array([agelims[:-1], agelims[1:]])
    ncomp = len(agelims) - 1
    mass_init =  expsfh(agelims, **extras)

    #### ADJUST MODEL PARAMETERS #####
    n = [p['name'] for p in model_params]
    model_params[n.index('sfh_logmass')]['N'] = ncomp
    model_params[n.index('sfh_logmass')]['init'] = np.log10(mass_init)
    model_params[n.index('sfh_logmass')]['prior_args'] = {'maxi':np.full(ncomp,14.0), 'mini':np.full(ncomp,0.0)}
    model_params[n.index('sfh_logmass')]['init_disp'] = 0.3
    model_params[n.index('agebins')]['N'] = ncomp
    model_params[n.index('agebins')]['init'] = agebins.T

    #### INSERT REDSHIFT INTO MODEL PARAMETER DICTIONARY ####
    zind = n.index('zred')
    model_params[zind]['init'] = zred

    #### CREATE AND RETURN MODEL
    model = BurstyModel(model_params)

    return model

model_type = BurstyModel

