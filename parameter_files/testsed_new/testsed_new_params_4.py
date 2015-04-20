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
              'outfile':os.getenv('APPS')+'/threedhst_bsfh/results/testsed/testsed',
              'ftol':0.5e-5, 
              'maxfev':5000,
              'nwalkers':248,
              'nburn':[32,64,128,128], 
              'niter': 2048,
              'initial_disp':0.1,
              'debug': False,
              'mock': False,
              'logify_spectrum': False,
              'normalize_spectrum': False,
              'set_init_params': None,  # DO NOT SET THIS TO TRUE SINCE TAGE == TUNIV*1.2 (fast,random)
              'min_error': 0.02,
              'abs_error': False,
              'spec': False, 
              'phot':True,
              'photname':os.getenv('APPS')+'/threedhst_bsfh/data/testsed.cat',
              'truename':os.getenv('APPS')+'/threedhst_bsfh/data/testsed.dat',
              'objname':'4',
              }

############
# OBS
#############

def load_obs_3dhst(filename, objnum, zperr=False):
    """
    Load 3D-HST photometry file, return photometry for a particular object.
    min_error: set the minimum photometric uncertainty to be some fraction
    of the flux. if not set, use default errors.
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

    return obs

obs = load_obs_3dhst(run_params['photname'], run_params['objname'], zperr=False)

#############
# MODEL_PARAMS
#############

class BurstyModel(sedmodel.CSPModel):
	
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
        
        # check to make sure tau models are separated
        if 'tau' in self.theta_index:
            start,end = self.theta_index['tau']
            tau = theta[start:end]
            if (tau[0] < 2*tau[1]):
                return -np.inf

        # implement mass ratio
        if 'mass' in self.theta_index:
            start,end = self.theta_index['mass']
            mass = theta[start:end]
            if (mass[1]/mass[0] > 20):
                return -np.inf

        for k, v in self.theta_index.iteritems():
            start, end = v
            lnp_prior += np.sum(self._config_dict[k]['prior_function']
                                (theta[start:end], **self._config_dict[k]['prior_args']))
        
        return lnp_prior

model_type = BurstyModel
model_params = []

param_template = {'name':'', 'N':1, 'isfree': False,
                  'init':0.0, 'units':'', 'label':'',
                  'prior_function_name': None, 'prior_args': None}

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
                        
model_params.append({'name': 'mass', 'N': 2,
                        'isfree': True,
                        'init': np.array([1e10, 1e9]),
                        'units': r'M_\odot',
                        'prior_function': tophat,
                        'prior_args': {'mini':np.array([1e7, 1e7]),
                                       'maxi':np.array([1e14, 1e14])}})

model_params.append({'name': 'pmetals', 'N': 1,
                        'isfree': False,
                        'init': -99,
                        'units': '',
                        'prior_function': None,
                        'prior_args': {'mini':-3, 'maxi':-1}})

model_params.append({'name': 'logzsol', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'init_disp': 0.4,
                        'log_param': True,
                        'units': r'$\log (Z/Z_\odot)$',
                        'prior_function': tophat,
                        'prior_args': {'mini':-1, 'maxi':0.19}})
                        
###### SFH   ########
model_params.append({'name': 'sfh', 'N': 1,
                        'isfree': False,
                        'init': 4,
                        'units': 'type',
                        'prior_function_name': None,
                        'prior_args': None})

model_params.append({'name': 'tau', 'N': 2,
                        'isfree': True,
                        'init': np.array([10.0, 1.0]),
                        'init_disp': 0.5,
                        'units': 'Gyr',
                        'prior_function':logarithmic,
                        'prior_args': {'mini':np.array([0.1, 0.1]),
                                       'maxi':np.array([100.0, 100.0])}})

model_params.append({'name': 'tage', 'N': 1,
                        'isfree': False,
                        'init': 14.0,
                        'units': 'Gyr',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.1, 'maxi':14.0}})

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

model_params.append({'name': 'sf_start', 'N': 2,
                        'isfree': True,
                        'reinit': True,
                        'init': np.array([1.0, 1.0]),
                        'units': 'Gyr',
                        'prior_function': tophat,
                        'prior_args': {'mini':np.array([0.0, 0.0]),
                                       'maxi':np.array([14.0, 14.0])}})

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
                        'init': 0,
                        'units': 'index',
                        'prior_function_name': None,
                        'prior_args': None})
                        
model_params.append({'name': 'dust1', 'N': 1,
                        'isfree': False,
                        'init': 0.0,
                        'init_disp': 0.5,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':3.0}})

model_params.append({'name': 'dust2', 'N': 2,
                        'isfree': True,
                        'init': np.array([0.35,0.35]),
                        'reinit': True,
                        'init_disp': 0.2,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':np.array([0.0, 0.0]),
                                       'maxi':np.array([4.0, 4.0])}})

model_params.append({'name': 'dust_index', 'N': 1,
                        'isfree': True,
                        'init': -0.7,
                        'reinit': True,
                        'units': '',
                        'prior_function': tophat,
                        'prior_args': {'mini':-3.0, 'maxi': -0.4}})

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
                        'units': 'mags',
                        'prior_function': tophat,
                        'prior_args': {'mini':0.0, 'maxi':0.2}})


# name outfile
run_params['outfile'] = run_params['outfile']+'_'+run_params['objname']
