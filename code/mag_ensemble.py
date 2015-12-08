import numpy as np
import matplotlib.pyplot as plt
import os, threed_dutils
import matplotlib as mpl
from astropy import constants
import magphys_plot_pref
import copy
from scipy.optimize import minimize

#### set up colors and plot style
prosp_color = '#e60000'
obs_color = '#95918C'
magphys_color = '#1974D2'
dpi = 150

#### herschel / non-herschel
nhargs = {'fmt':'o','alpha':0.7,'color':'0.2'}
hargs = {'fmt':'D','alpha':0.7,'color':'#E60000'}
hargs = {'fmt':'o','alpha':0.7,'color':'0.2'}
herschdict = [copy.copy(hargs),copy.copy(nhargs)]

#### AGN
colors = ['blue', 'purple', 'red']
labels = ['SF', 'SF/AGN', 'AGN']

minsfr = 1e-3

#### Halpha plot limit
halim = (-1.3,3.5)

def translate_line_names(linenames):
	'''
	translate from my names to Moustakas names
	'''
	translate = {r'H$\alpha$': 'Ha',
				 '[OIII] 5007': 'OIII',
	             r'H$\beta$': 'Hb',
	             '[NII] 6583': 'NII'}

	return np.array([translate[line] for line in linenames])

def remove_doublets(x, names):

	if any('[OIII]' in s for s in list(names)):
		keep = np.array(names) != '[OIII] 4959'
		x = x[keep]
		names = names[keep]
		#if not isinstance(x[0],basestring):
		#	x[np.array(names) == '[OIII] 4959'] *= 3.98

	if any('[NII]' in s for s in list(names)):
		keep = np.array(names) != '[NII] 6549'
		x = x[keep]
		names = names[keep]

	return x

def ret_inf(alldata,field, model='Prospectr',name=None):

	'''
	returns information from alldata
	'''

	# fields
	# flux, flux_errup, flux_errdown, lum, lum_errup, lum_errdown, eqw
	emline_names = alldata[0]['residuals']['emlines']['em_name']
	nlines = len(emline_names)

	# sigh... this is a hack
	if field == 'eqw_rest':
		fillvalue = np.zeros(shape=(3,nlines))
	else:
		fillvalue = np.zeros_like(alldata[0]['residuals']['emlines'][model][field])

	if name is None:
		return np.squeeze(np.array([f['residuals']['emlines'][model][field] if f['residuals']['emlines'] is not None else fillvalue for f in alldata]))
	else:
		emline_names = alldata[0]['residuals']['emlines']['em_name']
		idx = emline_names == name
		if field == 'eqw_rest':
			return np.squeeze(np.array([f['residuals']['emlines'][model][field] if f['residuals']['emlines'] is not None else fillvalue for f in alldata])[:,:,idx])
		else:
			return np.squeeze(np.array([f['residuals']['emlines'][model][field] if f['residuals']['emlines'] is not None else fillvalue for f in alldata])[:,idx])

def compare_moustakas_fluxes(alldata,dat,emline_names,objnames,outname='test.png',outdec='bdec.png',model='Prospectr'):

	##########
	#### extract info for objects with measurements in both catalogs
	##########
	idx_moust = []
	moust_objnames = []
	emline_names_doubrem = remove_doublets(emline_names,emline_names)
	moust_names = translate_line_names(emline_names_doubrem)
	yplot = None

	for ii in xrange(len(dat)):
		idx_moust.append(False)
		if dat[ii] is not None:
			idx_moust[ii] = True

			yflux = np.array([dat[ii]['F'+name][0] for name in moust_names])*1e-15
			yfluxerr = np.array([dat[ii]['e_F'+name][0] for name in moust_names])*1e-15
			if yplot is None:
				yplot = yflux[:,None]
				yerr = yfluxerr[:,None]
			else:
				yplot = np.concatenate((yplot,yflux[:,None]),axis=1)
				yerr = np.concatenate((yerr,yfluxerr[:,None]),axis=1)

			moust_objnames.append(objnames[ii])

	##### grab Prospector information
	ind = np.array(idx_moust,dtype=bool)

	xplot = remove_doublets(np.transpose(ret_inf(alldata,'flux',model=model)),emline_names)[:,ind]
	xplot_errup = remove_doublets(np.transpose(ret_inf(alldata,'flux_errup',model=model)),emline_names)[:,ind]
	xplot_errdown = remove_doublets(np.transpose(ret_inf(alldata,'flux_errdown',model=model)),emline_names)[:,ind]
	eqw = remove_doublets(np.transpose(ret_inf(alldata,'eqw_rest',model=model))[:,0,:],emline_names)[:,ind]

	#### plot information
	# remove NaNs from Moustakas here, which are presumably emission lines
	# where the flux was measured to be negative
	nplot = len(moust_names)
	ncols = int(np.round((nplot)/2.))
	fig, axes = plt.subplots(ncols, 2, figsize = (12,6*ncols))
	axes = np.ravel(axes)
	for ii in xrange(nplot):
		
		ok_idx = np.isfinite(yplot[ii,:])
		yp = yplot[ii,ok_idx]
		yp_err = threed_dutils.asym_errors(yp,
			                 yplot[ii,ok_idx]+yerr[ii,ok_idx],
			                 yplot[ii,ok_idx]-yerr[ii,ok_idx])

		# if I measure < 0 where Moustakas measures > 0,
		# clip to Moustakas minimum measurement, and
		# set errors to zero
		bad = xplot[ii,ok_idx] < 0
		xp = xplot[ii,ok_idx]
		xp_errup = xplot_errup[ii,ok_idx]
		xp_errdown = xplot_errdown[ii,ok_idx]
		if np.sum(bad) > 0:
			xp[bad] = np.min(np.concatenate((yplot[ii,ok_idx],xplot[ii,ok_idx][~bad])))*0.6
			xp_errup[bad] = 0.0
			xp_errdown[bad] = 1e-99
		xp_err = threed_dutils.asym_errors(xp, xp_errdown, xp_errup)

		typ = np.log10(yp)-np.log10(xp)
		axes[ii].errorbar(eqw[ii,ok_idx],typ,yerr=yp_err,
						  xerr=xp_err, 
			              linestyle=' ',
			              **nhargs)
		maxyval = np.max(np.abs(typ))
		axes[ii].set_ylim(-maxyval,maxyval)

		axes[ii].set_ylabel('log(Moustakas+10/measured) '+emline_names_doubrem[ii])
		axes[ii].set_xlabel('EQW '+emline_names_doubrem[ii])
		off,scat = threed_dutils.offset_and_scatter(np.log10(xp),np.log10(yp),biweight=True)
		axes[ii].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex',
				  transform = axes[ii].transAxes,horizontalalignment='right')
		axes[ii].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off) + ' dex',
			      transform = axes[ii].transAxes,horizontalalignment='right')
		axes[ii].axhline(0, linestyle='--', color='0.1')


		# print outliers
		diff = np.log10(xp) - np.log10(yp)
		outliers = np.abs(diff) > 3*scat
		print emline_names_doubrem[ii] + ' outliers:'
		for jj in xrange(len(outliers)):
			if outliers[jj] == True:
				print np.array(moust_objnames)[ok_idx][jj]+' ' + "{:.3f}".format(diff[jj]/scat)

	plt.tight_layout()
	plt.savefig(outname,dpi=dpi)
	plt.close()

	##### PLOT OBS VS OBS BALMER DECREMENT
	hb_idx_me = emline_names_doubrem == 'H$\\beta$'
	ha_idx_me = emline_names_doubrem == 'H$\\alpha$'
	hb_idx_mo = moust_names == 'Hb'
	ha_idx_mo = moust_names == 'Ha'

	# must have a positive flux in all measurements of all emission lines
	idx = np.isfinite(yplot[hb_idx_mo,:]) & \
          np.isfinite(yplot[ha_idx_mo,:]) & \
          (xplot[hb_idx_me,:] > 0) & \
          (xplot[ha_idx_me,:] > 0)
	idx = np.squeeze(idx)
	mydec = xplot[ha_idx_me,idx] / xplot[hb_idx_me,idx]
	modec = yplot[ha_idx_mo,idx] / yplot[hb_idx_mo,idx]

  
	fig, ax = plt.subplots(1,1, figsize = (10,10))
	ax.errorbar(mydec, modec, fmt='o',alpha=0.6,linestyle=' ')
	ax.set_xlabel('measured Balmer decrement')
	ax.set_ylabel('Moustakas+10 Balmer decrement')
	ax = threed_dutils.equalize_axes(ax, mydec,modec)
	off,scat = threed_dutils.offset_and_scatter(mydec,modec,biweight=True)
	ax.text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat),
			  transform = ax.transAxes,horizontalalignment='right')
	ax.text(0.99,0.1, 'mean offset='+"{:.3f}".format(off),
			      transform = ax.transAxes,horizontalalignment='right')
	ax.plot([2.86,2.86],[0.0,15.0],linestyle='-',color='black')
	ax.plot([0.0,15.0],[2.86,2.86],linestyle='-',color='black')
	ax.set_xlim(1,10)
	ax.set_ylim(1,10)
	plt.savefig(outdec,dpi=dpi)
	plt.close()


def compare_model_flux(alldata, emline_names, outname = 'test.png'):

	#################
	#### plot Prospector versus MAGPHYS flux
	#################
	ncol = int(np.ceil(len(emline_names)/2.))
	fig, axes = plt.subplots(ncol,2, figsize = (11,ncol*5))
	axes = np.ravel(axes)
	for ii,emname in enumerate(emline_names):
		magdat = np.log10(ret_inf(alldata,'lum',model='MAGPHYS',name=emname)) 
		prodat = np.log10(ret_inf(alldata,'lum',model='Prospectr',name=emname)) 
		yplot = prodat-magdat
		xplot = np.log10(ret_inf(alldata,'eqw_rest',model='Prospectr',name=emname))
		idx = np.isfinite(yplot)

		axes[ii].errorbar(xplot[idx,0], yplot[idx],linestyle=' ',**nhargs)
		maxyval = np.max(np.abs(yplot[idx]))
		axes[ii].set_ylim(-maxyval,maxyval)
		
		xlabel = r"log({0} EQW) [Prospector]"
		ylabel = r"log(Prosp/MAGPHYS) [{0} flux]"
		axes[ii].set_xlabel(xlabel.format(emname))
		axes[ii].set_ylabel(ylabel.format(emname))

		# horizontal line
		axes[ii].axhline(0, linestyle=':', color='grey')

		# equalize axes, show offset and scatter
		off,scat = threed_dutils.offset_and_scatter(magdat[idx],
			                                        prodat[idx],
			                                        biweight=True)
		axes[ii].text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
				  transform = axes[ii].transAxes,horizontalalignment='right')
		axes[ii].text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
			      transform = axes[ii].transAxes,horizontalalignment='right')
	
	# save
	plt.tight_layout()
	plt.savefig(outname,dpi=dpi)
	plt.close()	

def fmt_emline_info(alldata,add_abs_err = True):

	##### Observed quantities
	## emission line fluxes and EQWs, from CGS to Lsun
	obslines = {}
	mag      = {}
	prosp    = {}

	##### continuum first
	continuum =  ret_inf(alldata,'continuum_obs',model='obs')
	continuum[:,0,:] *= constants.L_sun.cgs.value # this factor needs to be removed after rerunning measure_emline_lum
	continuum[:,1:,:] /= constants.L_sun.cgs.value # this factor needs to be removed after rerunning measure_emline_lum
	lam_continuum = ret_inf(alldata,'continuum_lam',model='obs')
	obslines['continuum'] = continuum

	##### emission line EQWs and fluxes
	obslines['f_ha'] = np.transpose([ret_inf(alldata,'lum',model='Prospectr',name='H$\\alpha$'),
		                             ret_inf(alldata,'lum_errup',model='Prospectr',name='H$\\alpha$'),
		                             ret_inf(alldata,'lum_errdown',model='Prospectr',name='H$\\alpha$')]) / constants.L_sun.cgs.value
	obslines['err_ha'] = (obslines['f_ha'][:,1] - obslines['f_ha'][:,2])/2.

	obslines['f_hb'] = np.transpose([ret_inf(alldata,'lum',model='Prospectr',name='H$\\beta$'),
		                             ret_inf(alldata,'lum_errup',model='Prospectr',name='H$\\beta$'),
		                             ret_inf(alldata,'lum_errdown',model='Prospectr',name='H$\\beta$')]) / constants.L_sun.cgs.value
	obslines['err_hb'] = (obslines['f_hb'][:,1] - obslines['f_hb'][:,2])/2.

	obslines['f_hd'] = np.transpose([ret_inf(alldata,'lum',model='Prospectr',name='H$\\delta$'),
		                             ret_inf(alldata,'lum_errup',model='Prospectr',name='H$\\delta$'),
		                             ret_inf(alldata,'lum_errdown',model='Prospectr',name='H$\\delta$')]) / constants.L_sun.cgs.value
	obslines['err_hd'] = (obslines['f_hd'][:,1] - obslines['f_hd'][:,2])/2.

	obslines['f_nii'] = np.transpose([ret_inf(alldata,'lum',model='Prospectr',name='[NII] 6583'),
		                             ret_inf(alldata,'lum_errup',model='Prospectr',name='[NII] 6583'),
		                             ret_inf(alldata,'lum_errdown',model='Prospectr',name='[NII] 6583')]) / constants.L_sun.cgs.value
	obslines['err_nii'] = (obslines['f_nii'][:,1] - obslines['f_nii'][:,2])/2.
	obslines['eqw_nii'] = obslines['f_nii'] / continuum[:,2,0,None]
	obslines['eqw_err_nii'] = obslines['err_nii'] / continuum[:,2,0]

	# sum [OIII] lines
	obslines['f_oiii'] = np.transpose([ret_inf(alldata,'lum',model='Prospectr',name='[OIII] 5007'),
		                             ret_inf(alldata,'lum_errup',model='Prospectr',name='[OIII] 5007'),
		                             ret_inf(alldata,'lum_errdown',model='Prospectr',name='[OIII] 5007')])  / constants.L_sun.cgs.value
	obslines['err_oiii'] = (obslines['f_oiii'][:,1] - obslines['f_oiii'][:,2])/2.
	obslines['eqw_oiii'] = obslines['f_oiii'] / continuum[:,1,0,None]
	obslines['eqw_err_oiii'] = obslines['err_oiii'] / continuum[:,1,0]

	##### SIGNAL TO NOISE AND EQW CUTS
	# cuts
	obslines['sn_cut'] = 0.0
	obslines['eqw_cut'] = 7.0
	obslines['hdelta_sn_cut'] = 7

	'''
	obslines['sn_cut'] = 0.0
	obslines['eqw_cut'] = 3.0
	obslines['hdelta_sn_cut'] = 3
	'''

	####### absorption lines and Dn4000
	obslines['hdel'] = np.transpose([-ret_inf(alldata,'hdelta_lum',model='obs'),-ret_inf(alldata,'hdelta_lum_errup',model='obs'),-ret_inf(alldata,'hdelta_lum_errdown',model='obs')])/constants.L_sun.cgs.value
	obslines['hdel_err'] = (obslines['hdel'][:,1] - obslines['hdel'][:,2]) / 2.
	obslines['eqw_hdel'] = obslines['hdel'] / continuum[:,0,0,None]
	obslines['eqw_err_hdel'] = obslines['hdel_err'] / continuum[:,0,0]

	obslines['dn4000'] = ret_inf(alldata,'dn4000',model='obs')

	###### best-fit model absorption properties
	prosp['hbeta_abs'] = np.log10(-ret_inf(alldata,'hdelta_lum',model='Prospectr'))[:,1]
	prosp['hbeta_eqw'] = np.log10(-ret_inf(alldata,'hdelta_lum',model='Prospectr')/continuum[:,1,0,None]/constants.L_sun.cgs.value)[:,1]
	prosp['halpha_abs'] = np.log10(-ret_inf(alldata,'hdelta_lum',model='Prospectr'))[:,2]
	prosp['halpha_eqw'] = np.log10(-ret_inf(alldata,'hdelta_lum',model='Prospectr')/continuum[:,2,0,None]/constants.L_sun.cgs.value)[:,2]

	mag['hdel'] = np.log10(-ret_inf(alldata,'hdelta_lum',model='MAGPHYS'))
	mag['hdel_eqw'] = np.log10(-ret_inf(alldata,'hdelta_lum',model='MAGPHYS')/continuum[:,0,0,None]/constants.L_sun.cgs.value)
	mag['dn4000'] = ret_inf(alldata,'Dn4000',model='MAGPHYS')

	##### add Halpha, Hbeta absorption to errors
	if add_abs_err:
		
		# this is the relevant fraction of absorption flux to add to each error
		# currently scaled by the 0.178 dex scatter in Hdelta absorption flux
		# which is almost exactly 50%
		# CURRENTLY USING 0.25 BASED ON ERROR ANALYSIS PLOT, SO HALF OF WHAT'S SUGGESTED BY HDELTA COMPARISON
		# LOOK INTO IMPROVING CONTINUUM ESTIMATE FOR HDELTA
		hdel_scatter = 0.25
		halpha_corr = hdel_scatter*(10**prosp['halpha_abs']/constants.L_sun.cgs.value)
		hbeta_corr = hdel_scatter*(10**prosp['hbeta_abs']/constants.L_sun.cgs.value)

		# these are 'cosmetic' errors for S/N cuts, also used for Balmer decrements
		obslines['err_ha'] = np.sqrt(obslines['err_ha']**2 + halpha_corr**2)
		obslines['err_hb'] = np.sqrt(obslines['err_hb']**2 + hbeta_corr**2)

		# these are 'true' errors
		# we add in quadrature in up/down errors, which is probably wrong in detail
		obslines['f_ha'][:,1] = obslines['f_ha'][:,0] + np.sqrt((obslines['f_ha'][:,1] - obslines['f_ha'][:,0])**2+halpha_corr**2)
		obslines['f_ha'][:,2] = obslines['f_ha'][:,0] - np.sqrt((obslines['f_ha'][:,2] - obslines['f_ha'][:,0])**2+hbeta_corr**2)

		obslines['f_hb'][:,1] = obslines['f_hb'][:,0] + np.sqrt((obslines['f_hb'][:,1] - obslines['f_hb'][:,0])**2+halpha_corr**2)
		obslines['f_hb'][:,2] = obslines['f_hb'][:,0] - np.sqrt((obslines['f_hb'][:,2] - obslines['f_hb'][:,0])**2+hbeta_corr**2)

	##### Balmer series emission line EQWs
	# here so that the error adjustment above is propagated into EQWs
	obslines['eqw_ha'] = obslines['f_ha'] / continuum[:,2,0,None]
	obslines['eqw_err_ha'] = obslines['err_ha'] / continuum[:,2,0]

	obslines['eqw_hb'] = obslines['f_hb'] / continuum[:,1,0,None]
	obslines['eqw_err_hb'] = obslines['err_hb'] / continuum[:,1,0]

	##### names
	objnames = np.array([f['objname'] for f in alldata])

	####### calculate observed emission line ratios, propagate errors
	# Balmer decrement, OIII / Hb, NII / Ha
	# assuming independent variables (mostly true)
	# really should calculate in bootstrapping procedure
	obslines['bdec'] = obslines['f_ha'][:,0] / obslines['f_hb'][:,0]
	obslines['bdec_err'] = obslines['bdec'] * np.sqrt((obslines['err_ha']/obslines['f_ha'][:,0])**2+(obslines['err_hb']/obslines['f_hb'][:,0])**2)
	obslines['oiii_hb'] = obslines['f_oiii'][:,0] / obslines['f_hb'][:,0]
	obslines['oiii_hb_err'] = obslines['oiii_hb'] * np.sqrt((obslines['err_oiii']/obslines['f_oiii'][:,0])**2+(obslines['err_hb']/obslines['f_hb'][:,0])**2)
	obslines['nii_ha'] = obslines['f_nii'][:,0] / obslines['f_ha'][:,0]
	obslines['nii_ha_err'] = obslines['nii_ha'] * np.sqrt((obslines['err_nii']/obslines['f_nii'][:,0])**2+(obslines['err_ha']/obslines['f_ha'][:,0])**2)

	# observed rest-frame EQW
	obslines['eqw_ha'] = ret_inf(alldata,'eqw_rest',model='Prospectr',name='H$\\alpha$')
	obslines['eqw_hb'] = ret_inf(alldata,'eqw_rest',model='Prospectr',name='H$\\beta$')

	##### NAME VARIABLES
	# Prospector model variables
	parnames = alldata[0]['pquantiles']['parnames']
	dinx_idx = parnames == 'dust_index'
	dust1_idx = parnames == 'dust1'
	dust2_idx = parnames == 'dust2'
	met_idx = parnames == 'logzsol'

	slope_idx = parnames == 'sf_tanslope'
	trunc_idx = parnames == 'delt_trunc'
	tage_idx = parnames == 'tage'

	# Prospector extra variables
	parnames = alldata[0]['pextras']['parnames']
	bcalc_idx = parnames == 'bdec_calc'
	bcloud_idx = parnames == 'bdec_cloudy'
	emp_ha_idx = parnames == 'emp_ha'
	sfr_10_idx_p = parnames == 'sfr_10'
	sfr_100_idx_p = parnames == 'sfr_100'

	# Prospectr spec info
	parnames = alldata[0]['spec_info']['name']
	dn4000_idx = parnames == 'dn4000'

	# Prospect emission line variables
	linenames = alldata[0]['model_emline']['name']
	ha_em = linenames == 'Halpha'
	hb_em = linenames == 'Hbeta'
	hd_em = linenames == 'Hdelta'
	oiii_em = linenames == '[OIII]2'
	nii_em = linenames == '[NII]'

	# MAGPHYS variables
	mparnames = alldata[0]['model']['parnames']
	mu_idx = mparnames == 'mu'
	tauv_idx = mparnames == 'tauv'

	# magphys full
	mparnames = alldata[0]['model']['full_parnames']
	sfr_10_idx = mparnames == 'SFR_10'
	mmet_idx = mparnames == 'Z/Zo'
	mmass_idx = mparnames == 'M*/Msun'
	msfr_100_idx = mparnames == 'SFR(1e8)'

	#### calculate expected Balmer decrement for Prospector, MAGPHYS
	# best-fits + marginalized
	ngals = len(alldata)
	bdec_cloudy_bfit,bdec_calc_bfit,bdec_magphys, ha_magphys, sfr_10_mag, sfr_100_mag, \
	ha_ext_mag, met_mag = [np.zeros(ngals) for i in xrange(8)]
	
	bdec_cloudy_marg, bdec_calc_marg, cloudy_ha, cloudy_hb, cloudy_hd, \
	cloudy_nii, cloudy_oiii, ha_emp, pmet, ha_ratio, oiii_hb, \
	nii_ha, dn4000, d1, d2, didx,sfr_10,sfr_100,ha_ext,sfr_100_mag_marginalized = [np.zeros(shape=(ngals,3)) for i in xrange(20)]
	for ii,dat in enumerate(np.array(alldata)):

		####### BALMER DECREMENTS
		### best-fit calculated balmer decrement
		bdec_calc_bfit[ii] = dat['bfit']['bdec_calc']

		### best-fit CLOUDY balmer decrement
		bdec_cloudy_bfit[ii] = dat['bfit']['bdec_cloudy']

		#### marginalized CLOUDY balmer decrement
		bdec_cloudy_marg[ii,0] = dat['pextras']['q50'][bcloud_idx]
		bdec_cloudy_marg[ii,1] = dat['pextras']['q84'][bcloud_idx]
		bdec_cloudy_marg[ii,2] = dat['pextras']['q16'][bcloud_idx]

		# marginalized calculated balmer decrement
		bdec_calc_marg[ii,0] = dat['pextras']['q50'][bcalc_idx]
		bdec_calc_marg[ii,1] = dat['pextras']['q84'][bcalc_idx]
		bdec_calc_marg[ii,2] = dat['pextras']['q16'][bcalc_idx]

		#MAGPHYS balmer decrement
		tau1 = (1-dat['model']['parameters'][mu_idx][0])*dat['model']['parameters'][tauv_idx][0]
		tau2 = dat['model']['parameters'][mu_idx][0]*dat['model']['parameters'][tauv_idx][0]
		bdec = threed_dutils.calc_balmer_dec(tau1, tau2, -1.3, -0.7)
		bdec_magphys[ii] = np.squeeze(bdec)

		#### CLOUDY emission lines
		cloudy_ha[ii,0] = dat['model_emline']['q50'][ha_em]
		cloudy_ha[ii,1] = dat['model_emline']['q84'][ha_em]
		cloudy_ha[ii,2] = dat['model_emline']['q16'][ha_em]

		cloudy_hb[ii,0] = dat['model_emline']['q50'][hb_em]
		cloudy_hb[ii,1] = dat['model_emline']['q84'][hb_em]
		cloudy_hb[ii,2] = dat['model_emline']['q16'][hb_em]

		cloudy_hd[ii,0] = dat['model_emline']['q50'][hd_em]
		cloudy_hd[ii,1] = dat['model_emline']['q84'][hd_em]
		cloudy_hd[ii,2] = dat['model_emline']['q16'][hd_em]

		try:
			cloudy_nii[ii,0] = dat['model_emline']['q50'][nii_em]
			cloudy_nii[ii,1] = dat['model_emline']['q84'][nii_em]
			cloudy_nii[ii,2] = dat['model_emline']['q16'][nii_em]
		except ValueError as e:
			pass

		cloudy_oiii[ii,0] = dat['model_emline']['q50'][oiii_em]
		cloudy_oiii[ii,1] = dat['model_emline']['q84'][oiii_em]
		cloudy_oiii[ii,2] = dat['model_emline']['q16'][oiii_em]

		#### Empirical emission lines
		ha_emp[ii,0] = dat['pextras']['q50'][emp_ha_idx] / constants.L_sun.cgs.value
		ha_emp[ii,1] = dat['pextras']['q84'][emp_ha_idx] / constants.L_sun.cgs.value
		ha_emp[ii,2] = dat['pextras']['q16'][emp_ha_idx] / constants.L_sun.cgs.value

		###### best-fit MAGPHYS Halpha
		sfr_10_mag[ii] = dat['model']['full_parameters'][sfr_10_idx]
		sfr_100_mag[ii] = dat['model']['full_parameters'][msfr_100_idx] * dat['model']['full_parameters'][mmass_idx]
		sfr_100_mag_marginalized[ii] = dat['magphys']['percentiles']['SFR'][1:4]
		tau1 = (1-dat['model']['parameters'][mu_idx][0])*dat['model']['parameters'][tauv_idx][0]
		tau2 = dat['model']['parameters'][mu_idx][0]*dat['model']['parameters'][tauv_idx][0]
		ha_magphys[ii] = threed_dutils.synthetic_halpha(sfr_10_mag[ii], tau1, tau2, -1.3, -0.7) / constants.L_sun.cgs.value
		ha_ext_mag[ii] = threed_dutils.charlot_and_fall_extinction(6563.0,tau1,tau2,-1.3,-0.7,kriek=False)
		met_mag[ii] = dat['model']['full_parameters'][mmet_idx]

		##### CLOUDY Halpha / empirical halpha, chain calculation
		if ii == 0: import triangle
		ratio = np.log10(dat['model_emline']['fluxchain'][:,ha_em]*constants.L_sun.cgs.value / dat['pextras']['flatchain'][:,emp_ha_idx])
		ha_ratio[ii,:] = triangle.quantile(ratio, [0.5, 0.84, 0.16])

		##### BPT information
		ratio = np.log10(dat['model_emline']['fluxchain'][:,oiii_em] / dat['model_emline']['fluxchain'][:,hb_em])
		oiii_hb[ii,:] = triangle.quantile(ratio, [0.5, 0.84, 0.16])
		try:
			ratio = np.log10(dat['model_emline']['fluxchain'][:,nii_em] / dat['model_emline']['fluxchain'][:,ha_em])
			nii_ha[ii,:] = triangle.quantile(ratio, [0.5, 0.84, 0.16])
		except ValueError as e:
			pass

		##### marginalized metallicity
		pmet[ii,0] = dat['pquantiles']['q50'][met_idx]
		pmet[ii,1] = dat['pquantiles']['q84'][met_idx]
		pmet[ii,2] = dat['pquantiles']['q16'][met_idx]

		##### marginalized dn4000
		dn4000[ii,0] = dat['spec_info']['q50'][dn4000_idx]
		dn4000[ii,1] = dat['spec_info']['q84'][dn4000_idx]
		dn4000[ii,2] = dat['spec_info']['q16'][dn4000_idx]

		##### marginalized dust properties + SFR
		d1[ii,0] = dat['pquantiles']['q50'][dust1_idx]
		d1[ii,1] = dat['pquantiles']['q84'][dust1_idx]
		d1[ii,2] = dat['pquantiles']['q16'][dust1_idx]

		d2[ii,0] = dat['pquantiles']['q50'][dust2_idx]
		d2[ii,1] = dat['pquantiles']['q84'][dust2_idx]
		d2[ii,2] = dat['pquantiles']['q16'][dust2_idx]

		didx[ii,0] = dat['pquantiles']['q50'][dinx_idx]
		didx[ii,1] = dat['pquantiles']['q84'][dinx_idx]
		didx[ii,2] = dat['pquantiles']['q16'][dinx_idx]

		sfr_10[ii,0] = dat['pextras']['q50'][sfr_10_idx_p]
		sfr_10[ii,1] = dat['pextras']['q84'][sfr_10_idx_p]
		sfr_10[ii,2] = dat['pextras']['q16'][sfr_10_idx_p]

		sfr_100[ii,0] = dat['pextras']['q50'][sfr_100_idx_p]
		sfr_100[ii,1] = dat['pextras']['q84'][sfr_100_idx_p]
		sfr_100[ii,2] = dat['pextras']['q16'][sfr_100_idx_p]

		##### marginalized extinction at Halpha wavelengths
		d1_chain = dat['pquantiles']['random_chain'][:,dust1_idx]
		d2_chain = dat['pquantiles']['random_chain'][:,dust2_idx]
		didx_chain = dat['pquantiles']['random_chain'][:,dinx_idx]
		ha_ext_chain = threed_dutils.charlot_and_fall_extinction(6563.0,d1_chain,d2_chain,-1.0,didx_chain,kriek=False)
		ha_ext[ii,:] = triangle.quantile(ha_ext_chain, [0.5, 0.84, 0.16])

	##### hdelta absorption
	# add in hdelta emission from cloudy, maybe
	hdel_flux = -ret_inf(alldata,'hdelta_lum',model='Prospectr')/constants.L_sun.cgs.value# - cloudy_hd[:,0,None]
	prosp['hdel_abs'] = np.log10(hdel_flux)[:,0]
	prosp['hdel_eqw'] = np.log10(hdel_flux/continuum[:,0,0,None])[:,0]

	prosp['bdec_cloudy_bfit'] = bdec_cloudy_bfit
	prosp['bdec_calc_bfit'] = bdec_calc_bfit
	prosp['bdec_cloudy_marg'] = bdec_cloudy_marg
	prosp['bdec_calc_marg'] = bdec_calc_marg
	prosp['cloudy_ha'] = cloudy_ha
	prosp['cloudy_ha_eqw'] = cloudy_ha / continuum[:,2,0,None]
	prosp['cloudy_hb'] = cloudy_hb
	prosp['cloudy_hb_eqw'] = cloudy_hb / continuum[:,1,0,None]
	prosp['cloudy_nii'] = cloudy_nii
	prosp['cloudy_nii_eqw'] = cloudy_nii / continuum[:,2,0,None]
	prosp['cloudy_oiii'] = cloudy_oiii
	prosp['cloudy_oiii_eqw'] = cloudy_oiii / continuum[:,1,0,None]
	prosp['oiii_hb'] = oiii_hb
	prosp['nii_ha'] = nii_ha
	prosp['ha_emp'] = ha_emp
	prosp['ha_emp_eqw'] = ha_emp / continuum[:,2,0,None]
	prosp['ha_ratio'] = ha_ratio
	prosp['met'] = pmet
	prosp['dn4000'] = dn4000
	prosp['d1'] = d1
	prosp['d2'] = d2
	prosp['didx'] = didx
	prosp['sfr_10'] = sfr_10
	prosp['sfr_100'] = sfr_100
	prosp['ha_ext'] = ha_ext

	mag['bdec'] = bdec_magphys
	mag['ha'] = ha_magphys
	mag['ha_eqw'] = ha_magphys / continuum[:,2,0]
	mag['sfr_10'] = sfr_10_mag
	mag['sfr_100'] = sfr_100_mag
	mag['sfr_100_marginalized'] = sfr_100_mag_marginalized
	mag['ha_ext'] = ha_ext_mag
	mag['met'] = np.log10(met_mag)

	eline_info = {'obs': obslines, 'mag': mag, 'prosp': prosp, 'objnames':objnames}

	return eline_info

def bpt_diagram(e_pinfo,hflag,outname=None):

	########################################
	## plot obs BPT, predicted BPT, resid ##
	########################################
	axlim = (-2.2,0.5,-1.0,1.0)

	# cuts first
	sn_ha = e_pinfo['obs']['f_ha'][:,0] / np.abs(e_pinfo['obs']['err_ha'])
	sn_hb = e_pinfo['obs']['f_hb'][:,0] / np.abs(e_pinfo['obs']['err_hb'])
	sn_oiii = e_pinfo['obs']['f_oiii'][:,0] / np.abs(e_pinfo['obs']['err_oiii'])
	sn_nii = e_pinfo['obs']['f_nii'][:,0] / np.abs(e_pinfo['obs']['err_nii'])

	keep_idx = np.squeeze((sn_ha > e_pinfo['obs']['sn_cut']) & \
		                  (sn_hb > e_pinfo['obs']['sn_cut']) & \
		                  (sn_oiii > e_pinfo['obs']['sn_cut']) & \
		                  (sn_nii > e_pinfo['obs']['sn_cut']))

	##### CREATE PLOT QUANTITIES
	mod_oiii_hb = e_pinfo['prosp']['oiii_hb'][keep_idx,:]
	mod_nii_ha = e_pinfo['prosp']['nii_ha'][keep_idx,:]

	obs_oiii_hb = e_pinfo['obs']['oiii_hb'][keep_idx]
	obs_oiii_hb_err = e_pinfo['obs']['oiii_hb_err'][keep_idx]
	obs_nii_ha = e_pinfo['obs']['nii_ha'][keep_idx]
	obs_nii_ha_err = e_pinfo['obs']['nii_ha_err'][keep_idx]

	##### AGN identifiers
	sfing, composite, agn = return_agn_str(keep_idx)
	keys = [sfing, composite, agn]
	colors = ['blue', 'purple', 'red']
	labels = ['SF', 'SF/AGN', 'AGN']

	##### herschel identifier
	hflag = [hflag[keep_idx],~hflag[keep_idx]]

	#### TWO PLOTS
	# first plot: observed BPT
	# second plot: model BPT
	# third plot: residuals versus residuals (obs - mod)
	fig1, ax1 = plt.subplots(1,3, figsize = (18.75,6))

	# loop and put points on plot
	for ii in xrange(len(labels)):
		for kk in xrange(len(hflag)):

			### update colors, define sample
			herschdict[kk].update(color=colors[ii])
			plt_idx = keys[ii] & hflag[kk]

			### errors for this sample
			err_obs_x = threed_dutils.asym_errors(obs_nii_ha[plt_idx], 
		                                           obs_nii_ha[plt_idx]+obs_nii_ha_err[plt_idx],
		                                           obs_nii_ha[plt_idx]-obs_nii_ha_err[plt_idx], log=True)
			err_obs_y = threed_dutils.asym_errors(obs_oiii_hb[plt_idx], 
		                                           obs_oiii_hb[plt_idx]+obs_oiii_hb_err[plt_idx],
		                                           obs_oiii_hb[plt_idx]-obs_oiii_hb_err[plt_idx], log=True)
			err_mod_x = threed_dutils.asym_errors(mod_nii_ha[plt_idx,0], 
		                                           mod_nii_ha[plt_idx,1],
		                                           mod_nii_ha[plt_idx,2], log=False)
			err_mod_y = threed_dutils.asym_errors(mod_oiii_hb[plt_idx,0], 
		                                           mod_oiii_hb[plt_idx,1],
		                                           mod_oiii_hb[plt_idx,2], log=False)

			ax1[0].errorbar(np.log10(obs_nii_ha[plt_idx]), np.log10(obs_oiii_hb[plt_idx]), xerr=err_obs_x, yerr=err_obs_y,
				           linestyle=' ',**herschdict[kk])
			ax1[1].errorbar(mod_nii_ha[plt_idx,0], mod_oiii_hb[plt_idx,0], xerr=err_mod_x, yerr=err_mod_y,
				           linestyle=' ',**herschdict[kk])
			ax1[2].errorbar(np.log10(obs_nii_ha[plt_idx])-mod_nii_ha[plt_idx,0], 
			                np.log10(obs_oiii_hb[plt_idx])-mod_oiii_hb[plt_idx,0],
				            linestyle=' ',**herschdict[kk])

	#### plot bpt line
	# Kewley+06
	# log(OIII/Hbeta) < 0.61 /[log(NII/Ha) - 0.05] + 1.3 (star-forming to the left and below)
	# log(OIII/Hbeta) < 0.61 /[log(NII/Ha) - 0.47] + 1.19 (between AGN and star-forming)
	# x = 0.61 / (y-0.47) + 1.19
	x1 = np.linspace(-2.2,0.0,num=50)
	x2 = np.linspace(-2.2,0.35,num=50)
	for ax in ax1[:2]:
		ax.plot(x1,0.61 / (x1 - 0.05) + 1.3 , linestyle='--',color='0.5')
		ax.plot(x2,0.61 / (x2-0.47) + 1.19, linestyle='--',color='0.5')


	ax1[0].set_xlabel(r'log([NII 6583]/H$_{\alpha}$) [observed]')
	ax1[0].set_ylabel(r'log([OIII 5007]/H$_{\beta}$) [observed]')
	ax1[0].axis(axlim)

	ax1[1].set_xlabel(r'log([NII 6583]/H$_{\alpha}$) [Prospector]')
	ax1[1].set_ylabel(r'log([OIII 5007]/H$_{\beta}$) [Prospector]')
	ax1[1].axis(axlim)

	ax1[2].set_xlabel(r'log([NII 6583]/H$_{\alpha}$) [obs - model]')
	ax1[2].set_ylabel(r'log([OIII 5007]/H$_{\beta}$) [obs - model]')

	plt.tight_layout()
	plt.savefig(outname,dpi=dpi)
	plt.close()

def obs_vs_kennicutt_ha(e_pinfo,hflag,outname='test.png',outname_cloudy='test_cloudy.png',
						outname_ha_inpt='test_ha_inpt.png',
						outname_sfr_margcomp='test_sfr_margcomp.png',
	                    standardized_ha_axlim = True):
	
	#################
	#### plot observed Halpha versus model Halpha from Kennicutt relationship
	#################

	# S/N(Ha) > x, EQW (Ha) > x
	sn_ha = np.abs(e_pinfo['obs']['f_ha'][:,0] / e_pinfo['obs']['err_ha'])
	keep_idx = np.squeeze((sn_ha > e_pinfo['obs']['sn_cut']) & \
		                  (e_pinfo['obs']['eqw_ha'][:,0] > e_pinfo['obs']['eqw_cut']))

	##### create plot quantities
	pl_ha_mag = np.log10(e_pinfo['mag']['ha_eqw'][keep_idx])
	pl_ha_obs = np.log10(e_pinfo['obs']['eqw_ha'][keep_idx,:])
	pl_ha_emp = np.log10(e_pinfo['prosp']['ha_emp_eqw'][keep_idx,:]) 
	pl_ha_cloudy = np.log10(e_pinfo['prosp']['cloudy_ha_eqw'][keep_idx,:]) 
	pmet = e_pinfo['prosp']['met'][keep_idx,:]
	pl_ha_ratio = e_pinfo['prosp']['ha_ratio'][keep_idx,:]

	#### plot3+plot4 quantities
	mmet = e_pinfo['mag']['met'][keep_idx]
	msfr10 = np.log10(np.clip(e_pinfo['mag']['sfr_10'][keep_idx],minsfr,np.inf))
	msfr100 = np.log10(np.clip(e_pinfo['mag']['sfr_100'][keep_idx],minsfr,np.inf))
	msfr100_marginalized = np.log10(np.clip(10**e_pinfo['mag']['sfr_100_marginalized'][keep_idx,:],minsfr,np.inf))
	mha_ext = np.log10(1./e_pinfo['mag']['ha_ext'][keep_idx])
	ha_ext = np.log10(1./e_pinfo['prosp']['ha_ext'][keep_idx,:])
	sfr10 = np.log10(np.clip(e_pinfo['prosp']['sfr_10'][keep_idx,:],minsfr,np.inf))
	sfr100 = np.log10(np.clip(e_pinfo['prosp']['sfr_100'][keep_idx,:],minsfr,np.inf))

	##### AGN identifiers
	sfing, composite, agn = return_agn_str(keep_idx)
	keys = [sfing, composite, agn]
	colors = ['blue', 'purple', 'red']
	labels = ['SF', 'SF/AGN', 'AGN']

	##### herschel identifier
	hflag = [hflag[keep_idx],~hflag[keep_idx]]

	#### THREE PLOTS
	# first plot: (obs v prosp) Kennicutt, (obs v mag) Kennicutt
	# second plot: (kennicutt v CLOUDY), (kennicutt/cloudy v met)
	# third plot: (mag SFR10 v Prosp SFR10), (mag ext(ha) v Prosp ext(ha)), (mag met v Prosp met)
	# fourth plot: (mag SFR100 v Prosp SFR100), (mag SFR10 v Prosp SFR10)
	fig1, ax1 = plt.subplots(1,2, figsize = (12.5,6))
	fig2, ax2 = plt.subplots(1,2, figsize = (12.5,6))
	fig3, ax3 = plt.subplots(1,3, figsize = (18.75,6))
	fig4, ax4 = plt.subplots(1,2, figsize = (12.5,6))

	for ii in xrange(len(labels)):
		for kk in xrange(len(hflag)):

			### update colors, define region
			herschdict[kk].update(color=colors[ii])
			plt_idx = keys[ii] & hflag[kk]

			### setup errors
			prosp_emp_err = threed_dutils.asym_errors(pl_ha_emp[plt_idx,0],pl_ha_emp[plt_idx,1], pl_ha_emp[plt_idx,2],log=False)
			prosp_cloud_err = threed_dutils.asym_errors(pl_ha_cloudy[plt_idx,0],pl_ha_cloudy[plt_idx,1], pl_ha_cloudy[plt_idx,2],log=False)
			obs_err = threed_dutils.asym_errors(pl_ha_obs[plt_idx,0],pl_ha_obs[plt_idx,1], pl_ha_obs[plt_idx,2],log=False)
			ratio_err = threed_dutils.asym_errors(pl_ha_ratio[plt_idx,0],pl_ha_ratio[plt_idx,1], pl_ha_ratio[plt_idx,2],log=False)
			pmet_err = threed_dutils.asym_errors(pmet[plt_idx,0],pmet[plt_idx,1], pmet[plt_idx,2],log=False)
			ha_ext_err = threed_dutils.asym_errors(ha_ext[plt_idx,0], ha_ext[plt_idx,1], ha_ext[plt_idx,2],log=False)
			sfr10_err = threed_dutils.asym_errors(sfr10[plt_idx,0], sfr10[plt_idx,1], sfr10[plt_idx,2],log=False)
			sfr100_err = threed_dutils.asym_errors(sfr100[plt_idx,0], sfr100[plt_idx,1], sfr100[plt_idx,2],log=False)
			msfr100_err = threed_dutils.asym_errors(msfr100_marginalized[plt_idx,1], msfr100_marginalized[plt_idx,0], msfr100_marginalized[plt_idx,2],log=False)


			ax1[0].errorbar(pl_ha_obs[plt_idx,0], pl_ha_emp[plt_idx,0], xerr=obs_err, yerr=prosp_emp_err,
				           linestyle=' ',**herschdict[kk])
			ax1[1].errorbar(pl_ha_obs[plt_idx,0], pl_ha_mag[plt_idx], xerr=obs_err,
				           linestyle=' ',**herschdict[kk])
			ax2[0].errorbar(pl_ha_cloudy[plt_idx,0], pl_ha_emp[plt_idx,0], xerr=prosp_emp_err, yerr=prosp_emp_err, 
				           linestyle=' ',**herschdict[kk])
			ax2[1].errorbar(pmet[plt_idx,0],pl_ha_ratio[plt_idx,0],
				           linestyle=' ',**herschdict[kk])

			ax3[0].errorbar(sfr10[plt_idx,0], msfr10[plt_idx], xerr=sfr10_err, 
				           linestyle=' ',**herschdict[kk])
			ax3[1].errorbar(ha_ext[plt_idx,0], mha_ext[plt_idx], xerr=ha_ext_err, 
				           linestyle=' ',**herschdict[kk])
			ax3[2].errorbar(pmet[plt_idx,0], mmet[plt_idx], xerr=pmet_err, 
				           linestyle=' ',**herschdict[kk])

			ax4[0].errorbar(msfr100_marginalized[plt_idx,1], msfr100[plt_idx], xerr=msfr100_err, 
	           linestyle=' ',**herschdict[kk])
			ax4[1].errorbar(sfr100[plt_idx,0], msfr100_marginalized[plt_idx,1], xerr=sfr100_err, yerr=msfr100_err,
	           linestyle=' ',**herschdict[kk])

	ax1[0].set_xlabel(r'log(H$_{\alpha}$ EQW) [observed]')
	ax1[0].set_ylabel(r'log(Kennicutt H$_{\alpha}$ EQW) [Prospector]')
	if standardized_ha_axlim:
		ax1[0].axis((halim[0],halim[1],halim[0],halim[1]))
		ax1[0].plot(halim,halim,linestyle='--',color='0.1',alpha=0.8)
	else:
		ax1[0] = threed_dutils.equalize_axes(ax1[0], pl_ha_obs[:,0], pl_ha_emp[:,0])
	off,scat = threed_dutils.offset_and_scatter(pl_ha_obs[:,0], pl_ha_emp[:,0], biweight=True)
	ax1[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex', transform = ax1[0].transAxes,horizontalalignment='right')
	ax1[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ ' dex', transform = ax1[0].transAxes,horizontalalignment='right')

	ax1[1].set_xlabel(r'log(H$_{\alpha}$ EQW) [observed]')
	ax1[1].set_ylabel(r'log(Kennicutt H$_{\alpha}$ EQW) [MAGPHYS]')
	if standardized_ha_axlim:
		ax1[1].axis((halim[0],halim[1],halim[0],halim[1]))
		ax1[1].plot(halim,halim,linestyle='--',color='0.1',alpha=0.8)
	else:
		ax1[1] = threed_dutils.equalize_axes(ax1[1], pl_ha_obs[:,0], pl_ha_mag)
	off,scat = threed_dutils.offset_and_scatter(pl_ha_obs[:,0], pl_ha_mag, biweight=True)
	ax1[1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex', transform = ax1[1].transAxes,horizontalalignment='right')
	ax1[1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ ' dex', transform = ax1[1].transAxes,horizontalalignment='right')

	ax2[0].set_xlabel(r'log(CLOUDY H$_{\alpha}$ EQW) [Prospector]')
	ax2[0].set_ylabel(r'log(Kennicutt H$_{\alpha}$ EQW) [Prospector]')
	ax2[0] = threed_dutils.equalize_axes(ax2[0], pl_ha_cloudy[:,0], pl_ha_emp[:,0])
	off,scat = threed_dutils.offset_and_scatter(pl_ha_cloudy[:,0], pl_ha_emp[:,0], biweight=True)
	ax2[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex', transform = ax2[0].transAxes,horizontalalignment='right')
	ax2[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ ' dex', transform = ax2[0].transAxes,horizontalalignment='right')

	ax2[1].set_xlabel(r'log(Z/Z$_{\odot}$) [Prospector]')
	ax2[1].set_ylabel(r'log(H$_{\alpha}$ CLOUDY/empirical) [Prospector]')

	ax3[0].set_xlabel(r'log(SFR [10 Myr]) [marginalized, Prospector]')
	ax3[0].set_ylabel(r'log(SFR [10 Myr]) [best-fit, MAGPHYS]')
	ax3[0] = threed_dutils.equalize_axes(ax3[0], sfr10[:,0], msfr10)
	off,scat = threed_dutils.offset_and_scatter(sfr10[:,0], msfr10, biweight=True)
	ax3[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex', transform = ax3[0].transAxes,horizontalalignment='right')
	ax3[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ ' dex', transform = ax3[0].transAxes,horizontalalignment='right')

	ax3[1].set_xlabel(r'log(F$_{emit}$/F$_{obs}$) (6563 $\AA$) [marginalized, Prospector]')
	ax3[1].set_ylabel(r'log(F$_{emit}$/F$_{obs}$) (6563 $\AA$) [best-fit, MAGPHYS]')
	ax3[1] = threed_dutils.equalize_axes(ax3[1], ha_ext[:,0], mha_ext)
	off,scat = threed_dutils.offset_and_scatter(ha_ext[:,0], mha_ext, biweight=True)
	ax3[1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax3[1].transAxes,horizontalalignment='right')
	ax3[1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax3[1].transAxes,horizontalalignment='right')

	ax3[2].set_xlabel(r'log(Z/Z$_{\odot}$) [marginalized, Prospector]')
	ax3[2].set_ylabel(r'log(Z/Z$_{\odot}$) [best-fit, MAGPHYS]')
	ax3[2] = threed_dutils.equalize_axes(ax3[2], pmet[:,0], mmet)
	off,scat = threed_dutils.offset_and_scatter(pmet[:,0], mmet, biweight=True)
	ax3[2].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax3[2].transAxes,horizontalalignment='right')
	ax3[2].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax3[2].transAxes,horizontalalignment='right')

	ax4[0].set_xlabel(r'log(SFR [100 Myr]) [marginalized, MAGPHYS]')
	ax4[0].set_ylabel(r'log(SFR [100 Myr]) [best-fit, MAGPHYS]')
	ax4[0] = threed_dutils.equalize_axes(ax4[0], msfr100_marginalized[:,1], msfr100)
	off,scat = threed_dutils.offset_and_scatter(msfr100_marginalized[:,1], msfr100, biweight=True)
	ax4[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex', transform = ax4[0].transAxes,horizontalalignment='right')
	ax4[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ ' dex', transform = ax4[0].transAxes,horizontalalignment='right')

	ax4[1].set_xlabel(r'log(SFR [100 Myr]) [marginalized, Prospector]')
	ax4[1].set_ylabel(r'log(SFR [100 Myr]) [marginalized, MAGPHYS]')
	ax4[1] = threed_dutils.equalize_axes(ax4[1], sfr100[:,0], msfr100_marginalized[:,1])
	off,scat = threed_dutils.offset_and_scatter(sfr100[:,0], msfr100_marginalized[:,1], biweight=True)
	ax4[1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) +' dex', transform = ax4[1].transAxes,horizontalalignment='right')
	ax4[1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ ' dex', transform = ax4[1].transAxes,horizontalalignment='right')



	fig1.tight_layout()
	fig1.savefig(outname,dpi=dpi)
	fig2.tight_layout()
	fig2.savefig(outname_cloudy,dpi=dpi)
	fig3.tight_layout()
	fig3.savefig(outname_ha_inpt,dpi=dpi)
	fig4.tight_layout()
	fig4.savefig(outname_sfr_margcomp,dpi=dpi)
	plt.close()
	print 1/0

def bdec_corr_eqn(x, hdel_eqw_obs, hdel_eqw_model,
	              halpha_obs, hbeta_obs,
	              halpha_abs_eqw, hbeta_abs_eqw,
	              halpha_continuum, hbeta_continuum,
	              additive):

	##### how do we translate Hdelta offset into Halpha / Hbeta offset?
	##### then, pull out measured halpha, hbeta EQW to adjust for discrepancy in balmer absorption
	if additive:
		ratio = hdel_eqw_obs - hdel_eqw_model
		use_ratio = ratio*x

		halpha_new = halpha_obs + use_ratio * halpha_continuum
		hbeta_new = hbeta_obs + use_ratio * hbeta_continuum

	else:
		ratio = hdel_eqw_obs / hdel_eqw_model
		use_ratio = (ratio-1.0)*x + 1.0

		halpha_new = halpha_obs + halpha_abs_eqw*(use_ratio-1) * halpha_continuum
		hbeta_new = hbeta_obs + hbeta_abs_eqw*(use_ratio-1) * hbeta_continuum

	##### bdec corrected
	bdec_corrected = bdec_to_ext(halpha_new/hbeta_new)

	return bdec_corrected

def minimize_bdec_corr_eqn(x, hdel_eqw_obs, hdel_eqw_model, halpha_obs, hbeta_obs,
	                          halpha_abs_eqw, hbeta_abs_eqw,
	                          halpha_continuum, hbeta_continuum,
	                          additive,
	                          bdec_model):

	'''
	minimize the scatter in bdec_to_ext(obs_bdec), bdec_to_ext(model_bdec)
	by some function bdec_corr_eqw() described above
	'''

	bdec_corrected = bdec_corr_eqn(x, hdel_eqw_obs, hdel_eqw_model,
	                                  halpha_obs, hbeta_obs,
						              halpha_abs_eqw, hbeta_abs_eqw,
						              halpha_continuum, hbeta_continuum,
						              additive)

	off, scat = threed_dutils.offset_and_scatter(bdec_corrected, bdec_model,biweight=True)

	return scat

def bdec_correction(e_pinfo,hflag,outname='test.png',model='Prospectr',
	                additive=False):

	#################
	#### plot observed Halpha versus expected (PROSPECTR ONLY)
	#################
	# SAME as obs_vs_prosp_balmlines
	# PLUS hdelta_dn_comp
	# S/N cut
	sn_ha = np.abs(e_pinfo['obs']['f_ha'][:,0] / e_pinfo['obs']['err_ha'])
	sn_hb = np.abs(e_pinfo['obs']['f_hb'][:,0] / e_pinfo['obs']['err_hb'])

	agn_string = return_agn_str(np.ones_like(hflag),string=True)

	#### for now, aggressive S/N cut
	keep_idx = np.squeeze((sn_ha > e_pinfo['obs']['sn_cut']) & \
		                  (sn_hb > e_pinfo['obs']['sn_cut']) & \
		                  (e_pinfo['obs']['eqw_ha'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['eqw_hb'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['f_ha'][:,0] > 0) & \
		                  (e_pinfo['obs']['f_hb'][:,0] > 0) & \
		                  (np.abs((e_pinfo['obs']['hdel'][:,0]/e_pinfo['obs']['hdel_err'])) > e_pinfo['obs']['hdelta_sn_cut']) & \
		                  (e_pinfo['obs']['hdel'][:,0] > 0) & \
		                  (agn_string != 'AGN') & \
		                  (e_pinfo['obs']['eqw_hdel'][:,0] > 1e-7))

	##### write down Hdelta absorption measurements
	hdel_obs = e_pinfo['obs']['eqw_hdel'][keep_idx,0]
	hdel_prosp_bestfit = 10**e_pinfo['prosp']['hdel_eqw'][keep_idx]

	if additive:
		ratio = hdel_obs - hdel_prosp_bestfit
	else:
		ratio = hdel_obs / hdel_prosp_bestfit

	##### write down Halpha + Hbeta absorption, emission in model
	# N.B. EQW(emission) ~ EQW(absorption) for almost every Hbeta in this selection
	# in some cases, flux_measured(i.e., observed emission + absorption) < Hbeta absorption, but never by more than 20%
	# presumably in these cases, the Hbeta absorption feature is resolvable separately from the emission
	halpha_continuum = e_pinfo['obs']['continuum'][keep_idx,2,0]
	hbeta_continuum = e_pinfo['obs']['continuum'][keep_idx,1,0]
	halpha_abs_bestfit = 10**e_pinfo['prosp']['halpha_abs'][keep_idx]/constants.L_sun.cgs.value / halpha_continuum
	hbeta_abs_bestfit = 10**e_pinfo['prosp']['hbeta_abs'][keep_idx]/constants.L_sun.cgs.value / hbeta_continuum
	halpha_obs = e_pinfo['obs']['f_ha'][keep_idx,0]
	hbeta_obs = e_pinfo['obs']['f_hb'][keep_idx,0]

	##### observed, model Balmer decrements
	bdec_cloudy_marg = bdec_to_ext(e_pinfo['prosp']['bdec_cloudy_marg'][keep_idx,:])
	bdec_measured = bdec_to_ext(e_pinfo['obs']['bdec'][keep_idx])
	bdec_ratio = bdec_cloudy_marg[:,0] - bdec_measured

	##### best-fit offset
	sol = minimize(minimize_bdec_corr_eqn, 0.5,
				   args=(hdel_obs, hdel_prosp_bestfit,
	                     halpha_obs, hbeta_obs,
	                     halpha_abs_bestfit, hbeta_abs_bestfit,
	                     halpha_continuum, hbeta_continuum, additive,
	                     bdec_cloudy_marg[:,0]))
	bdec_corrected = bdec_corr_eqn(sol.x, hdel_obs, hdel_prosp_bestfit, 
                                          halpha_obs, hbeta_obs, 
                                          halpha_abs_bestfit, hbeta_abs_bestfit, 
                                          halpha_continuum, hbeta_continuum,
                                          additive,)


	##### PLOT
	fig, ax = plt.subplots(1,3, figsize = (18.75,6))
	axlim = (-1.2,1.5,-1.2,1.5)

	ax[0].errorbar(bdec_measured, bdec_cloudy_marg[:,0], linestyle=' ', **nhargs)
	ax[0].set_xlabel(r'A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$ [observed]')
	ax[0].set_ylabel(r'A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$ [Prospector]')
	off,scat = threed_dutils.offset_and_scatter(bdec_measured, bdec_cloudy_marg[:,0],biweight=True)
	ax[0].axis(axlim)
	ax[0].plot([axlim[0],axlim[1]],[axlim[0],axlim[1]],linestyle='--',color='0.1',alpha=0.8)
	ax[0].text(0.96,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax[0].transAxes,horizontalalignment='right')
	ax[0].text(0.96,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax[0].transAxes,horizontalalignment='right')
	ax[0].text(0.05,0.9, r'H$_{\alpha}$,H$_{\beta}$ emission EQW >'+str(int(e_pinfo['obs']['eqw_cut'])), transform = ax[0].transAxes)
	ax[0].text(0.05,0.85, r'H$_{\delta}$ absorption S/N >'+str(int(e_pinfo['obs']['hdelta_sn_cut'])), transform = ax[0].transAxes,horizontalalignment='left')
	ax[0].text(0.05,0.80, r'BPT AGN excluded', transform = ax[0].transAxes,horizontalalignment='left')
	ax[0].text(0.05,0.75, r'N = '+str(np.sum(keep_idx)), transform = ax[0].transAxes,horizontalalignment='left')

	ax[1].errorbar(bdec_corrected, bdec_cloudy_marg[:,0], linestyle=' ', **nhargs)
	ax[1].set_xlabel(r'A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$ [observed,corrected]')
	ax[1].set_ylabel(r'A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$ [Prospector]')
	off,scat = threed_dutils.offset_and_scatter(bdec_corrected, bdec_cloudy_marg[:,0],biweight=True)
	ax[1].axis(axlim)
	ax[1].plot([axlim[0],axlim[1]],[axlim[0],axlim[1]],linestyle='--',color='0.1',alpha=0.8)
	ax[1].text(0.96,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax[1].transAxes,horizontalalignment='right')
	ax[1].text(0.96,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax[1].transAxes,horizontalalignment='right')

	# how to make residual plot?
	if additive:
		ax[2].errorbar(bdec_ratio, ratio, linestyle=' ', **nhargs)
		ax[2].set_xlabel(r'A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$ [model - measured]')
		ax[2].set_ylabel(r'H$\delta_{obs}$ / H$\delta_{model}$')
		ax[2].axis((-1.5,1.5,-3.0,3.0))
		ax[2].plot([0.0,0.0],[-3.0,3.0],linestyle='--',color='0.1',alpha=0.8)
		ax[2].plot([-1.5,1.5],[0.0,0.0],linestyle='--',color='0.1',alpha=0.8)
	else:
		ax[2].errorbar(bdec_ratio, ratio, linestyle=' ', **nhargs)
		ax[2].set_xlabel(r'A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$ [model - measured]')
		ax[2].set_ylabel(r'H$\delta_{obs}$ / H$\delta_{model}$')
		ax[2].axis((-1.5,1.5,0.0,2.0))
		ax[2].plot([0.0,0.0],[0.0,2.0],linestyle='--',color='0.1',alpha=0.8)
		ax[2].plot([-1.5,1.5],[1.0,1.0],linestyle='--',color='0.1',alpha=0.8)
	
	plt.tight_layout()
	plt.savefig(outname,dpi=dpi)
	plt.close()
	os.system('open '+outname)
	print 1/0

def obs_vs_prosp_balmlines(e_pinfo,hflag,outname='test.png',model='Prospectr',
	                       standardized_ha_axlim = True):

	#################
	#### plot observed Halpha versus expected (PROSPECTR ONLY)
	#################

	# S/N cut
	sn_ha = np.abs(e_pinfo['obs']['f_ha'][:,0] / e_pinfo['obs']['err_ha'])
	sn_hb = np.abs(e_pinfo['obs']['f_hb'][:,0] / e_pinfo['obs']['err_hb'])

	keep_idx = np.squeeze((sn_ha > e_pinfo['obs']['sn_cut']) & \
		                  (sn_hb > e_pinfo['obs']['sn_cut']) & \
		                  (e_pinfo['obs']['eqw_ha'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['eqw_hb'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['f_ha'][:,0] > 0) & \
		                  (e_pinfo['obs']['f_hb'][:,0] > 0))

	f_ha = e_pinfo['obs']['eqw_ha'][keep_idx,:]
	f_hb = e_pinfo['obs']['eqw_hb'][keep_idx,:]
	model_ha = e_pinfo['prosp']['cloudy_ha_eqw'][keep_idx,:]
	model_hb = e_pinfo['prosp']['cloudy_hb_eqw'][keep_idx,:]

	##### AGN identifiers
	sfing, composite, agn = return_agn_str(keep_idx)
	keys = [sfing, composite, agn]

	##### herschel identifier
	hflag = [hflag[keep_idx],~hflag[keep_idx]]

	##### plot!
	fig, ax = plt.subplots(1,3, figsize = (18.75,6))

	xplot_ha = np.log10(model_ha[:,0])
	yplot_ha = np.log10(f_ha[:,0])

	xplot_hb = np.log10(model_hb[:,0])
	yplot_hb = np.log10(f_hb[:,0])
	norm_errs = []
	norm_flag = []

	for ii in xrange(len(labels)):
		for kk in xrange(len(hflag)):

			### update colors, define region
			herschdict[kk].update(color=colors[ii])
			plt_idx = keys[ii] & hflag[kk]

			### setup errors
			xerr_ha = threed_dutils.asym_errors(f_ha[plt_idx,0], f_ha[plt_idx,1], f_ha[plt_idx,2],log=True)
			xerr_hb = threed_dutils.asym_errors(f_hb[plt_idx,0],f_hb[plt_idx,1], f_hb[plt_idx,2],log=True)

			yerr_ha = threed_dutils.asym_errors(model_ha[plt_idx,0],model_ha[plt_idx,1], model_ha[plt_idx,2],log=True)
			yerr_hb = threed_dutils.asym_errors(model_hb[plt_idx,0],model_hb[plt_idx,1], model_hb[plt_idx,2],log=True)

			norm_errs.append(normalize_error(yplot_ha[plt_idx],yerr_ha,xplot_ha[plt_idx],xerr_ha))
			norm_flag.append([labels[ii]]*np.sum(plt_idx))

			ax[0].errorbar(xplot_ha[plt_idx], yplot_ha[plt_idx], yerr=yerr_ha, xerr=xerr_ha, 
				           linestyle=' ',**herschdict[kk])
			ax[1].errorbar(xplot_hb[plt_idx], yplot_hb[plt_idx], yerr=yerr_hb, xerr=xerr_hb,
	                       linestyle=' ',**herschdict[kk])
			ax[2].errorbar(xplot_ha[plt_idx] - yplot_ha[plt_idx],xplot_hb[plt_idx] - yplot_hb[plt_idx],
					       linestyle=' ',**herschdict[kk])

	ax[0].set_ylabel(r'log(H$_{\alpha}$ EQW) [Prospector]')
	ax[0].set_xlabel(r'log(H$_{\alpha}$ EQW) [observed]')
	if standardized_ha_axlim:
		ax[0].axis((halim[0],halim[1],halim[0],halim[1]))
		ax[0].plot(halim,halim,linestyle='--',color='0.1',alpha=0.8)
	else:
		ax[0] = threed_dutils.equalize_axes(ax[0],xplot_ha,yplot_ha)
	off,scat = threed_dutils.offset_and_scatter(xplot_ha,yplot_ha,biweight=True)
	ax[0].text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat)+ ' dex',
			  transform = ax[0].transAxes,horizontalalignment='right')
	ax[0].text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
			      transform = ax[0].transAxes,horizontalalignment='right')
	ax[0].legend(loc=2)

	ax[1].set_ylabel(r'log(H$_{\beta}$ EQW) [Prospector]')
	ax[1].set_xlabel(r'log(H$_{\beta}$ EQW) [observed]')
	ax[1] = threed_dutils.equalize_axes(ax[1],xplot_hb,yplot_hb)
	off,scat = threed_dutils.offset_and_scatter(xplot_hb,yplot_hb,biweight=True)
	ax[1].text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat)+ ' dex',
			  transform = ax[1].transAxes,horizontalalignment='right')
	ax[1].text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
			      transform = ax[1].transAxes,horizontalalignment='right')


	ax[2].set_ylabel(r'log(model/obs) H$_{\alpha}$)')
	ax[2].set_xlabel(r'log(model/obs) H$_{\beta}$)')
	max = np.max([np.abs(ax[2].get_ylim()).max(),np.abs(ax[2].get_xlim()).max()])
	ax[2].plot([0.0,0.0],[-max,max],linestyle='--',alpha=1.0,color='0.4')
	ax[2].plot([-max,max],[0.0,0.0],linestyle='--',alpha=1.0,color='0.4')
	ax[2].axis((-max,max,-max,max))

	plt.tight_layout()
	plt.savefig(outname,dpi=dpi)
	plt.close()

	return norm_errs, norm_flag

def obs_vs_model_hdelta_dn(e_pinfo,hflag,outname=None):

	min = -1.0
	max = 1.3
	eqw_plotlim = (min,max,min,max)

	### define limits
	good_idx = (np.abs((e_pinfo['obs']['hdel'][:,0]/ e_pinfo['obs']['hdel_err'])) > e_pinfo['obs']['hdelta_sn_cut']) & \
	           (e_pinfo['obs']['hdel'][:,0] > 0) & \
	           (e_pinfo['obs']['eqw_hdel'][:,0] > 1e-7)

	### define plot quantities
	dn4000_obs = e_pinfo['obs']['dn4000'][good_idx]
	dn4000_prosp = e_pinfo['prosp']['dn4000'][good_idx,0]
	dn4000_prosp_errs = threed_dutils.asym_errors(e_pinfo['prosp']['dn4000'][good_idx,0],e_pinfo['prosp']['dn4000'][good_idx,1],e_pinfo['prosp']['dn4000'][good_idx,2])
	dn4000_mag = e_pinfo['mag']['dn4000'][good_idx]

	hdel_obs = e_pinfo['obs']['eqw_hdel'][good_idx,0]
	hdel_plot_errs = threed_dutils.asym_errors(e_pinfo['obs']['eqw_hdel'][good_idx,0], e_pinfo['obs']['eqw_hdel'][good_idx,1], e_pinfo['obs']['eqw_hdel'][good_idx,2], log=True)
	hdel_prosp = e_pinfo['prosp']['hdel_eqw'][good_idx]
	hdel_mag = e_pinfo['mag']['hdel_eqw'][good_idx]

	##### AGN identifiers
	sfing, composite, agn = return_agn_str(good_idx)
	norm_flag = np.empty(np.sum(good_idx), dtype='|S8')
	norm_flag[sfing] = labels[0]
	norm_flag[composite] = labels[1]
	norm_flag[agn] = labels[2]

	### plot comparison
	fig, ax = plt.subplots(2,2, figsize = (15,15))

	ax[0,0].errorbar(dn4000_obs, dn4000_prosp, yerr=dn4000_prosp_errs, linestyle=' ', **nhargs)
	ax[0,0].set_xlabel(r'observed D$_n$(4000)')
	ax[0,0].set_ylabel(r'Prospector D$_n$(4000)')
	ax[0,0] = threed_dutils.equalize_axes(ax[0,0], dn4000_obs, dn4000_prosp)
	off,scat = threed_dutils.offset_and_scatter(dn4000_obs, dn4000_prosp,biweight=True)
	ax[0,0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax[0,0].transAxes,horizontalalignment='right')
	ax[0,0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax[0,0].transAxes,horizontalalignment='right')
	norm_errs = normalize_error(dn4000_obs,[np.zeros_like(dn4000_obs),np.zeros_like(dn4000_obs)],dn4000_prosp,dn4000_prosp_errs)

	ax[0,1].errorbar(dn4000_obs, dn4000_mag, linestyle=' ', **nhargs)
	ax[0,1].set_xlabel(r'observed D$_n$(4000)')
	ax[0,1].set_ylabel(r'MAGPHYS D$_n$(4000)')
	ax[0,1] = threed_dutils.equalize_axes(ax[0,1], dn4000_obs, dn4000_mag)
	off,scat = threed_dutils.offset_and_scatter(dn4000_obs, dn4000_mag,biweight=True)
	ax[0,1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax[0,1].transAxes,horizontalalignment='right')
	ax[0,1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax[0,1].transAxes,horizontalalignment='right')

	ax[1,0].errorbar(np.log10(hdel_obs), hdel_prosp, xerr=hdel_plot_errs, linestyle=' ', **nhargs)
	ax[1,0].set_xlabel(r'observed log(H$_{\delta}$ EQW)')
	ax[1,0].set_ylabel(r'Prospector log(H$_{\delta}$ EQW)')
	#ax[1,0] = threed_dutils.equalize_axes(ax[1,0], np.log10(hdel_obs), hdel_prosp)
	off,scat = threed_dutils.offset_and_scatter(np.log10(hdel_obs), hdel_prosp,biweight=True)
	ax[1,0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat) + ' dex', transform = ax[1,0].transAxes,horizontalalignment='right')
	ax[1,0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off) + ' dex', transform = ax[1,0].transAxes,horizontalalignment='right')
	ax[1,0].axis(eqw_plotlim)
	ax[1,0].plot([min,max],[min,max],linestyle='--',color='0.1',alpha=0.8)

	ax[1,1].errorbar(np.log10(hdel_obs), hdel_mag[:,0], xerr=hdel_plot_errs, linestyle=' ', **nhargs)
	ax[1,1].set_xlabel(r'observed log(H$_{\delta}$ EQW)')
	ax[1,1].set_ylabel(r'MAGPHYS log(H$_{\delta}$ EQW)')
	#ax[1,1] = threed_dutils.equalize_axes(ax[1,1], np.log10(hdel_obs), hdel_mag[:,0])
	off,scat = threed_dutils.offset_and_scatter(np.log10(hdel_obs), hdel_mag[:,0],biweight=True)
	ax[1,1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax[1,1].transAxes,horizontalalignment='right')
	ax[1,1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax[1,1].transAxes,horizontalalignment='right')
	ax[1,1].axis(eqw_plotlim)
	ax[1,1].plot([min,max],[min,max],linestyle='--',color='0.1',alpha=0.8)


	plt.savefig(outname, dpi=dpi)
	plt.close()

	return norm_errs, norm_flag

def bdec_to_ext(bdec):
	return 2.5*np.log10(bdec/2.86)

def normalize_error(obs,obserr,mod,moderr):
	
	# define output
	out = np.zeros_like(obs)
	
	# find out which side of error bar to use
	undershot = obs > mod
	
	# create output
	out[~undershot] = (obs[~undershot] - mod[~undershot]) / np.sqrt(moderr[0][~undershot]**2+obserr[0][~undershot]**2)
	out[undershot] = (obs[undershot] - mod[undershot]) / np.sqrt(moderr[1][undershot]**2+obserr[1][undershot]**2)

	return out

def gauss_fit(x,y):

	from astropy.modeling import fitting, functional_models
	init = functional_models.Gaussian1D(mean=0.0,stddev=1,amplitude=1)
	fitter = fitting.LevMarLSQFitter()
	fit = fitter(init,x,y)

	return fit


def onesig_error_plot(bdec_errs,bdec_flag,dn4000_errs,dn4000_flag,ha_errs,ha_flag,outbase):


	# NOTE: THROWING OUT HUGE OUTLIERS (80sigma)
	# next step: pass in an AGN / composite mask, make plot with and without AGN

	kwargs = {'color':'0.5','alpha':0.8,'histtype':'bar','lw':2,'normed':1,'range':(-80,80)}
	nbins = 200

	x = [np.array([item for sublist in bdec_errs for item in sublist]),
	     dn4000_errs,
	     np.array([item for sublist in ha_errs for item in sublist])]
	tits = [r'(obs - model) / 1$\sigma$ error [Balmer decrement]',
	        r'(obs - model) / 1$\sigma$ error [D$_n$(4000)]',
	        r'(obs - model) / 1$\sigma$ error [H$_{\alpha}$]']
	flags = [np.array([item for sublist in bdec_flag for item in sublist]),
	         dn4000_flag,
	         np.array([item for sublist in ha_flag for item in sublist])]

	#### ALL GALAXIES
	fig, axes = plt.subplots(1, 3, figsize = (18.75,6))
	for ii, ax in enumerate(axes):
		num, b, p = ax.hist(x[ii],nbins,**kwargs)
		save_xlim = ax.get_xlim()
		b = (b[:-1] + b[1:])/2.
		ax.set_ylabel('N')
		ax.set_xlabel(tits[ii])
		fit = gauss_fit(b,num)
		ax.plot(b,fit(b),lw=5, color='red',linestyle='--')
		ax.text(0.98,0.9,r'$\sigma$='+"{:.2f}".format(fit.stddev.value),transform = ax.transAxes,ha='right')
		ax.set_xlim(save_xlim)
	plt.savefig(outbase+'all_errs.png',dpi=dpi)
	plt.close()

	#### NO AGN
	fig, axes = plt.subplots(1, 3, figsize = (18.75,6))
	for ii, ax in enumerate(axes):
		keepers = flags[ii] != 'AGN'
		num, b, p = ax.hist(x[ii][keepers],nbins,**kwargs)
		save_xlim = ax.get_xlim()
		b = (b[:-1] + b[1:])/2.
		ax.set_ylabel('N')
		ax.set_xlabel(tits[ii])
		fit = gauss_fit(b,num)
		ax.plot(b,fit(b),lw=5, color='red',linestyle='--')
		ax.text(0.98,0.9,r'$\sigma$='+"{:.2f}".format(fit.stddev.value),transform = ax.transAxes,ha='right')
		ax.set_xlim(save_xlim)
	plt.savefig(outbase+'no_agn_errs.png',dpi=dpi)
	plt.close()

	#### ONLY STAR-FORMING
	fig, axes = plt.subplots(1, 3, figsize = (18.75,6))
	for ii, ax in enumerate(axes):
		keepers = flags[ii] == 'SF'
		num, b, p = ax.hist(x[ii][keepers],nbins,**kwargs)
		save_xlim = ax.get_xlim()
		b = (b[:-1] + b[1:])/2.
		ax.set_ylabel('N')
		ax.set_xlabel(tits[ii])
		fit = gauss_fit(b,num)
		ax.plot(b,fit(b),lw=5, color='red',linestyle='--')
		ax.text(0.98,0.9,r'$\sigma$='+"{:.2f}".format(fit.stddev.value),transform = ax.transAxes,ha='right')
		ax.set_xlim(save_xlim)
	plt.savefig(outbase+'sf_only_errs.png',dpi=dpi)
	plt.close()

def obs_vs_model_bdec(e_pinfo,hflag,outname1='test.png',outname2='test.png'):
	
	#################
	#### plot observed Balmer decrement versus expected
	#################
	# first is Prospector CLOUDY marg + MAGPHYS versus observations
	# second is Prospector CLOUDY bfit, Prospector calc bfit, Prospector calc marg versus observations

	# S/N
	sn_ha = np.abs(e_pinfo['obs']['f_ha'][:,0] / e_pinfo['obs']['err_ha'])
	sn_hb = np.abs(e_pinfo['obs']['f_hb'][:,0] / e_pinfo['obs']['err_hb'])

	#### for now, aggressive S/N cuts
	# S/N(Ha) > 10, S/N (Hbeta) > 10
	keep_idx = np.squeeze((sn_ha > e_pinfo['obs']['sn_cut']) & \
		                  (sn_hb > e_pinfo['obs']['sn_cut']) & \
		                  (e_pinfo['obs']['eqw_ha'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['eqw_hb'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['f_ha'][:,0] > 0) & \
		                  (e_pinfo['obs']['f_hb'][:,0] > 0))

	##### write down plot variables
	pl_bdec_cloudy_marg = bdec_to_ext(e_pinfo['prosp']['bdec_cloudy_marg'][keep_idx,:])
	pl_bdec_calc_marg = bdec_to_ext(e_pinfo['prosp']['bdec_calc_marg'][keep_idx,:])
	pl_bdec_cloudy_bfit = bdec_to_ext(e_pinfo['prosp']['bdec_cloudy_bfit'][keep_idx])
	pl_bdec_calc_bfit = bdec_to_ext(e_pinfo['prosp']['bdec_calc_bfit'][keep_idx])
	pl_bdec_magphys = bdec_to_ext(e_pinfo['mag']['bdec'][keep_idx])
	pl_bdec_measured = bdec_to_ext(e_pinfo['obs']['bdec'][keep_idx])

	##### BPT classifications, herschel flag
	sfing, composite, agn = return_agn_str(keep_idx)
	keys = [sfing, composite, agn]
	hflag = [hflag[keep_idx],~hflag[keep_idx]]

	#### create plots
	fig1, ax1 = plt.subplots(1,2, figsize = (12.5,6))
	fig2, ax2 = plt.subplots(1,3, figsize = (18.75,6))
	axlims = (-0.1,1.7)
	norm_errs = []
	norm_flag = []

	# loop and put points on plot
	for ii in xrange(len(labels)):
		for kk in xrange(len(hflag)):

			### update colors, define sample
			herschdict[kk].update(color=colors[ii])
			plt_idx = keys[ii] & hflag[kk]

			### errors for this sample
			errs_obs = threed_dutils.asym_errors(pl_bdec_measured[plt_idx], 
		                                         bdec_to_ext(e_pinfo['obs']['bdec'][keep_idx][plt_idx]+e_pinfo['obs']['bdec_err'][keep_idx][plt_idx]),
		                                         bdec_to_ext(e_pinfo['obs']['bdec'][keep_idx][plt_idx]-e_pinfo['obs']['bdec_err'][keep_idx][plt_idx]), log=False)
			errs_cloudy_marg = threed_dutils.asym_errors(pl_bdec_cloudy_marg[plt_idx,0],
				                                   pl_bdec_cloudy_marg[plt_idx,1], 
				                                   pl_bdec_cloudy_marg[plt_idx,2],log=False)
			errs_calc_marg = threed_dutils.asym_errors(pl_bdec_cloudy_marg[plt_idx,0],
				                                   pl_bdec_cloudy_marg[plt_idx,1], 
				                                   pl_bdec_cloudy_marg[plt_idx,2],log=False)

			norm_errs.append(normalize_error(pl_bdec_measured[plt_idx],errs_obs,pl_bdec_cloudy_marg[plt_idx,0],errs_cloudy_marg))
			norm_flag.append([labels[ii]]*np.sum(plt_idx))

			ax1[0].errorbar(pl_bdec_measured[plt_idx], pl_bdec_cloudy_marg[plt_idx,0], xerr=errs_obs, yerr=errs_cloudy_marg,
				           linestyle=' ',**herschdict[kk])
			ax1[1].errorbar(pl_bdec_measured[plt_idx], pl_bdec_magphys[plt_idx], xerr=errs_obs,
				           linestyle=' ',**herschdict[kk])

			ax2[0].errorbar(pl_bdec_measured[plt_idx], pl_bdec_calc_marg[plt_idx,0], xerr=errs_obs, yerr=errs_calc_marg,
				           linestyle=' ',**herschdict[kk])
			ax2[1].errorbar(pl_bdec_measured[plt_idx], pl_bdec_calc_bfit[plt_idx], xerr=errs_obs,
				           linestyle=' ',**herschdict[kk])
			ax2[2].errorbar(pl_bdec_measured[plt_idx], pl_bdec_cloudy_bfit[plt_idx], xerr=errs_obs,
				           linestyle=' ',**herschdict[kk])

	#### PRINT OUTLIERS
	# (galaxy, bdec obs, bdec mod, S/N + EQW (Ha), S/N + EQW (Hb)
	resid = pl_bdec_measured - pl_bdec_cloudy_marg[:,0]
	sort = np.argsort(np.abs(resid))
	agn_string = return_agn_str(keep_idx,string=True)
	for s in sort: print e_pinfo['objnames'][keep_idx][s], agn_string[s], "{:.1f}".format(pl_bdec_measured[s]), "{:.1f}".format(pl_bdec_cloudy_marg[s,0]), "{:.1f}".format(sn_ha[keep_idx][s]), "{:.1f}".format(e_pinfo['obs']['eqw_ha'][keep_idx,0][s]), "{:.1f}".format(sn_hb[keep_idx][s]), "{:.1f}".format(e_pinfo['obs']['eqw_hb'][keep_idx,0][s])

	#### MAIN FIGURE ERRATA
	ax1[0].set_xlabel(r'observed A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax1[0].set_ylabel(r'Prospector A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax1[0] = threed_dutils.equalize_axes(ax1[0], pl_bdec_measured,pl_bdec_cloudy_marg[:,0],axlims=axlims)
	off,scat = threed_dutils.offset_and_scatter(pl_bdec_measured,pl_bdec_cloudy_marg[:,0],biweight=True)
	ax1[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax1[0].transAxes,horizontalalignment='right')
	ax1[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax1[0].transAxes,horizontalalignment='right')

	ax1[1].set_xlabel(r'observed A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax1[1].set_ylabel(r'MAGPHYS A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax1[1] = threed_dutils.equalize_axes(ax1[1], pl_bdec_measured,pl_bdec_magphys,axlims=axlims)
	off,scat = threed_dutils.offset_and_scatter(pl_bdec_measured,pl_bdec_magphys,biweight=True)
	ax1[1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax1[1].transAxes,horizontalalignment='right')
	ax1[1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax1[1].transAxes,horizontalalignment='right')

	#### SECONDARY FIGURE ERRATA
	ax2[0].set_xlabel(r'observed A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax2[0].set_ylabel(r'Prospector calc marginalized A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax2[0] = threed_dutils.equalize_axes(ax2[0], pl_bdec_measured,pl_bdec_calc_marg[:,0],axlims=axlims)
	off,scat = threed_dutils.offset_and_scatter(pl_bdec_measured,pl_bdec_calc_marg[:,0],biweight=True)
	ax2[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax2[0].transAxes,horizontalalignment='right')
	ax2[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax2[0].transAxes,horizontalalignment='right')

	ax2[1].set_xlabel(r'observed A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax2[1].set_ylabel(r'Prospector calc best-fit A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax2[1] = threed_dutils.equalize_axes(ax2[1], pl_bdec_measured,pl_bdec_calc_bfit,axlims=axlims)
	off,scat = threed_dutils.offset_and_scatter(pl_bdec_measured,pl_bdec_calc_bfit,biweight=True)
	ax2[1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax2[1].transAxes,horizontalalignment='right')
	ax2[1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax2[1].transAxes,horizontalalignment='right')

	ax2[2].set_xlabel(r'observed A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax2[2].set_ylabel(r'Prospector CLOUDY best-fit A$_{\mathrm{H}\beta}$ - A$_{\mathrm{H}\alpha}$')
	ax2[2] = threed_dutils.equalize_axes(ax2[2], pl_bdec_measured,pl_bdec_cloudy_bfit,axlims=axlims)
	off,scat = threed_dutils.offset_and_scatter(pl_bdec_measured,pl_bdec_cloudy_bfit,biweight=True)
	ax2[2].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat), transform = ax2[2].transAxes,horizontalalignment='right')
	ax2[2].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off), transform = ax2[2].transAxes,horizontalalignment='right')


	fig1.tight_layout()
	fig1.savefig(outname1,dpi=dpi)

	fig2.tight_layout()
	fig2.savefig(outname2,dpi=dpi)
	plt.close()

	return norm_errs, norm_flag

def obs_vs_prosp_sfr(e_pinfo,hflag,outname='test.png'):

	#### pull out observed Halpha, observed Balmer decrement ####
	# Make same cuts as Balmer decrement calculation
	# S/N
	sn_ha = np.abs(e_pinfo['obs']['f_ha'][:,0] / e_pinfo['obs']['err_ha'])
	sn_hb = np.abs(e_pinfo['obs']['f_hb'][:,0] / e_pinfo['obs']['err_hb'])

	#### for now, aggressive S/N cuts
	# S/N(Ha) > 10, S/N (Hbeta) > 10
	keep_idx = np.squeeze((sn_ha > e_pinfo['obs']['sn_cut']) & \
		                  (sn_hb > e_pinfo['obs']['sn_cut']) & \
		                  (e_pinfo['obs']['eqw_ha'][:,0] > e_pinfo['obs']['eqw_cut']) & \
		                  (e_pinfo['obs']['eqw_hb'][:,0] > e_pinfo['obs']['eqw_cut']))
	
	# halpha
	f_ha = e_pinfo['obs']['f_ha'][keep_idx,0]
	mod_ha = e_pinfo['prosp']['cloudy_ha'][keep_idx,0]

	# Balmer decrements
	bdec_obs = e_pinfo['obs']['bdec'][keep_idx]
	bdec_mod = e_pinfo['prosp']['bdec_cloudy_marg'][keep_idx]

	#### AGN+Herschel identifiers ######
	sfing, composite, agn = return_agn_str(keep_idx)
	keys = [sfing, composite, agn]
	hflag = [hflag[keep_idx],~hflag[keep_idx]]


	#### turn Balmer decrement into tau(lambda = 6563) #####
	# we'll do this by adjusting dust1 ONLY
	# try adjusting by dust2 ONLY later, see if results change
	# start by defining wavelengths and pulling out galaxy parameters
	ha_lam = 6562.801
	hb_lam = 4861.363
	d1 = e_pinfo['prosp']['d1'][keep_idx,0]
	d2 = e_pinfo['prosp']['d2'][keep_idx,0]
	didx = e_pinfo['prosp']['didx'][keep_idx,0]

	ha_ext_obs = np.zeros(len(d1))
	ha_ext_mod = np.zeros(len(d1))
	for ii in xrange(len(d1)):
		# create dust1 test array
		dust_test = np.linspace(0.0,4.0,2000)
		balm_dec_test = 2.86*threed_dutils.charlot_and_fall_extinction(ha_lam,dust_test,d2[ii],-1.0,didx[ii],kriek=True) / \
		                     threed_dutils.charlot_and_fall_extinction(hb_lam,dust_test,d2[ii],-1.0,didx[ii],kriek=True)

		# pull out dust1 that best matches observed Balmer decrement
		# note that this will violate my model priors on dust1/dust2 if it wants to
		d1_new = dust_test[(np.abs(bdec_obs[ii] - balm_dec_test)).argmin()]

		# calculate extinction at Halpha
		ha_ext_obs[ii] = threed_dutils.charlot_and_fall_extinction(ha_lam,d1_new,d2[ii],-1.0,didx[ii],kriek=True)
		ha_ext_mod[ii] = threed_dutils.charlot_and_fall_extinction(ha_lam,d1[ii],d2[ii],-1.0,didx[ii],kriek=True)


	#### correct observed Halpha into intrinsic Halpha, and into CGS
	f_ha_corr = f_ha / ha_ext_obs * constants.L_sun.cgs.value

	#### compute observed SFR, model SFR
	obs_sfr = f_ha_corr / (1.7*1.26e41)
	mod_sfr = e_pinfo['prosp']['sfr_10'][keep_idx,0]

	#### compute balmer decrement residuals
	# obs - model
	bdec_resid = e_pinfo['obs']['bdec'][keep_idx] - e_pinfo['prosp']['bdec_cloudy_marg'][keep_idx,0]

	#### plot
	fig, ax = plt.subplots(1,3, figsize = (18.75,6))

	# loop and put points on plot
	for ii in xrange(len(labels)):
		for kk in xrange(len(hflag)):

			### update colors, define sample
			herschdict[kk].update(color=colors[ii])
			plt_idx = keys[ii] & hflag[kk]

			ax[0].errorbar(bdec_resid[plt_idx], obs_sfr[plt_idx]/mod_sfr[plt_idx],
				           linestyle=' ',**herschdict[kk])
			ax[1].errorbar(ha_ext_mod[plt_idx]/ha_ext_obs[plt_idx], obs_sfr[plt_idx]/mod_sfr[plt_idx],
				           linestyle=' ',**herschdict[kk])
			ax[2].errorbar(ha_ext_mod[plt_idx]/ha_ext_obs[plt_idx], f_ha[plt_idx]/mod_ha[plt_idx],
				           linestyle=' ',**herschdict[kk])

	ax[0].set_xlabel(r'(obs-model) [Balmer decrement]')
	ax[0].set_ylabel(r'SFR$_{\mathrm{obs}}$(H$\alpha$)/SFR$_{\mathrm{model}}$(10 Myr)')
	ax[0].set_ylim(0.0,4.0)

	ax[1].errorbar([0.0,4.0],[0.0,4.0],linestyle='--',alpha=0.5,color='0.5')
	ax[1].set_xlabel(r'$e^{-\tau_{mod}(\mathrm{H}\alpha)} / e^{-\tau_{obs}(\mathrm{H}\alpha)}$')
	ax[1].set_ylabel(r'SFR$_{\mathrm{obs}}$(H$\alpha$)/SFR$_{\mathrm{model}}$(10 Myr)')
	ax[1].set_ylim(0.0,4.0)
	ax[1].set_xlim(0.0,4.0)

	ax[2].errorbar([0.0,3.3],[0.0,3.3],linestyle='--',alpha=0.5,color='0.5')
	ax[2].set_xlabel(r'$e^{-\tau_{mod}(\mathrm{H}\alpha)} / e^{-\tau_{obs}(\mathrm{H}\alpha)}$')
	ax[2].set_ylabel(r'H$_{\alpha}$(obs)/H$_{\alpha}$(mod)')
	ax[2].set_ylim(0.0,3.3)
	ax[2].set_xlim(0.0,3.3)

	plt.savefig(outname, dpi=dpi)
	plt.close()

def return_agn_str(idx, string=False):

	from astropy.io import fits
	hdulist = fits.open(os.getenv('APPS')+'/threedhst_bsfh/data/brownseds_data/photometry/table1.fits')
	agn_str = hdulist[1].data['Class']
	hdulist.close()

	agn_str = agn_str[idx]
	sfing = (agn_str == 'SF') | (agn_str == '---')
	composite = (agn_str == 'SF/AGN')
	agn = agn_str == 'AGN'

	if string:
		return agn_str
	else:
		return sfing, composite, agn

def residual_plots(alldata,obs_info, bdec_info):
	# bdec_info: bdec_magphys, bdec_prospector, bdec_measured, keep_idx, dust1, dust2, dust2_index
	# obs_info: model_ha, f_ha, f_ha_errup, f_ha_errdown

	fldr = '/Users/joel/code/python/threedhst_bsfh/plots/brownseds/magphys/emlines_comp/residuals/'
	idx = bdec_info['keep_idx']

	sfr_100 = np.log10(np.clip([x['bfit']['sfr_100'] for x in alldata],1e-4,np.inf))[idx]

	#### bdec resid versus ha resid
	bdec_resid = bdec_info['bdec_prospector'][idx] - bdec_info['bdec_measured'][idx]
	ha_resid = np.log10(obs_info['f_ha'][idx]) - np.log10(obs_info['model_ha'][idx,0])

	fig, ax = plt.subplots(1,1, figsize = (8,8))

	ax.errorbar(ha_resid, bdec_resid, fmt='o',alpha=0.6,linestyle=' ')
	ax.set_xlabel(r'log(Prospector/obs) [H$_{\alpha}$]')
	ax.set_ylabel(r'Prospector - obs [Balmer decrement]')
	
	plt.savefig(fldr+'bdec_resid_versus_ha_resid.png', dpi=dpi)

	sfing, composite, agn = return_agn_str(idx)
	keys = [sfing, composite, agn]

	#### dust1 / dust2
	fig, ax = plt.subplots(1,2, figsize = (18,8))
	
	xplot = bdec_info['dust1'][idx]/bdec_info['dust2'][idx]
	yplot = bdec_resid
	for ii in xrange(len(labels)):
		ax[0].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii])
	ax[0].axhline(0, linestyle=':', color='grey')
	ax[0].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))
	ax[0].set_xlabel(r'dust1/dust2')
	ax[0].set_ylabel(r'Prospector - obs [Balmer decrement]')

	yplot = ha_resid
	for ii in xrange(len(labels)):
		ax[1].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii])
	ax[1].axhline(0, linestyle=':', color='grey')
	ax[1].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))	
	ax[1].set_xlabel(r'dust1/dust2')
	ax[1].set_ylabel(r'log(Prospector/obs) [H$_{\alpha}$]')
	ax[1].legend()
	
	plt.savefig(fldr+'dust1_dust2_residuals.png', dpi=dpi)

	#### dust2_index
	fig, ax = plt.subplots(1,2, figsize = (18,8))

	xplot = bdec_info['dust2_index'][idx]
	yplot = bdec_resid
	for ii in xrange(len(labels)):
		ax[0].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii])
	ax[0].set_xlabel(r'dust2_index')
	ax[0].set_ylabel(r'Prospector - obs [Balmer decrement]')
	ax[0].axhline(0, linestyle=':', color='grey')
	ax[0].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))

	yplot = ha_resid
	for ii in xrange(len(labels)):
		ax[1].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii])
	ax[1].set_xlabel(r'dust2_index')
	ax[1].set_ylabel(r'log(Prospector/obs) [H$_{\alpha}$]')
	ax[1].legend(loc=3)
	ax[1].axhline(0, linestyle=':', color='grey')
	ax[1].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))
	
	plt.savefig(fldr+'dust_index_residuals.png', dpi=dpi)

	#### total attenuation at 5500 angstroms
	fig, ax = plt.subplots(1,2, figsize = (18,8))

	xplot = bdec_info['dust1'][idx] + bdec_info['dust2'][idx]
	yplot = bdec_resid
	for ii in xrange(len(labels)):
		ax[0].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii])
	ax[0].set_xlabel(r'total attenuation [5500 $\AA$]')
	ax[0].set_ylabel(r'Prospector - obs [Balmer decrement]')
	ax[0].legend(loc=4)
	ax[0].axhline(0, linestyle=':', color='grey')
	ax[0].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))

	yplot = ha_resid
	for ii in xrange(len(labels)):
		ax[1].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii],)
	ax[1].set_xlabel(r'total attenuation [5500 $\AA$]')
	ax[1].set_ylabel(r'log(Prospector/obs) [H$_{\alpha}$]')
	ax[1].axhline(0, linestyle=':', color='grey')
	ax[1].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))
	
	plt.savefig(fldr+'total_attenuation_residuals.png', dpi=dpi)

	#### sfr_100 residuals
	fig, ax = plt.subplots(1,2, figsize = (18,8))

	xplot = sfr_100
	yplot = bdec_resid
	for ii in xrange(len(labels)):
		ax[0].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii])
	ax[0].set_xlabel(r'SFR$_{100 \mathrm{ Myr}}$ [M$_{\odot}$/yr]')
	ax[0].set_ylabel(r'Prospector - obs [Balmer decrement]')
	ax[0].legend(loc=3)
	ax[0].axhline(0, linestyle=':', color='grey')
	ax[0].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))

	yplot = ha_resid
	for ii in xrange(len(labels)):
		ax[1].errorbar(xplot[keys[ii]], yplot[keys[ii]], fmt='o',alpha=0.6,linestyle=' ',color=colors[ii],label=labels[ii],)
	ax[1].set_xlabel(r'SFR$_{100 \mathrm{ Myr}}$ [M$_{\odot}$/yr]')
	ax[1].set_ylabel(r'log(Prospector/obs) [H$_{\alpha}$]')
	ax[1].axhline(0, linestyle=':', color='grey')
	ax[1].set_ylim(-np.max(np.abs(yplot)),np.max(np.abs(yplot)))
	
	plt.savefig(fldr+'sfr_100_residuals.png', dpi=dpi)

	#### dust2_index vs dust1/dust2
	fig, ax = plt.subplots(1,1, figsize = (8,8))

	ax.errorbar(bdec_info['dust2_index'], bdec_info['dust1']/bdec_info['dust2'], fmt='o',alpha=0.6,linestyle=' ')
	ax.set_xlabel(r'dust2_index')
	ax.set_ylabel(r'dust1/dust2')

	plt.savefig(fldr+'idx_versus_ratio.png', dpi=dpi)



def plot_emline_comp(alldata,outfolder,hflag):
	'''
	emission line luminosity comparisons:
		(1) Observed luminosity, Prospector vs MAGPHYS continuum subtraction
		(2) Moustakas+10 comparisons
		(3) model Balmer decrement (from dust) versus observed Balmer decrement
		(4) model Halpha (from Kennicutt + dust) versus observed Halpha
	'''

	##### Pull relevant information out of alldata
	emline_names = alldata[0]['residuals']['emlines']['em_name']

	##### load moustakas+10 line flux information
	objnames = np.array([f['objname'] for f in alldata])
	dat = threed_dutils.load_moustakas_data(objnames = list(objnames))
	
	##### plots, one by one
	# observed line fluxes, with MAGPHYS / Prospector continuum
	compare_model_flux(alldata,emline_names,outname = outfolder+'continuum_model_flux_comparison.png')

	# observed line fluxes versus Moustakas+10
	compare_moustakas_fluxes(alldata,dat,emline_names,objnames,
							 outname=outfolder+'moustakas_flux_comparison.png',
							 outdec=outfolder+'moustakas_bdec_comparison.png')
	
	##### format emission line data for plotting
	e_pinfo = fmt_emline_info(alldata)

	# model versus observations, Balmer decrement
	bdec_errs,bdec_flag = obs_vs_model_bdec(e_pinfo, hflag, outname1=outfolder+'bdec_comparison.png',outname2=outfolder+'prospector_bdec_comparison.png')

	# model versus observations, Hdelta
	dn4000_errs,dn4000_flag = obs_vs_model_hdelta_dn(e_pinfo, hflag, outname=outfolder+'hdelta_dn_comp.png')

	# balmer decrement + hdelta?
	bdec_correction(e_pinfo,hflag,outname=outfolder+'bdec_corrected.png')

	# model versus observations, Halpha + Hbeta
	ha_errs,ha_flag = obs_vs_prosp_balmlines(e_pinfo,hflag,outname=outfolder+'balmer_line_comparison.png')

	# model SFR versus observed SFR(Ha) corrected for dust attenuation
	obs_vs_prosp_sfr(e_pinfo,hflag,outname=outfolder+'obs_sfr_comp.png')

	# error plots
	onesig_error_plot(bdec_errs,bdec_flag,dn4000_errs,dn4000_flag,ha_errs,ha_flag,outfolder)

	# model versus observations for Kennicutt Halphas
	obs_vs_kennicutt_ha(e_pinfo,hflag,
		                outname=outfolder+'empirical_halpha_comparison.png',
		                outname_cloudy=outfolder+'empirical_halpha_versus_cloudy.png',
		                outname_ha_inpt=outfolder+'kennicutt_ha_input.png',
		                outname_sfr_margcomp=outfolder+'sfr_margcomp.png')

	# model versus observations for BPT diagram
	bpt_diagram(e_pinfo,hflag,outname=outfolder+'bpt.png')

	residual_plots(alldata,obs_info, bdec_info)

def plot_relationships(alldata,outfolder):

	'''
	mass-metallicity
	mass-SFR
	etc
	'''

	##### set up plots
	fig = plt.figure(figsize=(13,6.0))
	gs1 = mpl.gridspec.GridSpec(1, 2)
	msfr = plt.Subplot(fig, gs1[0])
	mz = plt.Subplot(fig, gs1[1])

	fig.add_subplot(msfr)
	fig.add_subplot(mz)

	alpha = 0.6
	ms = 6.0

	##### find prospector indexes
	parnames = alldata[0]['pquantiles']['parnames']
	idx_mass = parnames == 'mass'
	idx_met = parnames == 'logzsol'

	eparnames = alldata[0]['pextras']['parnames']
	idx_sfr = eparnames == 'sfr_100'

	##### find magphys indexes
	idx_mmet = alldata[0]['model']['full_parnames'] == 'Z/Zo'

	##### extract mass, SFR, metallicity
	magmass, promass, magsfr, prosfr, promet = [np.empty(shape=(0,3)) for x in xrange(5)]
	magmet = np.empty(0)
	for data in alldata:
		if data:
			
			# mass
			tmp = np.array([data['pquantiles']['q16'][idx_mass][0],
				            data['pquantiles']['q50'][idx_mass][0],
				            data['pquantiles']['q84'][idx_mass][0]])
			promass = np.concatenate((promass,np.atleast_2d(np.log10(tmp))),axis=0)
			magmass = np.concatenate((magmass,np.atleast_2d(data['magphys']['percentiles']['M*'][1:4])))

			# SFR
			tmp = np.array([data['pextras']['q16'][idx_sfr][0],
				            data['pextras']['q50'][idx_sfr][0],
				            data['pextras']['q84'][idx_sfr][0]])
			tmp = np.log10(np.clip(tmp,minsfr,np.inf))
			prosfr = np.concatenate((prosfr,np.atleast_2d(tmp)))
			magsfr = np.concatenate((magsfr,np.atleast_2d(data['magphys']['percentiles']['SFR'][1:4])))

			# metallicity
			tmp = np.array([data['pquantiles']['q16'][idx_met][0],
				            data['pquantiles']['q50'][idx_met][0],
				            data['pquantiles']['q84'][idx_met][0]])
			promet = np.concatenate((promet,np.atleast_2d(tmp)))
			magmet = np.concatenate((magmet,np.log10(np.atleast_1d(data['model']['full_parameters'][idx_mmet][0]))))

	##### Errors on Prospector+Magphys quantities
	# mass errors
	proerrs_mass = [promass[:,1]-promass[:,0],
	                promass[:,2]-promass[:,1]]
	magerrs_mass = [magmass[:,1]-magmass[:,0],
	                magmass[:,2]-magmass[:,1]]

	# SFR errors
	proerrs_sfr = [prosfr[:,1]-prosfr[:,0],
	               prosfr[:,2]-prosfr[:,1]]
	magerrs_sfr = [magsfr[:,1]-magsfr[:,0],
	               magsfr[:,2]-magsfr[:,1]]

	# metallicity errors
	proerrs_met = [promet[:,1]-promet[:,0],
	               promet[:,2]-promet[:,1]]


	##### STAR-FORMING SEQUENCE #####
	msfr.errorbar(promass[:,1],prosfr[:,1],
		          fmt='o', alpha=alpha,
		          color=prosp_color,
		          label='Prospectr',
			      xerr=proerrs_mass, yerr=proerrs_sfr,
			      ms=ms)
	msfr.errorbar(magmass[:,1],magsfr[:,1],
		          fmt='o', alpha=alpha,
		          color=magphys_color,
		          label='MAGPHYS',
			      xerr=magerrs_mass, yerr=magerrs_sfr,
			      ms=ms)

	# Chang et al. 2015
	# + 0.39 dex, -0.64 dex
	chang_color = 'orange'
	chang_mass = np.linspace(7,12,40)
	chang_sfr = 0.8 * np.log10(10**chang_mass/1e10) - 0.23
	chang_scatlow = 0.64
	chang_scathigh = 0.39

	msfr.plot(chang_mass, chang_sfr,
		          color=chang_color,
		          lw=2.5,
		          label='Chang+15',
		          zorder=-1)

	msfr.fill_between(chang_mass, chang_sfr-chang_scatlow, chang_sfr+chang_scathigh, 
		                  color=chang_color,
		                  alpha=0.3)


	#### Salim+07
	ssfr_salim = -0.35*(chang_mass-10)-9.83
	salim_sfr = np.log10(10**ssfr_salim*10**chang_mass)

	msfr.plot(chang_mass, salim_sfr,
		          color='green',
		          lw=2.5,
		          label='Salim+07',
		          zorder=-1)

	# legend
	msfr.legend(loc=2, prop={'size':12},
			    frameon=False)

	msfr.set_xlabel(r'log(M/M$_{\odot}$)')
	msfr.set_ylabel(r'log(SFR/M$_{\odot}$/yr)')

	##### MASS-METALLICITY #####
	mz.errorbar(promass[:,1],promet[:,1],
		          fmt='o', alpha=alpha,
		          color=prosp_color,
			      xerr=proerrs_mass, yerr=proerrs_met,
			      ms=ms)
	mz.errorbar(magmass[:,1],magmet,
		          fmt='o', alpha=alpha,
		          color=magphys_color,
			      xerr=magerrs_mass,
			      ms=ms)	

	# Gallazzi+05
	# shape: mass q50 q16 q84
	# IMF is probably Kroupa, though not stated in paper
	# must add correction...
	massmet = np.loadtxt(os.getenv('APPS')+'/threedhst_bsfh/data/gallazzi_05_massmet.txt')

	mz.plot(massmet[:,0], massmet[:,1],
		          color='green',
		          lw=2.5,
		          label='Gallazzi+05',
		          zorder=-1)

	mz.fill_between(massmet[:,0], massmet[:,2], massmet[:,3], 
		                  color='green',
		                  alpha=0.3)


	# legend
	mz.legend(loc=4, prop={'size':12},
			    frameon=False)

	mz.set_ylim(-2.0,0.3)
	mz.set_xlim(9,11.8)
	mz.set_xlabel(r'log(M/M$_{\odot}$)')
	mz.set_ylabel(r'log(Z/Z$_{\odot}$/yr)')

	plt.savefig(outfolder+'relationships.png',dpi=dpi)
	plt.close

def prospector_comparison(alldata,outfolder,hflag):

	'''
	For Prospector:
	dust_index versus total attenuation
	dust_index versus SFR
	dust1 versus dust2, everything below -0.45 dust index highlighted
	'''
	
	#### find prospector indexes
	parnames = alldata[0]['pquantiles']['parnames']
	idx_mass = parnames == 'mass'
	didx_idx = parnames == 'dust_index'
	d1_idx = parnames == 'dust1'
	d2_idx = parnames == 'dust2'

	#### agn flags
	sfing, composite, agn = return_agn_str(np.ones_like(hflag,dtype=bool))
	agn_flags = [sfing,composite,agn]

	#### best-fits
	d1 = np.array([x['bfit']['maxprob_params'][d1_idx][0] for x in alldata])
	d2 = np.array([x['bfit']['maxprob_params'][d2_idx][0] for x in alldata])
	didx = np.array([x['bfit']['maxprob_params'][didx_idx][0] for x in alldata])
	sfr_100 = np.log10(np.clip([x['bfit']['sfr_100'] for x in alldata],1e-4,np.inf))
	sfr_100_marginalized = np.log10(np.clip([x['pextras']['q50'][x['pextras']['parnames'] == 'sfr_100'] for x in alldata],1e-4,np.inf))
	sfr_10_marginalized = np.log10(np.clip([x['pextras']['q50'][x['pextras']['parnames'] == 'sfr_10'] for x in alldata],1e-4,np.inf))
	sfr_10 = np.log10(np.clip([x['bfit']['sfr_10'] for x in alldata],1e-4,np.inf))

	#### total attenuation
	dusttot = np.zeros_like(d1)
	for ii in xrange(len(dusttot)): dusttot[ii] = -np.log10(threed_dutils.charlot_and_fall_extinction(5500.,d1[ii],d2[ii],-1.0,didx[ii], kriek=True))

	#### plotting series of comparisons
	fig, ax = plt.subplots(2,3, figsize = (22,12))

	ax[0,0].errorbar(didx,dusttot, fmt='o',alpha=0.6,linestyle=' ',color='0.4')
	ax[0,0].set_ylabel(r'total attenuation [5500 $\AA$]')
	ax[0,0].set_xlabel(r'dust_index')
	ax[0,0].axis((didx.min()-0.1,didx.max()+0.1,dusttot.min()-0.1,dusttot.max()+0.1))

	for flag,col in zip(agn_flags,colors): ax[0,1].errorbar(didx[flag],sfr_100[flag], fmt='o',alpha=0.6,linestyle=' ',color=col)
	ax[0,1].set_xlabel(r'dust_index')
	ax[0,1].set_ylabel(r'SFR$_{100 \mathrm{ Myr}}$ [M$_{\odot}$/yr]')
	ax[0,1].axis((didx.min()-0.1,didx.max()+0.1,sfr_100.min()-0.1,sfr_100.max()+0.1))
	for ii in xrange(len(labels)): ax[0,1].text(0.04,0.92-0.08*ii,labels[ii],color=colors[ii],transform = ax[0,1].transAxes,weight='bold')

	l_idx = didx > -0.45
	h_idx = didx < -0.45
	ax[0,2].errorbar(d1[h_idx],d2[h_idx], fmt='o',alpha=0.6,linestyle=' ',color='0.4')
	ax[0,2].errorbar(d1[l_idx],d2[l_idx], fmt='o',alpha=0.6,linestyle=' ',color='blue')
	ax[0,2].set_xlabel(r'dust1')
	ax[0,2].set_ylabel(r'dust2')
	ax[0,2].axis((d1.min()-0.1,d1.max()+0.1,d2.min()-0.1,d2.max()+0.1))
	ax[1,0].text(0.97,0.05,'dust_index > -0.45',color='blue',transform = ax[0,2].transAxes,weight='bold',ha='right')

	l_idx = didx > -0.45
	h_idx = didx < -0.45
	ax[1,0].errorbar(didx[~hflag],d1[~hflag]/d2[~hflag], fmt='o',alpha=0.6,linestyle=' ', label='no herschel',color='0.4')
	ax[1,0].errorbar(didx[hflag],d1[hflag]/d2[hflag], fmt='o',alpha=0.6,linestyle=' ', label='has herschel',color='red')
	ax[1,0].set_xlabel(r'dust_index')
	ax[1,0].set_ylabel(r'dust1/dust2')
	ax[1,0].axis((didx.min()-0.1,didx.max()+0.1,(d1/d2).min()-0.1,(d1/d2).max()+0.1))
	ax[1,0].text(0.05,0.92,'Herschel-detected',color='red',transform = ax[1,0].transAxes,weight='bold')

	ax[1,1].errorbar(sfr_100_marginalized, sfr_10_marginalized, fmt='o',alpha=0.6,linestyle=' ',color=obs_color)
	ax[1,1].set_xlabel(r'log(SFR [100 Myr]) [marginalized]')
	ax[1,1].set_ylabel(r'log(SFR [10 Myr]) [marginalized]')
	ax[1,1] = threed_dutils.equalize_axes(ax[1,1], sfr_100_marginalized,sfr_10_marginalized)
	off,scat = threed_dutils.offset_and_scatter(sfr_100_marginalized,sfr_10_marginalized,biweight=True)
	ax[1,1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat),
			  transform = ax[1,1].transAxes,horizontalalignment='right')
	ax[1,1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off),
			      transform = ax[1,1].transAxes,horizontalalignment='right')

	ax[1,2].errorbar(sfr_10, sfr_10_marginalized, fmt='o',alpha=0.6,linestyle=' ',color=obs_color)
	ax[1,2].set_xlabel(r'log(SFR [10 Myr]) [best-fit]')
	ax[1,2].set_ylabel(r'log(SFR [10 Myr]) [marginalized]')
	ax[1,2] = threed_dutils.equalize_axes(ax[1,2], sfr_10,sfr_10_marginalized)
	off,scat = threed_dutils.offset_and_scatter(sfr_10,sfr_10_marginalized,biweight=True)
	ax[1,2].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat),
			  transform = ax[1,2].transAxes,horizontalalignment='right')
	ax[1,2].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off),
			      transform = ax[1,2].transAxes,horizontalalignment='right')

	plt.savefig(outfolder+'bestfit_param_comparison.png', dpi=dpi)
	plt.close()

def plot_comparison(alldata,outfolder):

	'''
	mass vs mass
	sfr vs sfr
	etc
	'''

	##### set up plots
	fig = plt.figure(figsize=(18,12))
	gs1 = mpl.gridspec.GridSpec(2, 3)
	mass = plt.Subplot(fig, gs1[0])
	sfr = plt.Subplot(fig, gs1[1])
	met = plt.Subplot(fig, gs1[2])
	ext_diff = plt.Subplot(fig,gs1[3])
	balm = plt.Subplot(fig,gs1[4])
	ext_tot = plt.Subplot(fig,gs1[5])

	fig.add_subplot(mass)
	fig.add_subplot(sfr)
	fig.add_subplot(met)
	fig.add_subplot(balm)
	fig.add_subplot(ext_tot)
	fig.add_subplot(ext_diff)


	alpha = 0.6
	fmt = 'o'

	##### find prospector indexes
	parnames = alldata[0]['pquantiles']['parnames']
	idx_mass = parnames == 'mass'
	idx_met = parnames == 'logzsol'
	dinx_idx = parnames == 'dust_index'
	dust1_idx = parnames == 'dust1'
	dust2_idx = parnames == 'dust2'

	eparnames = alldata[0]['pextras']['parnames']
	idx_sfr = eparnames == 'sfr_100'

	##### find magphys indexes
	mparnames = alldata[0]['model']['parnames']
	mfparnames = alldata[0]['model']['full_parnames']
	idx_mmet = mfparnames == 'Z/Zo'
	mu_idx = mparnames == 'mu'
	tauv_idx = mparnames == 'tauv'


	##### mass
	magmass, promass = np.empty(shape=(0,3)), np.empty(shape=(0,3))
	for data in alldata:
		if data:
			tmp = np.array([data['pquantiles']['q16'][idx_mass][0],
				            data['pquantiles']['q50'][idx_mass][0],
				            data['pquantiles']['q84'][idx_mass][0]])
			promass = np.concatenate((promass,np.atleast_2d(np.log10(tmp))),axis=0)
			magmass = np.concatenate((magmass,np.atleast_2d(data['magphys']['percentiles']['M*'][1:4])))

	proerrs = [promass[:,1]-promass[:,0],
	           promass[:,2]-promass[:,1]]
	magerrs = [magmass[:,1]-magmass[:,0],
	           magmass[:,2]-magmass[:,1]]
	mass.errorbar(promass[:,1],magmass[:,1],
		          fmt=fmt, alpha=alpha,
			      xerr=proerrs, yerr=magerrs, color='0.4')

	# labels
	mass.set_xlabel(r'log(M$_*$) [Prospector]',labelpad=13)
	mass.set_ylabel(r'log(M$_*$) [MAGPHYS]')
	mass = threed_dutils.equalize_axes(mass,promass[:,1],magmass[:,1])

	# text
	off,scat = threed_dutils.offset_and_scatter(promass[:,1],magmass[:,1],biweight=True)
	mass.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = mass.transAxes,horizontalalignment='right')
	mass.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = mass.transAxes,horizontalalignment='right')

	##### SFR
	magsfr, prosfr = np.empty(shape=(0,3)), np.empty(shape=(0,3))
	for data in alldata:
		if data:
			tmp = np.array([data['pextras']['q16'][idx_sfr][0],
				            data['pextras']['q50'][idx_sfr][0],
				            data['pextras']['q84'][idx_sfr][0]])
			tmp = np.log10(np.clip(tmp,minsfr,np.inf))
			prosfr = np.concatenate((prosfr,np.atleast_2d(tmp)))
			magsfr = np.concatenate((magsfr,np.atleast_2d(data['magphys']['percentiles']['SFR'][1:4])))

	proerrs = [prosfr[:,1]-prosfr[:,0],
	           prosfr[:,2]-prosfr[:,1]]
	magerrs = [magsfr[:,1]-magsfr[:,0],
	           magsfr[:,2]-magsfr[:,1]]
	sfr.errorbar(prosfr[:,1],magsfr[:,1],
		          fmt=fmt, alpha=alpha,
			      xerr=proerrs, yerr=magerrs, color='0.4')

	# labels
	sfr.set_xlabel(r'log(SFR) [Prospector]')
	sfr.set_ylabel(r'log(SFR) [MAGPHYS]')
	sfr = threed_dutils.equalize_axes(sfr,prosfr[:,1],magsfr[:,1])

	# text
	off,scat = threed_dutils.offset_and_scatter(prosfr[:,1],magsfr[:,1],biweight=True)
	sfr.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = sfr.transAxes,horizontalalignment='right')
	sfr.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = sfr.transAxes,horizontalalignment='right')

	##### metallicity
	# check that we're using the same solar abundance
	magmet, promet = np.empty(0),np.empty(shape=(0,3))
	for data in alldata:
		if data:
			tmp = np.array([data['pquantiles']['q16'][idx_met][0],
				            data['pquantiles']['q50'][idx_met][0],
				            data['pquantiles']['q84'][idx_met][0]])
			promet = np.concatenate((promet,np.atleast_2d(tmp)))
			magmet = np.concatenate((magmet,np.log10(np.atleast_1d(data['model']['full_parameters'][idx_mmet][0]))))

	proerrs = [promet[:,1]-promet[:,0],
	           promet[:,2]-promet[:,1]]
	met.errorbar(promet[:,1],magmet,
		          fmt=fmt, alpha=alpha,
			      xerr=proerrs, color='0.4')

	# labels
	met.set_xlabel(r'log(Z/Z$_{\odot}$) [Prospector]',labelpad=13)
	met.set_ylabel(r'log(Z/Z$_{\odot}$) [best-fit MAGPHYS]')
	met = threed_dutils.equalize_axes(met,promet[:,1],magmet)

	# text
	off,scat = threed_dutils.offset_and_scatter(promet[:,1],magmet,biweight=True)
	met.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = met.transAxes,horizontalalignment='right')
	met.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = met.transAxes,horizontalalignment='right')
	

	#### Balmer decrement
	bdec_magphys, bdec_prospector = [],[]
	for ii,dat in enumerate(alldata):
		tau1 = dat['bfit']['maxprob_params'][dust1_idx][0]
		tau2 = dat['bfit']['maxprob_params'][dust2_idx][0]
		dindex = dat['bfit']['maxprob_params'][dinx_idx][0]
		bdec = threed_dutils.calc_balmer_dec(tau1, tau2, -1.0, dindex,kriek=True)
		bdec_prospector.append(bdec)
		
		tau1 = (1-dat['model']['parameters'][mu_idx][0])*dat['model']['parameters'][tauv_idx][0]
		tau2 = dat['model']['parameters'][mu_idx][0]*dat['model']['parameters'][tauv_idx][0]
		bdec = threed_dutils.calc_balmer_dec(tau1, tau2, -1.3, -0.7)
		bdec_magphys.append(np.squeeze(bdec))
	
	bdec_magphys = np.array(bdec_magphys)
	bdec_prospector = np.array(bdec_prospector)

	balm.errorbar(bdec_prospector,bdec_magphys,
		          fmt=fmt, alpha=alpha, color='0.4')

	# labels
	balm.set_xlabel(r'Prospector H$_{\alpha}$/H$_{\beta}$',labelpad=13)
	balm.set_ylabel(r'MAGPHYS H$_{\alpha}$/H$_{\beta}$')
	balm = threed_dutils.equalize_axes(balm,bdec_prospector,bdec_magphys)

	# text
	off,scat = threed_dutils.offset_and_scatter(bdec_prospector,bdec_magphys,biweight=True)
	balm.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = balm.transAxes,horizontalalignment='right')
	balm.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = balm.transAxes,horizontalalignment='right')

	#### Extinction
	tautot_magphys,tautot_prospector,taudiff_magphys,taudiff_prospector = [],[], [], []
	for ii,dat in enumerate(alldata):
		tau1 = dat['bfit']['maxprob_params'][dust1_idx][0]
		tau2 = dat['bfit']['maxprob_params'][dust2_idx][0]
		dindex = dat['bfit']['maxprob_params'][dinx_idx][0]

		dust2 = threed_dutils.charlot_and_fall_extinction(5500.,tau1,tau2,-1.0,dindex, kriek=True, nobc=True)
		dusttot = threed_dutils.charlot_and_fall_extinction(5500.,tau1,tau2,-1.0,dindex, kriek=True)
		taudiff_prospector.append(-np.log(dust2))
		tautot_prospector.append(-np.log10(dusttot))
		
		tau1 = (1-dat['model']['parameters'][mu_idx][0])*dat['model']['parameters'][tauv_idx][0]
		tau2 = dat['model']['parameters'][mu_idx][0]*dat['model']['parameters'][tauv_idx][0]
		taudiff_magphys.append(tau2)
		tautot_magphys.append(tau1+tau2)
	
	taudiff_prospector = np.array(taudiff_prospector)
	taudiff_magphys = np.array(taudiff_magphys)
	tautot_magphys = np.array(tautot_magphys)
	tautot_prospector = np.array(tautot_prospector)

	ext_tot.errorbar(tautot_prospector,tautot_magphys,
		          fmt=fmt, alpha=alpha, color='0.4')

	# labels
	ext_tot.set_xlabel(r'Prospector total $\tau_{5500}$',labelpad=13)
	ext_tot.set_ylabel(r'MAGPHYS total $\tau_{5500}$')
	ext_tot = threed_dutils.equalize_axes(ext_tot,tautot_prospector,tautot_magphys)

	# text
	off,scat = threed_dutils.offset_and_scatter(tautot_prospector,tautot_magphys,biweight=True)
	ext_tot.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = ext_tot.transAxes,horizontalalignment='right')
	ext_tot.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = ext_tot.transAxes,horizontalalignment='right',)

	ext_diff.errorbar(taudiff_prospector,taudiff_magphys,
		          fmt=fmt, alpha=alpha, color='0.4')

	# labels
	ext_diff.set_xlabel(r'Prospector diffuse $\tau_{5500}$',labelpad=13)
	ext_diff.set_ylabel(r'MAGPHYS diffuse $\tau_{5500}$')
	ext_diff = threed_dutils.equalize_axes(ext_diff,taudiff_prospector,taudiff_magphys)

	# text
	off,scat = threed_dutils.offset_and_scatter(taudiff_prospector,taudiff_magphys,biweight=True)
	ext_diff.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = ext_diff.transAxes,horizontalalignment='right')
	ext_diff.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = ext_diff.transAxes,horizontalalignment='right')


	plt.tight_layout()
	plt.savefig(outfolder+'basic_comparison.png',dpi=dpi)
	plt.close()

def time_res_incr_comp(alldata_2,alldata_7):

	'''
	compare time_res_incr = 2, 7. input is 7. load 2 separately.
	'''

	mass_2 = np.array([f['bfit']['maxprob_params'][0] for f in alldata_2])
	mass_7 = np.array([f['bfit']['maxprob_params'][0] for f in alldata_7])

	sfr_2 = np.log10(np.clip([f['bfit']['sfr_100'] for f in alldata_2],1e-4,np.inf))
	sfr_7 = np.log10(np.clip([f['bfit']['sfr_100'] for f in alldata_7],1e-4,np.inf))

	fig, ax = plt.subplots(1,2, figsize = (18,8))

	ax[0].errorbar(np.log10(mass_2), np.log10(mass_7), fmt='o',alpha=0.6,linestyle=' ',color='0.4')
	ax[0].set_xlabel(r'log(best-fit M/M$_{\odot}$) [tres = 2]')
	ax[0].set_ylabel(r'log(best-fit M/M$_{\odot}$) [tres = 7]')
	ax[0] = threed_dutils.equalize_axes(ax[0], np.log10(mass_2),np.log10(mass_7))
	off,scat = threed_dutils.offset_and_scatter(np.log10(mass_2),np.log10(mass_7),biweight=True)
	ax[0].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat),
			  transform = ax[0].transAxes,horizontalalignment='right')
	ax[0].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off),
			      transform = ax[0].transAxes,horizontalalignment='right')

	ax[1].errorbar(sfr_2,sfr_7, fmt='o',alpha=0.6,linestyle=' ',color='0.4')
	ax[1].set_xlabel(r'log(best-fit SFR) [tres = 2]')
	ax[1].set_ylabel(r'log(best-fit SFR) [tres = 7]')
	ax[1] = threed_dutils.equalize_axes(ax[1], sfr_2,sfr_7)
	off,scat = threed_dutils.offset_and_scatter(sfr_2,sfr_7,biweight=True)
	ax[1].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat),
			  transform = ax[1].transAxes,horizontalalignment='right')
	ax[1].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off),
			      transform = ax[1].transAxes,horizontalalignment='right')

	plt.savefig(os.getenv('APPS')+'/threedhst_bsfh/plots/brownseds/pcomp/bestfit_mass_sfr_comp.png',dpi=dpi)
	plt.close()

	nparams = len(alldata_2[0]['bfit']['maxprob_params'])
	parnames = alldata_2[0]['pquantiles']['parnames']
	fig, ax = plt.subplots(4,3, figsize = (23/1.5,30/1.5))
	ax = np.ravel(ax)
	for ii in xrange(nparams):
		
		cent2 = np.array([dat['pquantiles']['q50'][ii] for dat in alldata_2])
		up2 = np.array([dat['pquantiles']['q84'][ii] for dat in alldata_2])
		down2 = np.array([dat['pquantiles']['q16'][ii] for dat in alldata_2])

		cent7 = np.array([dat['pquantiles']['q50'][ii] for dat in alldata_7])
		up7 = np.array([dat['pquantiles']['q84'][ii] for dat in alldata_7])
		down7 = np.array([dat['pquantiles']['q16'][ii] for dat in alldata_7])

		if ii == 0:
			errs2 = threed_dutils.asym_errors(cent2, up2, down2, log=True)
			cent2 = np.log10(cent2)
			errs7 = threed_dutils.asym_errors(cent7, up7, down7, log=True)
			cent7 = np.log10(cent7)
		else:
			errs2 = threed_dutils.asym_errors(cent2, up2, down2, log=False)
			errs7 = threed_dutils.asym_errors(cent7, up7, down7, log=False)

		ax[ii].errorbar(cent2,cent7,xerr=errs2,yerr=errs7,fmt='o',color='0.4',alpha=0.6)
		ax[ii].set_xlabel(parnames[ii]+' tres=2')
		ax[ii].set_ylabel(parnames[ii]+' tres=7')

		ax[ii] = threed_dutils.equalize_axes(ax[ii], cent2,cent7)
		off,scat = threed_dutils.offset_and_scatter(cent2,cent7,biweight=True)
		ax[ii].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat),
			  transform = ax[ii].transAxes,horizontalalignment='right')
		ax[ii].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off),
			      transform = ax[ii].transAxes,horizontalalignment='right')

	plt.tight_layout()
	plt.savefig(os.getenv('APPS')+'/threedhst_bsfh/plots/brownseds/pcomp/model_params_comp.png',dpi=dpi)
	plt.close()

	nparams = len(alldata_2[0]['pextras']['parnames'])
	parnames = alldata_2[0]['pextras']['parnames']
	fig, ax = plt.subplots(3,3, figsize = (18,18))
	ax = np.ravel(ax)
	for ii in xrange(nparams):
		
		cent2 = np.array([dat['pextras']['q50'][ii] for dat in alldata_2])
		up2 = np.array([dat['pextras']['q84'][ii] for dat in alldata_2])
		down2 = np.array([dat['pextras']['q16'][ii] for dat in alldata_2])

		cent7 = np.array([dat['pextras']['q50'][ii] for dat in alldata_7])
		up7 = np.array([dat['pextras']['q84'][ii] for dat in alldata_7])
		down7 = np.array([dat['pextras']['q16'][ii] for dat in alldata_7])

		errs2 = threed_dutils.asym_errors(cent2, up2, down2, log=True)
		errs7 = threed_dutils.asym_errors(cent7, up7, down7, log=True)
		if 'ssfr' in parnames[ii]:
			cent2 = np.log10(np.clip(cent2,1e-13,np.inf))
			cent7 = np.log10(np.clip(cent7,1e-13,np.inf))
		elif 'sfr' in parnames[ii]:
			cent2 = np.log10(np.clip(cent2,1e-4,np.inf))
			cent7 = np.log10(np.clip(cent7,1e-4,np.inf))
		elif 'emp_ha' in parnames[ii]:
			cent2 = np.log10(np.clip(cent2,1e37,np.inf))
			cent7 = np.log10(np.clip(cent7,1e37,np.inf))
		else:
			cent2 = np.log10(cent2)
			cent7 = np.log10(cent7)


		ax[ii].errorbar(cent2,cent7,xerr=errs2,yerr=errs7,fmt='o',color='0.4',alpha=0.6)
		ax[ii].set_xlabel('log('+parnames[ii]+') tres=2')
		ax[ii].set_ylabel('log('+parnames[ii]+') tres=7')

		ax[ii] = threed_dutils.equalize_axes(ax[ii], cent2,cent7)
		off,scat = threed_dutils.offset_and_scatter(cent2,cent7,biweight=True)
		ax[ii].text(0.99,0.05, 'biweight scatter='+"{:.3f}".format(scat)+' dex',
			  transform = ax[ii].transAxes,horizontalalignment='right')
		ax[ii].text(0.99,0.1, 'mean offset='+"{:.3f}".format(off)+ 'dex',
			      transform = ax[ii].transAxes,horizontalalignment='right')

	plt.tight_layout()
	plt.savefig(os.getenv('APPS')+'/threedhst_bsfh/plots/brownseds/pcomp/derived_params_comp.png',dpi=dpi)
	plt.close()



