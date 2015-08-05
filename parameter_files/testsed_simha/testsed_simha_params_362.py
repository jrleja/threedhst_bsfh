import numpy as np
import fsps,os,threed_dutils
from sedpy import attenuation
from bsfh import priors, sedmodel, elines
from astropy.cosmology import WMAP9
import bsfh.datautils as dutils
tophat = priors.tophat
logarithmic = priors.logarithmic

#############
# RUN_PARAMS
#############

run_params = {'verbose':True,
              'outfile':os.getenv('APPS')+'/threedhst_bsfh/results/testsed_simha/testsed_simha',
              'ftol':0.5e-5, 
              'maxfev':5000,
              'nwalkers':248,
              'nburn':[16,16,32], 
              'niter': 200,
              'initial_disp':0.1,
              'debug': False,
              'min_error': 0.01,
              'abs_error': False,
              'spec': False, 
              'phot':True,
              'photname':os.getenv('APPS')+'/threedhst_bsfh/data/testsed_simha_truth.cat',
              'truename':os.getenv('APPS')+'/threedhst_bsfh/data/testsed_simha_truth.dat',
              'objname':'362',
              }

############
# OBS
#############

def load_fsps_filters():

    # this translates filter names
    # to names that FSPS recognizes
    # ripped from brownseds_params.py
    translate_pfsps = {
    'FUV': 'GALEX_FUV',
    'UVW2': 'UVOT_W2',
    'UVM2': 'UVOT_M2',
    'NUV': 'GALEX_NUV',
    'UVW1': 'UVOT_W1',
    'Umag': np.nan,    # [11.9/15.7]? Swift/UVOT U AB band magnitude
    'umag': 'SDSS_u',
    'gmag': 'SDSS_g',
    'Vmag': np.nan,    # [10.8/15.6]? Swift/UVOT V AB band magnitude
    'rmag': 'SDSS_r',
    'imag': 'SDSS_i',
    'zmag': 'SDSS_z',
    'Jmag': '2MASS_J',
    'Hmag': '2MASS_H',
    'Ksmag': '2MASS_Ks',
    'W1mag': 'WISE_W1',
    '[3.6]': 'IRAC_1',
    '[4.5]': 'IRAC_2',
    'W2mag': 'WISE_W2',
    '[5.8]': 'IRAC_3',
    '[8.0]': 'IRAC_4',
    'W3mag': 'WISE_W3',
    'PUIB': np.nan,    # [8.2/15.6]? Spitzer/IRS Blue Peak Up Imaging channel (13.3-18.7um) AB magnitude
    'W4mag': np.nan,    # two WISE4 magnitudes, what is the correction?
    "W4'mag": 'WISE_W4',
    'PUIR': np.nan,    # Spitzer/IRS Red Peak Up Imaging channel (18.5-26.0um) AB magnitude
    '[24]': 'MIPS_24',
    'pacs70': 'PACS_70',
    'pacs100': 'PACS_100',
    'pacs160': 'PACS_160',
    'spire250': 'SPIRE_250',
    'spire350': 'SPIRE_350',
    'spire500': 'SPIRE_500'
    }

    filters = translate_pfsps.values()
    filters = np.array(filters)[np.array(filters) != 'nan']

    return filters

def load_obs_3dhst(filename, objnum, zperr=False):
    """
    Custom-built because the photometric files are actually generated by the model
    """
    obs ={}

    with open(filename, 'r') as f:
        hdr = f.readline().split()
    dat = np.loadtxt(filename, comments = '#',
                     dtype = np.dtype([(n, np.float) for n in hdr[1:]]))
    obj_ind = np.where(dat['id'] == int(objnum))[0][0]
    
    # extract fluxes+uncertainties for all objects and all filters
    flux_fields = [f for f in dat.dtype.names if f[0:2] == 'f_']
    unc_fields = [f for f in dat.dtype.names if f[0:2] == 'e_']
    filters = [f[2:] for f in flux_fields]

    # extract fluxes for particular object, converting from record array to numpy array
    flux = dat[flux_fields].view(float).reshape(len(dat),-1)[obj_ind]
    unc  = dat[unc_fields].view(float).reshape(len(dat),-1)[obj_ind]

    # define all outputs
    wave_effective = np.array(threed_dutils.return_mwave_custom(filters))
    phot_mask = np.logical_or(np.logical_or((flux != unc),(flux > 0)),flux != -99.0)

    if zperr is True:
        zp_offsets = threed_dutils.load_zp_offsets(None)
        band_names = np.array([x['Band'].lower()+'_'+x['Field'].lower() for x in zp_offsets])
        
        for kk in xrange(len(filters)):
            match = band_names == filters[kk]
            if np.sum(match) > 0:
                maggies_unc[kk] = ( (maggies_unc[kk]**2) + (maggies[kk]*(1-zp_offsets[match]['Flux-Correction'][0]))**2 ) **0.5

    # sort outputs based on effective wavelength
    points = zip(wave_effective,filters,phot_mask,flux,unc)
    sorted_points = sorted(points)

    # build output dictionary
    obs['wave_effective'] = np.array([point[0] for point in sorted_points])
    obs['filters'] = np.array([point[1] for point in sorted_points])
    obs['phot_mask'] =  np.array([point[2] for point in sorted_points])
    obs['maggies'] = np.array([point[3] for point in sorted_points])
    obs['maggies_unc'] =  np.array([point[4] for point in sorted_points])
    obs['wavelength'] = None
    obs['spectrum'] = None

    # uncomment this if you want to use build_sample
    # to create photometry in the brown filter set
    #obs['filters'] = np.array(load_fsps_filters())
    #obs['maggies'] = None

    return obs

obs = load_obs_3dhst(run_params['photname'], run_params['objname'], zperr=False)

#############
# MODEL_PARAMS
#############

def transform_delt_to_sftrunc(tage=None, delt_trunc=None, **extras):

    return tage*delt_trunc

def transform_logtau_to_tau(tau=None, logtau=None, **extras):

    return 10**logtau

def add_dust1(dust2=None, **extras):

    return 1.86*dust2

class BurstyModel(sedmodel.CSPModel):

    def theta_disps(self, thetas, initial_disp=0.1):
        """Get a vector of dispersions for each parameter to use in
        generating sampler balls for emcee's Ensemble sampler.

        :param initial_disp: (default: 0.1)
            The default dispersion to use in case the `init_disp` key
            is not provided in the parameter configuration.  This is
            in units of the parameter, so e.g. 0.1 will result in a
            smpler ball with a dispersion that is 10% of the central
            parameter value.
        """
        disp = np.zeros(self.ndim) + initial_disp
        for par, inds in self.theta_index.iteritems():
            
            # fractional dispersion
            if par == 'mass' or \
               par == 'tage':
                disp[inds[0]:inds[1]] = self._config_dict[par].get('init_disp', initial_disp) * thetas[inds[0]:inds[1]]

            # constant (log) dispersion
            if par == 'logtau' or \
               par == 'metallicity' or \
               par == 'sf_slope' or \
               par == 'delt_trunc':
                disp[inds[0]:inds[1]] = self._config_dict[par].get('init_disp', initial_disp)

            # fractional dispersion with artificial floor
            if par == 'dust2' or \
               par == 'dust_index':
                disp[inds[0]:inds[1]] = (self._config_dict[par].get('init_disp', initial_disp) * thetas[inds[0]:inds[1]]**2 + \
                                         0.1**2)**0.5
            
        return disp

    def theta_disp_floor(self, thetas):
        """Get a vector of dispersions for each parameter to use as
        a floor for the walker-calculated dispersions.
        """
        disp = np.zeros(self.ndim)
        for par, inds in self.theta_index.iteritems():
            
            # constant 5% floor
            if par == 'mass':
                disp[inds[0]:inds[1]] = 0.05 * thetas[inds[0]:inds[1]]

            # constant 0.05 floor (log space, sf_slope, dust_index)
            if par == 'logzsol':
                disp[inds[0]:inds[1]] = 0.25

            if par == 'logtau':
                disp[inds[0]:inds[1]] = 0.25

            if par == 'sf_slope':
                disp[inds[0]:inds[1]] = 0.6

            if par == 'dust2' or \
               par == 'dust_index':
                disp[inds[0]:inds[1]] = 0.15

            # 15% floor
            if par == 'tage':
                disp[inds[0]:inds[1]] = 0.15 * thetas[inds[0]:inds[1]]

            if par == 'delt_trunc':
                disp[inds[0]:inds[1]] = 0.1
            
        return disp

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

        for k, v in self.theta_index.iteritems():
            start, end = v
            lnp_prior += np.sum(self._config_dict[k]['prior_function']
                                (theta[start:end], **self._config_dict[k]['prior_args']))
        return lnp_prior

#### SET SFH PRIORS #####

#### TUNIV #####
#tuniv = WMAP9.age(model_params[parmlist.index('zred')]['init']).value
tuniv  = 14.0
run_params['tuniv']       = tuniv
run_params['time_buffer'] = 0.05

#### TAGE #####
tage_maxi = tuniv
tage_init = tuniv/2.
tage_mini  = 0.11      # FSPS standard

model_type = BurstyModel
model_params = []

param_template = {'name':'', 'N':1, 'isfree': False,
                  'init':0.0, 'units':'', 'label':'',
                  'prior_function_name': None, 'prior_args': None}

###### BASIC PARAMETERS ##########
model_params.append({'name': 'zred', 'N': 1,
                        'isfree': False,
                        'init': 1.0,
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
                        
model_params.append({'name': 'mass', 'N': 1,
                        'isfree': True,
                        'init': 1e10,
                        'init_disp': 0.25,
                        'units': r'M_\odot',
                        'prior_function': tophat,
                        'prior_args': {'mini':1e7,'maxi':1e14}})

model_params.append({'name': 'pmetals', 'N': 1,
                        'isfree': False,
                        'init': -99,
                        'units': '',
                        'prior_function': None,
                        'prior_args': {'mini':-3, 'maxi':-1}})

model_params.append({'name': 'logzsol', 'N': 1,
                        'isfree': True,
                        'init': -0.1,
                        'init_disp': 0.15,
                        'units': r'$\log (Z/Z_\odot)$',
                        'prior_function': tophat,
                        'prior_args': {'mini':-1.98, 'maxi':0.19}})
                        
###### SFH   ########
model_params.append({'name': 'sfh', 'N': 1,
                        'isfree': False,
                        'init': 5,
                        'units': 'type',
                        'prior_function_name': None,
                        'prior_args': None})

model_params.append({'name': 'logtau', 'N': 1,
                        'isfree': True,
                        'init': 0.0,
                        'init_disp': 0.25,
                        'units': 'log(Gyr)',
                        'prior_function': tophat,
                        'prior_args': {'mini':-1.0,
                                       'maxi':2.0}})

model_params.append({'name': 'tau', 'N': 1,
                        'isfree': False,
                        'init': 1.0,
                        'depends_on': transform_logtau_to_tau,
                        'units': 'Gyr',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.1,
                                       'maxi':100}})

model_params.append({'name': 'tage', 'N': 1,
                        'isfree': True,
                        'init': tage_init,
                        'init_disp': 0.25,
                        'units': 'Gyr',
                        'prior_function': tophat,
                        'prior_args': {'mini':tage_mini, 'maxi':tage_maxi}})

model_params.append({'name': 'tburst', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'init_disp': 1.0,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':10.0}})

model_params.append({'name': 'fburst', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'init_disp': 0.5,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':0.2}})

model_params.append({'name': 'fconst', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':1.0}})

model_params.append({'name': 'sf_start', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'units': 'Gyr',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0,'maxi':14.0}})

model_params.append({'name': 'delt_trunc', 'N': 1,
                        'isfree': True,
                        'init': 0.5,
                        'init_disp': 0.1,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi': 1.0}})

model_params.append({'name': 'sf_trunc', 'N': 1,
                        'isfree': False,
                        'init': 1.0,
                        'units': '',
                        'depends_on': transform_delt_to_sftrunc,
                        'prior_function': tophat,
                        'prior_args': {'mini':0, 'maxi':16}})

model_params.append({'name': 'sf_slope', 'N': 1,
                        'isfree': True,
                        'init': -1.0,
                        'init_disp': 0.3,
                        'units': None,
                        'prior_function': tophat,
                        'prior_args': {'mini':-10.0,'maxi':2.0}})

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
                        'isfree': False,
                        'init': 0.0,
                        'depends_on': add_dust1,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':8.0}})

model_params.append({'name': 'dust2', 'N': 1,
                        'isfree': True,
                        'init': 1.0,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0,'maxi':4.0}})

model_params.append({'name': 'dust_index', 'N': 1,
                        'isfree': True,
                        'init': -0.7,
                        'units': '',
                        'prior_function': priors.normal_clipped,
                        'prior_args': {'mini':-3.0, 'maxi': -0.4,'mean':-0.7,'sigma':0.5}})

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
                        'isfree': False,
                        'init': 0.01,
                        'units': None,
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':1.0}})

model_params.append({'name': 'duste_umin', 'N': 1,
                        'isfree': False,
                        'init': 1.0,
                        'units': None,
                        'prior_function': tophat,
                        'prior_args': {'mini':0.1, 'maxi':25.0}})

model_params.append({'name': 'duste_qpah', 'N': 1,
                        'isfree': False,
                        'init': 3.0,
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

# name outfile
run_params['outfile'] = run_params['outfile']+'_'+run_params['objname']
