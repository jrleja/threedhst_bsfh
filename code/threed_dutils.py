import numpy as np
import os, fsps
from bsfh import model_setup
from scipy.interpolate import interp1d
from scipy.integrate import simps
from calc_ml import load_filter_response

def setup_sps(zcontinuous=2):

	'''
	easy way to define an SPS
	'''

	# load stellar population, set up custom filters
	sps = fsps.StellarPopulation(zcontinuous=zcontinuous, compute_vega_mags=False)
	custom_filter_keys = os.getenv('APPS')+'/threedhst_bsfh/filters/filter_keys_threedhst.txt'
	fsps.filters.FILTERS = model_setup.custom_filter_dict(custom_filter_keys)

	return sps

def synthetic_emlines(mass,sfr,dust1,dust2,dust_index):

	'''
	SFR in Msun/yr
	mass in Msun
	'''

	# wavelength in angstroms
	emlines = np.array(['Halpha','Hbeta','Hgamma','[OIII]', '[NII]','[OII]'])
	lam     = np.array([6563,4861,4341,5007,6583,3727])
	flux    = np.zeros(shape=(len(lam),len(np.atleast_1d(mass))))

	# calculate SFR
	#deltat = 0.3 # in Gyr
	#sfr = integrate_sfh(sps.params['tage']-deltat,
	#                    sps.params['tage'],
	#                    [np.array(1.0)],
	#                    sps.params['tage'],
	#                    sps.params['tau'],
	#                    sps.params['sf_start'],
	#                    sps.params['tburst'],
	#                    sps.params['fburst'])
	#sfr = sfr / (1e9*deltat)
    
	# calculate Halpha luminosity from KS relationship
	# comes out in units of [ergs/s]
	# correct from Chabrier to Salpeter with a factor of 1.7
	flux[0,:] = 1.26e41 * (sfr*1.7)

	# Halpha: Hbeta: Hgamma = 2.8:1.0:0.47 (Miller 1974)
	flux[1,:] = flux[0,:]/2.8
	flux[2,:] = flux[1,:]*0.47

	# [OIII] from Fig 8, http://arxiv.org/pdf/1401.5490v2.pdf
	# assume [OIII] is a singlet for now
	# this calculates [5007], add 4959 manually
	y_ratio=np.array([0.3,0.35,0.5,0.8,1.0,1.3,1.6,2.0,2.7,\
	       3.0,4.10,4.9,4.9,6.2,6.2])
	x_ssfr=np.array([1e-10,2e-10,3e-10,4e-10,5e-10,6e-10,7e-10,9e-10,1.2e-9,\
	       2e-9,3e-9,5e-9,8e-9,1e-8,2e-8])
	ratio=np.interp(1.0/sfr,x_ssfr,y_ratio)

	# 5007/4959 = 2.88
	flux[3,:] = ratio*flux[1,:]*(1+1/2.88)

	# from Leja et al. 2013
	# log[NII/Ha] = -5.36+0.44log(M)
	lnii_ha = -5.36+0.44*np.log10(mass)
	flux[4,:] = (10**lnii_ha)*flux[0,:]

	# [Ha / [OII]] vs [NII] / Ha from Hayashi et al. 2013, fig 6
	# evidence in discussion suggests should add reddening
	# corresponding to extinction of A(Ha) = 0.35
	# also should change with metallicity, oh well
	nii_ha_x = np.array([0.13,0.2,0.3,0.4,0.5])
	ha_oii_y = np.array([1.1,1.3,2.0,2.9,3.6])
	ratio = np.interp(flux[4,:]/flux[0,:],nii_ha_x,ha_oii_y)
	flux[5,:] = (1.0/ratio)*flux[0,:]

	# correct for dust
	tau2 = ((lam.reshape(len(lam),1)/5500.)**dust_index)*dust2
	tau1 = ((lam.reshape(len(lam),1)/5500.)**dust_index)*dust1
	tautot = tau2+tau1
	flux = flux*np.exp(-tautot)

	# comes out in ergs/s
	output = {'name': emlines,
	          'lam': lam,
	          'flux': flux}
	return output

def generate_basenames(runname):

	filebase=[]
	parm=[]
	ancilname='COSMOS_testsamp.dat'


	if runname == 'dtau_intmet':

		id_list = os.getenv('APPS')+"/threedhst_bsfh/data/COSMOS_testsamp.ids"
		ids = np.loadtxt(id_list, dtype='|S20')
		ngals = len(ids)

		basename = "dtau_intmet"
		parm_basename = "dtau_intmet_params"

		for jj in xrange(ngals):
			ancildat = load_ancil_data(os.getenv('APPS')+
			                           '/threedhst_bsfh/data/COSMOS_testsamp.dat',
			                           ids[jj])
			heqw_txt = "%04d" % int(ancildat['Ha_EQW_obs']) 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+runname+'/'+basename+'_'+heqw_txt+'_'+ids[jj])
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/"+runname+'/'+parm_basename+'_'+str(jj+1)+'.py')	

	if runname == 'dtau_neboff':

		id_list = os.getenv('APPS')+"/threedhst_bsfh/data/COSMOS_testsamp.ids"
		ids = np.loadtxt(id_list, dtype='|S20')
		ngals = len(ids)

		basename = "dtau_neboff"
		parm_basename = "dtau_neboff_params"

		for jj in xrange(ngals):
			ancildat = load_ancil_data(os.getenv('APPS')+
			                           '/threedhst_bsfh/data/COSMOS_testsamp.dat',
			                           ids[jj])
			heqw_txt = "%04d" % int(ancildat['Ha_EQW_obs']) 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+runname+'/'+basename+'_'+heqw_txt+'_'+ids[jj])
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/"+runname+'/'+parm_basename+'_'+str(jj+1)+'.py')		

	if runname == 'dtau_nebon':

		id_list = os.getenv('APPS')+"/threedhst_bsfh/data/COSMOS_testsamp.ids"
		ids = np.loadtxt(id_list, dtype='|S20')
		ngals = len(ids)

		basename = "dtau_nebon"
		parm_basename = "dtau_nebon_params"

		for jj in xrange(ngals):
			ancildat = load_ancil_data(os.getenv('APPS')+
			                           '/threedhst_bsfh/data/COSMOS_testsamp.dat',
			                           ids[jj])
			heqw_txt = "%04d" % int(ancildat['Ha_EQW_obs']) 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+runname+'/'+basename+'_'+heqw_txt+'_'+ids[jj])
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/"+runname+'/'+parm_basename+'_'+str(jj+1)+'.py')	

	if runname == 'neboff_oiii':

		id_list = os.getenv('APPS')+"/threedhst_bsfh/data/COSMOS_oiii_em.ids"
		ids = np.loadtxt(id_list, dtype='|S20')
		ngals = len(ids)

		basename = "neboff_oiii"
		parm_basename = "neboff_oiii_params"
		ancilname='COSMOS_oiii_em.dat'

		for jj in xrange(ngals):
			ancildat = load_ancil_data(os.getenv('APPS')+
			                           '/threedhst_bsfh/data/COSMOS_oiii_em.dat',
			                           ids[jj])
			heqw_txt = "%04d" % int(ancildat['Ha_EQW_obs']) 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+runname+'/'+basename+'_'+heqw_txt+'_'+ids[jj])
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/"+runname+'/'+parm_basename+'_'+str(jj+1)+'.py')		

	if runname == 'nebon':

		id_list = os.getenv('APPS')+"/threedhst_bsfh/data/COSMOS_testsamp.ids"
		ids = np.loadtxt(id_list, dtype='|S20')
		ngals = len(ids)

		basename = "ha_selected_nebon"
		parm_basename = "halpha_selected_nebon_params"
		
		for jj in xrange(ngals):
			ancildat = load_ancil_data(os.getenv('APPS')+
			                           '/threedhst_bsfh/data/COSMOS_testsamp.dat',
			                           ids[jj])
			heqw_txt = "%04d" % int(ancildat['Ha_EQW_obs']) 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+basename+'_'+heqw_txt+'_'+ids[jj])
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/"+parm_basename+'_'+str(jj+1)+'.py')

	if runname == 'neboff':

		id_list = os.getenv('APPS')+"/threedhst_bsfh/data/COSMOS_testsamp.ids"
		ids = np.loadtxt(id_list, dtype='|S20')
		ngals = len(ids)

		basename = "ha_selected_neboff"
		parm_basename = "halpha_selected_params"

		for jj in xrange(ngals):
			ancildat = load_ancil_data(os.getenv('APPS')+
			                           '/threedhst_bsfh/data/COSMOS_testsamp.dat',
			                           ids[jj])
			heqw_txt = "%04d" % int(ancildat['Ha_EQW_obs']) 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+runname+'/'+basename+'_'+heqw_txt+'_'+ids[jj])
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/"+runname+'/'+parm_basename+'_'+str(jj+1)+'.py')

	if runname == 'photerr':
		
		id = '19723'
		basename = 'photerr/photerr'
		errnames = np.loadtxt(os.getenv('APPS')+'/threedhst_bsfh/parameter_files/photerr/photerr.txt')

		for jj in xrange(len(errnames)): 
			filebase.append(os.getenv('APPS')+"/threedhst_bsfh/results/"+basename+'_'+str(errnames[jj])+'_'+id)
			parm.append(os.getenv('APPS')+"/threedhst_bsfh/parameter_files/photerr/photerr_params_"+str(jj+1)+'.py')

	return filebase,parm,ancilname

def chop_chain(chain):
	'''
	simple placeholder
	will someday replace with a test for convergence to determine where to chop
	JRL 1/5/14
	'''
	nchop=1e50

	flatchain = chain[:,int(chain.shape[1]/nchop):,:]
	flatchain = flatchain.reshape(flatchain.shape[0] * flatchain.shape[1],
                                  flatchain.shape[2])

	return flatchain


def return_mwave_custom(filters):

	"""
	returns effective wavelength based on filter names
	"""

	loc = os.getenv('APPS')+'/threedhst_bsfh/filters/'
	key_str = 'filter_keys_threedhst.txt'
	lameff_str = 'lameff_threedhst.txt'
	
	lameff = np.loadtxt(loc+lameff_str)
	keys = np.loadtxt(loc+key_str, dtype='S20',usecols=[1])
	keys = keys.tolist()
	keys = np.array([keys.lower() for keys in keys], dtype='S20')
	
	lameff_return = [[lameff[keys == filters[i]]][0] for i in range(len(filters))]
	lameff_return = [item for sublist in lameff_return for item in sublist]
	assert len(filters) == len(lameff_return), "Filter name is incorrect"

	return lameff_return

def load_ancil_data(filename,objnum):

	'''
	loads ancillary plotting information
	'''
	
	with open(filename, 'r') as f:
		for jj in range(1): hdr = f.readline().split()
	dat = np.loadtxt(filename, comments = '#',dtype = np.dtype([(n, np.float) for n in hdr[1:]]))
	
	if objnum:
		objdat = dat[dat['id'] == float(objnum)]
		return objdat

	return dat

def load_mips_data(filename,objnum=None):
	
	with open(filename, 'r') as f:
		for jj in range(1): hdr = f.readline().split()
	dat = np.loadtxt(filename, comments = '#',dtype = np.dtype([(n, np.float) for n in hdr[1:]]))
	
	if objnum is not None:
		objdat = dat[dat['id'] == float(objnum)]
		return objdat

	return dat

def load_obs_3dhst(filename, objnum, mips=None, min_error = None, abs_error=False):
	"""
	Load 3D-HST photometry file, return photometry for a particular object.
	min_error: set the minimum photometric uncertainty to be some fraction
	of the flux. if not set, use default errors.
	"""
	obs ={}
	fieldname=filename.split('/')[-1].split('_')[0].upper()
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

	# add mips
	if mips:
		mips_dat = load_mips_data(mips,objnum=objnum)
		flux=np.append(flux,mips_dat['f24tot'])
		unc=np.append(unc,mips_dat['ef24tot'])
		filters.append('MIPS_24um')

	# define all outputs
	filters = [filter.lower()+'_'+fieldname.lower() for filter in filters]
	wave_effective = np.array(return_mwave_custom(filters))
	phot_mask = np.logical_or(np.logical_or((flux != unc),(flux > 0)),flux != -99.0)
	maggies = flux/(10**10)
	maggies_unc = unc/(10**10)

	# set minimum photometric error
	if min_error is not None:
		if abs_error:
			maggies_unc = min_error*maggies
		else:
			under = maggies_unc < min_error*maggies
			maggies_unc[under] = min_error*maggies[under]
	
	# sort outputs based on effective wavelength
	points = zip(wave_effective,filters,phot_mask,maggies,maggies_unc)
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

def load_fast_3dhst(filename, objnum):
	"""
	Load FAST output for a particular object
	Returns a dictionary of inputs for BSFH
	"""

	# filter through header junk, load data
	with open(filename, 'r') as f:
		for jj in range(1): hdr = f.readline().split()
	dat = np.loadtxt(filename, comments = '#',dtype = np.dtype([(n, np.float) for n in hdr[1:]]))

	# extract field names, search for ID, pull out object info
	fields = [f for f in dat.dtype.names]
	id_ind = fields.index('id')
	obj_ind = [int(x[id_ind]) for x in dat].index(int(objnum))
	values = dat[fields].view(float).reshape(len(dat),-1)[obj_ind]

	return values, fields

def integrate_mag(spec_lam,spectra,filter, z=None, alt_file=None):

	'''
	borrowed from calc_ml
	given a filter name and spectrum, calculate magnitude/luminosity in filter (see alt_file for filter names)
	INPUT: 
		SPEC_LAM: must be in angstroms. if redshift is specified, this should ALREADY be corrected for reddening.
		SPECTRA: must be in Lsun/Hz (FSPS standard). if redshift is specified, the normalization will be taken care of.
	OUTPUT:
		LUMINOSITY: comes out in erg/s
		MAG: comes out as absolute magnitude
			NOTE: if redshift is specified, INSTEAD RETURN apparent magnitude and flux [erg/s/cm^2]
	'''

	if type(filter) == str:
		resp_lam, res = load_filter_response(filter, 
		                                 	 alt_file='/Users/joel/code/fsps/data/allfilters_threedhst.dat')
	else:
		resp_lam = filter[0][0]
		res      = filter[1][0]

	# calculate effective width
	#dlam = (resp_lam[1:]-resp_lam[:-1])/2.
	#width = np.array([dlam[ii]+dlam[ii+1] for ii in xrange(len(resp_lam)-2)])
	#width = np.concatenate((np.atleast_1d(dlam[0]*2),width,np.atleast_1d(dlam[-1]*2)))
	#effective_width = np.sum(res*width)
	
	# physical units, in CGS, from sps_vars.f90 in the SPS code
	pc2cm = 3.08568E18
	lsun  = 3.839E33
	c     = 2.99E10

	# interpolate filter response onto spectral lambda array
	# when interpolating, set response outside wavelength range to be zero.
	response_interp_function = interp1d(resp_lam,res, bounds_error = False, fill_value = 0)
	resp_interp = response_interp_function(spec_lam)
	
	# integrate spectrum over filter response
	# first calculate luminosity: convert to flambda (factor of c/lam^2, with c converted to AA/s)
	# then integrate over flambda [Lsun/AA] to get Lsun
	spec_flam = spectra*(c*1e8/(spec_lam**2))
	luminosity = simps(spec_flam*resp_interp,spec_lam)
	
	# now calculate luminosity density [erg/s/Hz] in filter
	# this involves normalizing the filter response by integrating over wavelength
	norm = simps(resp_interp/spec_lam,spec_lam)
	luminosity_density = simps(spectra*(resp_interp/norm)/spec_lam,spec_lam)

	# if redshift is specified, convert to flux and apparent magnitude
	if z:
		from astropy.cosmology import WMAP9
		dfactor = (WMAP9.luminosity_distance(z).value*1e5)**(-2)*(1+z)
		luminosity = luminosity*dfactor
		luminosity_density = luminosity_density*dfactor

	# convert luminosity density to flux density
	# the units of the spectra are Lsun/Hz; convert to
	# erg/s/cm^2/Hz, at 10pc for absolute mags
	flux_density = luminosity_density*lsun/(4.0*np.pi*(pc2cm*10)**2)
	luminosity   = luminosity*lsun

	# convert flux density to magnitudes in AB system
	mag = -2.5*np.log10(flux_density)-48.60

	#print 'maggies: {0}'.format(10**(-0.4*mag)*1e10)
	return mag, luminosity

def mips_to_lir(z):

	# mips information
	# effective width from commented calculation in integrate_mag above
	# avg wavelength from table 2.2 of mips instrument handbook
	mips_eff_width = 48850.322
	mips_avg_lam   = 236800.0

	# load Table 2 from Dale & Helou 2002
	filename = os.getenv('APPS')+'/threedhst_bsfh/data/dale_helou_table2.dat'
	with open(filename, 'r') as f:
		for jj in range(1): hdr = f.readline().split()
	data = np.loadtxt(filename, comments = '#',dtype = np.dtype([(n, np.float) for n in hdr[1:]]))

	# take log average to make SED
	# note that Kate refers to L_IR as 8-1000 ums
	# whereas this integral is implicitly over 3um-1100um
	# only ~3% flux in 3-5 um, and up to ~13% in 5-13um, so not too worried...
	# but these will be slightly underestimated as a result!
	to_average = data['alpha'] < 2.5
	fluxes = np.zeros(6)
	waves = [(3,5),(5,13),(13,20),(20,42),(42,122),(122,1100)] # in microns
	avg_waves = np.array([(x[0]+x[1])/2. for x in waves])
	for i, names in enumerate(data.dtype.names):
		if np.logical_and(names != 'lfnu60_lfnu100', names != 'alpha'):
			fluxes[i-2] = 10**np.mean(np.log10(data[names][to_average]))
	fluxes = np.array([fluxes[ii]/(waves[ii][1]-waves[ii][0]) for ii in xrange(len(waves))])
	fluxes = fluxes/np.sum(fluxes)

	# interpolate flux density fraction
	interp_helou = interp1d(avg_waves, fluxes)
	fluxfrac = interp_helou(mips_avg_lam/(1.+z))*mips_eff_width/(1.+z)
	
	return 1./fluxfrac

def calculate_uv_ir_sfr():

	# step 1: calculate MIPS flux from spectrum (or plug in MIPS flux for testing)
	# step 2: calculate MIPS flux ---> f_{IR}
	# step 3: convert to L_{IR}
	# step 4: calculate L_2500 (?)
	# step 5: tear it up
	# step 6: realize you need to do none of this
	pass

def integrate_sfh(t1,t2,mass,tage,tau,sf_start,tburst,fburst):
	
	'''
	integrate a delayed tau SFH between t1 and t2
	'''
	
	# double or single tau model?
	# does NOT currently accept different tages
	# double t2 if not doubled:
	ndim = len(np.atleast_1d(mass))
	if len(np.atleast_1d(t2)) != ndim:
		t2 = np.zeros(ndim)+t2

		
	totmass = np.sum(mass)
	norm=(mass/totmass)*(1.0-fburst)
	tot = np.zeros(ndim)-99
	
	# if we're outside of the boundaries, return boundary values
	_= np.logical_or((t1<sf_start),(t2<sf_start))
	if np.sum(_) > 0:
		tot[_] = 0.0

	_ = t2 > tage
	if np.sum(_) > 0:
		tot[_]     = norm[_]

	# check what needs to be calculated still
	# add tau model
	need2calc = (tot == -99)
	if np.sum(need2calc) > 0:
		intsfr = (np.exp(-t1[need2calc]/tau[need2calc])*(1+t1[need2calc]/tau[need2calc]) - 
		          np.exp(-t2[need2calc]/tau[need2calc])*(1+t2[need2calc]/tau[need2calc]))

		tot[need2calc]=intsfr*norm[need2calc]/(np.exp(-sf_start[need2calc]/tau[need2calc])*(sf_start[need2calc]/tau[need2calc]+1)-
				                               np.exp(-tage[need2calc]    /tau[need2calc])*(tage[need2calc]    /tau[need2calc]+1))
	# add burst
	need_burst = np.logical_and((t2 > tburst),(t1 < tburst))
	if np.sum(need_burst) > 0:
		tot[need_burst] = tot[need_burst] + fburst[need_burst]
	intsfr = np.sum(tot)

	if intsfr > 1.00000001:
		print intsfr
		print 'intsfr should not be greater than 1.0!'
		print 1/0
	if intsfr < -0.0000001:
		print intsfr
		print 1/0
	return intsfr