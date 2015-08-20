import numpy as np
import matplotlib.pyplot as plt
from magphys import read_magphys_output
import os, copy, threed_dutils
from bsfh import read_results
import matplotlib.image as mpimg
from matplotlib import gridspec
from scipy.interpolate import interp1d
from matplotlib.ticker import MaxNLocator
import pickle


c = 3e18   # angstroms per second
minsfr = 1e-4
plt.ioff() # don't pop up a window for each plot

#### set up colors and plot style
prosp_color = '#e60000'
obs_color = '#95918C'
magphys_color = '#1974D2'

#### where do the pickle files go?
outpickle = '/Users/joel/code/magphys/data/pickles'

def equalize_axes(ax, x,y, dynrange=0.1, line_of_equality=True):
	
	''' 
	sets up an equal x and y range that encompasses all of the data
	if line_of_equality, add a diagonal line of equality 
	dynrange represents the % of the data range above and below which
	the plot limits are set
	'''

	dynx, dyny = (np.nanmax(x)-np.nanmin(x))*dynrange,\
                 (np.nanmax(y)-np.nanmin(y))*dynrange
	if np.nanmin(x)-dynx > np.nanmin(y)-dyny:
		min = np.nanmin(y)-dyny
	else:
		min = np.nanmin(x)-dynx
	if np.nanmax(x)+dynx > np.nanmax(y)+dyny:
		max = np.nanmax(x)+dynx
	else:
		max = np.nanmax(y)+dyny

	ax.axis((min,max,min,max))

	if line_of_equality:
		ax.errorbar([-1e3,1e3],[-1e3,1e3],linestyle='--',color='0.1',alpha=0.8)

	return ax
	

def plot_comparison(alldata,outfolder):

	'''
	mass vs mass
	sfr vs sfr
	etc
	'''

	##### set up plots
	fig = plt.figure(figsize=(10,10))
	gs1 = gridspec.GridSpec(2, 2)
	mass = plt.Subplot(fig, gs1[0])
	sfr = plt.Subplot(fig, gs1[1])
	met = plt.Subplot(fig, gs1[2])
	age = plt.Subplot(fig,gs1[3])

	fig.add_subplot(mass)
	fig.add_subplot(sfr)
	fig.add_subplot(met)
	#fig.add_subplot(age)

	fmt = 'ko'
	alpha = 0.6

	##### find prospectr indexes
	parnames = alldata[0]['pquantiles']['parnames']
	idx_mass = parnames == 'mass'
	idx_met = parnames == 'logzsol'

	eparnames = alldata[0]['pextras']['parnames']
	idx_sfr = eparnames == 'sfr_100'

	##### find magphys indexes
	idx_mmet = alldata[0]['model']['full_parnames'] == 'Z/Zo'

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
			      xerr=proerrs, yerr=magerrs)

	# labels
	mass.set_xlabel(r'log(M$_*$) [Prospectr]',labelpad=13)
	mass.set_ylabel(r'log(M$_*$) [MAGPHYS]')
	mass = equalize_axes(mass,promass[:,1],magmass[:,1])

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
			      xerr=proerrs, yerr=magerrs)

	# labels
	sfr.set_xlabel(r'log(SFR) [Prospectr]')
	sfr.set_ylabel(r'log(SFR) [MAGPHYS]')
	sfr = equalize_axes(sfr,prosfr[:,1],magsfr[:,1])

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
			      xerr=proerrs)

	# labels
	met.set_xlabel(r'log(Z/Z$_{\odot}$) [Prospectr]',labelpad=13)
	met.set_ylabel(r'log(Z/Z$_{\odot}$) [best-fit MAGPHYS]')
	met = equalize_axes(met,promet[:,1],magmet)

	# text
	off,scat = threed_dutils.offset_and_scatter(promet[:,1],magmet,biweight=True)
	met.text(0.99,0.05, 'biweight scatter='+"{:.2f}".format(scat) + ' dex',
			  transform = met.transAxes,horizontalalignment='right')
	met.text(0.99,0.1, 'mean offset='+"{:.2f}".format(off) + ' dex',
		      transform = met.transAxes,horizontalalignment='right')
	

	plt.savefig(outfolder+'basic_comparison.png',dpi=300)
	plt.close()

def plot_all_residuals(alldata):

	'''
	show all residuals for spectra + photometry, magphys + prospectr
	'''

	##### set up plots
	fig = plt.figure(figsize=(15,12.5))
	gs1 = gridspec.GridSpec(4, 1)
	gs1.update(top=0.95, bottom=0.05, left=0.05, right=0.75,hspace=0.22)
	phot = plt.Subplot(fig, gs1[0])
	opt = plt.Subplot(fig, gs1[1])
	akar = plt.Subplot(fig, gs1[2])
	spit = plt.Subplot(fig,gs1[3])
	

	gs2 = gridspec.GridSpec(4, 1)
	gs2.update(top=0.95, bottom=0.05, left=0.8, right=0.97,hspace=0.22)
	phot_hist = plt.Subplot(fig, gs2[0])
	opt_hist = plt.Subplot(fig, gs2[1])
	akar_hist = plt.Subplot(fig, gs2[2])
	spit_hist = plt.Subplot(fig,gs2[3])
	
	
	##### add plots
	plots = [opt,akar,spit]
	plots_hist = [opt_hist, akar_hist, spit_hist]
	for plot in plots: fig.add_subplot(plot)
	for plot in plots_hist: fig.add_subplot(plot)
	fig.add_subplot(phot)
	fig.add_subplot(phot_hist)

	#### parameters
	alpha_minor = 0.2
	lw_minor = 0.5
	alpha_major = 0.8
	lw_major = 2.5

	##### load and plot photometric residuals
	chi_magphys, chi_prosp, chisq_magphys,chisq_prosp, lam_rest = np.array([]),np.array([]),np.array([]), np.array([]), np.array([])
	for data in alldata:

		if data:
			chi_magphys = np.append(chi_magphys,data['residuals']['phot']['chi_magphys'])
			chi_prosp = np.append(chi_prosp,data['residuals']['phot']['chi_prosp'])
			chisq_magphys = np.append(chisq_magphys,data['residuals']['phot']['chisq_magphys'])
			chisq_prosp = np.append(chisq_prosp,data['residuals']['phot']['chisq_prosp'])
			lam_rest = np.append(lam_rest,np.log10(data['residuals']['phot']['lam_obs']/(1+data['residuals']['phot']['z'])))

			phot.plot(np.log10(data['residuals']['phot']['lam_obs']/(1+data['residuals']['phot']['z'])), 
				      data['residuals']['phot']['chi_magphys'],
				      alpha=alpha_minor,
				      color=magphys_color,
				      lw=lw_minor
				      )

			phot.plot(np.log10(data['residuals']['phot']['lam_obs']/(1+data['residuals']['phot']['z'])), 
				      data['residuals']['phot']['chi_prosp'],
				      alpha=alpha_minor,
				      color=prosp_color,
				      lw=lw_minor
				      )

	##### calculate and plot running median
	nfilters = 33 # calculate this more intelligently?
	magbins, magmedian = threed_dutils.running_median(lam_rest,chi_magphys,nbins=33)
	probins, promedian = threed_dutils.running_median(lam_rest,chi_prosp,nbins=33)

	phot.plot(magbins, 
		      magmedian,
		      color='black',
		      lw=lw_major*1.1
		      )

	phot.plot(magbins, 
		      magmedian,
		      color=magphys_color,
		      lw=lw_major
		      )

	phot.plot(probins, 
		      promedian,
		      color='black',
		      lw=lw_major*1.1
		      )
	phot.plot(probins, 
		      promedian,
		      alpha=alpha_major,
		      color=prosp_color,
		      lw=lw_major
		      )
	phot.text(0.99,0.92, 'MAGPHYS',
			  transform = phot.transAxes,horizontalalignment='right',
			  color=magphys_color)
	phot.text(0.99,0.85, 'Prospectr',
			  transform = phot.transAxes,horizontalalignment='right',
			  color=prosp_color)
	phot.text(0.99,0.05, 'photometry',
			  transform = phot.transAxes,horizontalalignment='right')
	phot.set_xlabel(r'log($\lambda_{\mathrm{rest}}$) [$\AA$]')
	phot.set_ylabel(r'$\chi$')
	phot.axhline(0, linestyle=':', color='grey')

	##### histogram of chisq values
	nbins = 10
	alpha_hist = 0.3
	# first call is transparent, to get bins
	# suitable for both data sets
	histmax = 2
	okmag = chisq_magphys < histmax
	okpro = chisq_prosp < histmax
	n, b, p = phot_hist.hist([chisq_magphys[okmag],chisq_prosp[okpro]],
		                 nbins, histtype='bar',
		                 color=[magphys_color,prosp_color],
		                 alpha=0.0,lw=2)
	n, b, p = phot_hist.hist(chisq_magphys[okmag],
		                 bins=b, histtype='bar',
		                 color=magphys_color,
		                 alpha=alpha_hist,lw=2)
	n, b, p = phot_hist.hist(chisq_prosp[okpro],
		                 bins=b, histtype='bar',
		                 color=prosp_color,
		                 alpha=alpha_hist,lw=2)

	phot_hist.set_ylabel('N')
	phot_hist.set_xlabel(r'$\chi^2_{\mathrm{phot}}/$N$_{\mathrm{phot}}$')

	##### load and plot spectroscopic residuals
	label = ['Optical','Akari', 'Spitzer IRS']
	nbins = [500,50,50]
	for i, plot in enumerate(plots):
		res_magphys, res_prosp, lam_magphys, lam_prosp, mean_off_mag, mean_off_pro = np.array([]),np.array([]),np.array([]),np.array([]),np.array([]),np.array([])
		for data in alldata:
			if data:
				if data['residuals'][label[i]]:
					res_magphys = np.append(res_magphys,data['residuals'][label[i]]['magphys_resid'])
					res_prosp = np.append(res_prosp,data['residuals'][label[i]]['prospectr_resid'])
					lam_magphys = np.append(lam_magphys,np.log10(data['residuals'][label[i]]['magphys_restlam']))
					lam_prosp = np.append(lam_prosp,np.log10(data['residuals'][label[i]]['prospectr_restlam']))		

					plot.plot(np.log10(data['residuals'][label[i]]['magphys_restlam']), 
						      data['residuals'][label[i]]['magphys_resid'],
						      alpha=alpha_minor,
						      color=magphys_color,
						      lw=lw_minor
						      )

					plot.plot(np.log10(data['residuals'][label[i]]['prospectr_restlam']), 
						      data['residuals'][label[i]]['prospectr_resid'],
						      alpha=alpha_minor,
						      color=prosp_color,
						      lw=lw_minor
						      )

					mean_off_mag = np.append(mean_off_mag,np.nanmean(data['residuals'][label[i]]['magphys_resid']))
					mean_off_pro = np.append(mean_off_pro,np.nanmean(data['residuals'][label[i]]['prospectr_resid']))

		##### calculate and plot running median
		magbins, magmedian = threed_dutils.running_median(lam_magphys,res_magphys,nbins=nbins[i])
		probins, promedian = threed_dutils.running_median(lam_prosp,res_prosp,nbins=nbins[i])

		plot.plot(magbins, 
			      magmedian,
			      color='black',
			      lw=lw_major*1.1
			      )

		plot.plot(magbins, 
			      magmedian,
			      color=magphys_color,
			      lw=lw_major
			      )

		plot.plot(probins, 
			      promedian,
			      color='black',
			      lw=lw_major
			      )

		plot.plot(probins, 
			      promedian,
			      color=prosp_color,
			      lw=lw_major
			      )

		plot.set_xlabel(r'log($\lambda_{\mathrm{rest}}$) [$\AA$]')
		plot.set_ylabel(r'log(f$_{\mathrm{obs}}/$f$_{\mathrm{mod}}$)')
		plot.text(0.99,0.05, label[i],
			      transform = plot.transAxes,horizontalalignment='right')
		plot.axhline(0, linestyle=':', color='grey')
	
		##### histogram of mean offsets
		nbins_hist = 10
		alpha_hist = 0.3
		# first histogram is transparent, to get bins
		# suitable for both data sets
		histmax = 2
		okmag = mean_off_mag < histmax
		okpro = mean_off_pro < histmax
		n, b, p = plots_hist[i].hist([mean_off_mag[okmag],mean_off_pro[okpro]],
			                 nbins_hist, histtype='bar',
			                 color=[magphys_color,prosp_color],
			                 alpha=0.0,lw=2)
		n, b, p = plots_hist[i].hist(mean_off_mag[okmag],
			                 bins=b, histtype='bar',
			                 color=magphys_color,
			                 alpha=alpha_hist,lw=2)
		n, b, p = plots_hist[i].hist(mean_off_pro[okpro],
			                 bins=b, histtype='bar',
			                 color=prosp_color,
			                 alpha=alpha_hist,lw=2)

		plots_hist[i].set_ylabel('N')
		plots_hist[i].set_xlabel(r'mean offset [dex]')

		if label[i] == 'Optical':
			plot.set_ylim(-1.5,1.5)
		if label[i] == 'Spitzer IRS':
			plot.set_ylim(-1.5,1.5)

	outfolder = os.getenv('APPS')+'/threedhst_bsfh/plots/brownseds/magphys/'
	
	plt.savefig(outfolder+'median_residuals.png',dpi=300)
	plt.close()

def load_spectra(objname, nufnu=True):
	
	# flux is read in as ergs / s / cm^2 / Angstrom
	# the source key is:
	# 0 = model
	# 1 = optical spectrum
	# 2 = Akari
	# 3 = Spitzer IRS

	foldername = '/Users/joel/code/python/threedhst_bsfh/data/brownseds_data/spectra/'
	rest_lam, flux, obs_lam, source = np.loadtxt(foldername+objname.replace(' ','_')+'_spec.dat',comments='#',unpack=True)

	if nufnu:

		# convert to flam * lam
		flux = flux * obs_lam

		# convert to janskys, then maggies * Hz
		flux = flux * 1e23 / 3631

	out = {}
	out['rest_lam'] = rest_lam
	out['flux'] = flux
	out['obs_lam'] = obs_lam
	out['source'] = source

	return out


def return_sedplot_vars(thetas, sample_results, sps, nufnu=True):

	'''
	if nufnu == True: return in units of nu * fnu (maggies * Hz). Else, return maggies.
	'''

	# observational information
	mask = sample_results['obs']['phot_mask']
	wave_eff = sample_results['obs']['wave_effective'][mask]
	obs_maggies = sample_results['obs']['maggies'][mask]
	obs_maggies_unc = sample_results['obs']['maggies_unc'][mask]

	# model information
	spec, mu ,_ = sample_results['model'].mean_model(thetas, sample_results['obs'], sps=sps)
	mu = mu[mask]

	# output units
	if nufnu == True:
		mu *= c/wave_eff
		spec *= c/sps.wavelengths
		obs_maggies *= c/wave_eff
		obs_maggies_unc *= c/wave_eff

	# here we want to return
	# effective wavelength of photometric bands, observed maggies, observed uncertainty, model maggies, observed_maggies-model_maggies / uncertainties
	# model maggies, observed_maggies-model_maggies/uncertainties
	return wave_eff, obs_maggies, obs_maggies_unc, mu, (obs_maggies-mu)/obs_maggies_unc, spec, sps.wavelengths

def plot_obs_spec(obs_spec, phot, spec_res, alpha, 
	              modlam, modspec, maglam, magspec,z, objname, source,
	              color='black',label=''):

	'''
	standard wrapper for plotting observed + residuals for spectra
	'''

	mask = obs_spec['source'] == source
	if np.sum(mask) > 0:

		phot.plot(np.log10(obs_spec['obs_lam'][mask]), 
			      np.log10(obs_spec['flux'][mask]),
			      alpha=0.9,
			      color=color
			      )

		# interpolate observations onto fsps grid
		obs_flux_interp = interp1d(obs_spec['obs_lam'][mask],
			                       obs_spec['flux'][mask], 
			                       bounds_error = False, fill_value = 0)

		nz = (modlam > np.min(obs_spec['obs_lam'][mask])) & \
		     (modlam < np.max(obs_spec['obs_lam'][mask]))
		prospectr_lam = modlam[nz]
		prospectr_resid = np.log10(obs_flux_interp(modlam[nz])) - np.log10(modspec[nz])
		spec_res.plot(np.log10(prospectr_lam), 
			          prospectr_resid,
			          color=prosp_color,
			          alpha=alpha,
			          linestyle='-')

		# interpolate magphys onto fsps grid
		mag_flux_interp = interp1d(maglam, magspec,
		                           bounds_error=False, fill_value=0)
		magphys_lam = prospectr_lam
		magphys_resid = np.log10(obs_flux_interp(modlam[nz])) - np.log10(mag_flux_interp(modlam[nz]))
		spec_res.plot(np.log10(magphys_lam), 
			          magphys_resid,
			          color=magphys_color,
			          alpha=alpha,
			          linestyle='-')

		#### write text, add lines
		spec_res.text(0.98,0.05, label,
			          transform = spec_res.transAxes,horizontalalignment='right')
		spec_res.axhline(0, linestyle=':', color='grey')
		spec_res.set_xlim(min(np.log10(magphys_lam))*0.95,max(np.log10(magphys_lam))*1.03)
		if label == 'Optical':
			spec_res.set_ylim(-np.std(magphys_resid)*4,np.std(magphys_resid)*4)

		# output rest-frame wavelengths + residuals
		out = {
			   'magphys_restlam': magphys_lam/(1+z),
			   'magphys_resid': magphys_resid,
			   'prospectr_restlam': prospectr_lam/(1+z),
			   'prospectr_resid': prospectr_resid
			   }

		return out

	else:

		# remove axis
		spec_res.axis('off')

def sed_comp_figure(sample_results, sps, model, magphys,
                alpha=0.3, samples = [-1],
                maxprob=0, outname=None, fast=False,
                truths = None, agb_off = False,
                **kwargs):
	"""
	Plot the photometry for the model and data (with error bars) for
	a single object, and plot residuals.

	Returns a dictionary called 'residuals', which contains the 
	photometric + spectroscopic residuals for this object, for both
	magphys and prospectr.
	"""


	#### set up plot
	fig = plt.figure(figsize=(12,12))
	gs = gridspec.GridSpec(2, 1, height_ratios=[3,1])
	gs.update(bottom=0.525, top=0.99, hspace=0.00)
	phot, res = plt.Subplot(fig, gs[0]), plt.Subplot(fig, gs[1])

	gs2 = gridspec.GridSpec(3, 1)
	gs2.update(top=0.475, bottom=0.05, hspace=0.15)
	spec_res_opt,spec_res_akari,spec_res_spit = plt.subplot(gs2[0]),plt.subplot(gs2[1]),plt.subplot(gs2[2])

	ms = 8
	alpha = 0.8

	#### setup output
	residuals={}

	##### Prospectr maximum probability model ######
	# plot the spectrum, photometry, and chi values
	try:
		wave_eff, obsmags, obsmags_unc, modmags, chi, modspec, modlam = \
		return_sedplot_vars(sample_results['quantiles']['maxprob_params'], 
			                sample_results, sps)
	except KeyError:
		print "You must run post-processing on the Prospectr " + \
			  "data for " + sample_results['run_params']['objname']
		return None

	phot.plot(np.log10(wave_eff), np.log10(modmags), 
		      color=prosp_color, marker='o', ms=ms, 
		      linestyle=' ', label='Prospectr', alpha=alpha, 
		      markeredgewidth=0.7,**kwargs)
	
	res.plot(np.log10(wave_eff), chi, 
		     color=prosp_color, marker='o', linestyle=' ', label='Prospectr', 
		     ms=ms,alpha=alpha,markeredgewidth=0.7,**kwargs)
	
	nz = modspec > 0
	phot.plot(np.log10(modlam[nz]), np.log10(modspec[nz]), linestyle='-',
              color=prosp_color, alpha=0.6,**kwargs)

	##### photometric observations, errors ######
	xplot = np.log10(wave_eff)
	yplot = np.log10(obsmags)
	linerr_down = np.clip(obsmags-obsmags_unc, 1e-80, np.inf)
	linerr_up = np.clip(obsmags+obsmags_unc, 1e-80, np.inf)
	yerr = [yplot - np.log10(linerr_down), np.log10(linerr_up)-yplot]
	phot.errorbar(xplot, yplot, yerr=yerr,
                  color=obs_color, marker='o', label='observed', alpha=alpha, linestyle=' ',ms=ms)
	print 1/0
	# plot limits
	phot.set_xlim(3.1,max(xplot)*1.04)
	phot.set_ylim(min(yplot[np.isfinite(yplot)])*0.95,max(yplot[np.isfinite(yplot)])*1.04)
	res.set_xlim(3.1,max(xplot)*1.04)
	res.axhline(0, linestyle=':', color='grey')

	##### magphys: spectrum + photometry #####
	# note: we steal the filter effective wavelengths from Prospectr here
	# if filters are mismatched in Prospectr vs MAGPHYS, this will do weird things
	# not fixing it, since it may serve as an "alarm bell"
	m = magphys['obs']['phot_mask']

	# comes out in maggies, change to maggies*Hz
	nu_eff = c / wave_eff
	spec_fac = c / magphys['model']['lam']

	try:
		phot.plot(np.log10(wave_eff), 
			      np.log10(magphys['model']['flux'][m]*nu_eff), 
			      color=magphys_color, marker='o', ms=ms, 
			      linestyle=' ', label='MAGPHYS', alpha=alpha, 
			      markeredgewidth=0.7,**kwargs)
	except:
		print sample_results['obs']['phot_mask']
		print magphys['obs']['phot_mask']
		print sample_results['run_params']['objname']
		print 'Mismatch between Prospectr and MAGPHYS photometry!'
		plt.close()
		return None
	
	chi_magphys = (magphys['obs']['flux'][m]-magphys['model']['flux'][m])/magphys['obs']['flux_unc'][m]
	res.plot(np.log10(wave_eff), 
		     chi_magphys, 
		     color=magphys_color, marker='o', linestyle=' ', label='MAGPHYS', 
		     ms=ms,alpha=alpha,markeredgewidth=0.7,**kwargs)
	
	nz = magphys['model']['spec'] > 0
	phot.plot(np.log10(magphys['model']['lam'][nz]), 
		      np.log10(magphys['model']['spec'][nz]*spec_fac), 
		      linestyle='-', color=magphys_color, alpha=0.6,
		      **kwargs)

	##### observed spectra + residuals #####
	obs_spec = load_spectra(sample_results['run_params']['objname'])

	label = ['Optical','Akari', 'Spitzer IRS']
	resplots = [spec_res_opt, spec_res_akari, spec_res_spit]

	for ii in xrange(3):
		residuals[label[ii]] = plot_obs_spec(obs_spec, phot, resplots[ii], alpha, modlam, modspec,
					                         magphys['model']['lam'], magphys['model']['spec']*spec_fac,
					                         magphys['metadata']['redshift'], sample_results['run_params']['objname'],
		                                     ii+1, color=obs_color, label=label[ii])

	# diagnostic text
	textx = (phot.get_xlim()[1]-phot.get_xlim()[0])*0.975+phot.get_xlim()[0]
	texty = (phot.get_ylim()[1]-phot.get_ylim()[0])*0.2+phot.get_ylim()[0]
	deltay = (phot.get_ylim()[1]-phot.get_ylim()[0])*0.038

	# calculate reduced chi-squared
	chisq=np.sum(chi**2)/np.sum(sample_results['obs']['phot_mask'])
	chisq_magphys=np.sum(chi_magphys**2)/np.sum(sample_results['obs']['phot_mask'])
	print magphys['metadata']['chisq'], chisq_magphys
	#ndof = np.sum(sample_results['obs']['phot_mask']) - len(sample_results['model'].free_params)-1
	#reduced_chisq = chisq/(ndof-1)
	phot.text(textx, texty, r'best-fit $\chi^2/$N$_{\mathrm{phot}}$='+"{:.2f}".format(chisq),
			  fontsize=10, ha='right', color=prosp_color)
	phot.text(textx, texty-deltay, r'best-fit $\chi^2/$N$_{\mathrm{phot}}$='+"{:.2f}".format(chisq_magphys),
			  fontsize=10, ha='right', color=magphys_color)
		
	z_txt = sample_results['model'].params['zred'][0]
		
	# galaxy text
	phot.text(textx, texty-2*deltay, 'z='+"{:.2f}".format(z_txt),
			  fontsize=10, ha='right')
		
	# extra line
	phot.axhline(0, linestyle=':', color='grey')
	
	# legend
	# make sure not to repeat labels
	from collections import OrderedDict
	handles, labels = phot.get_legend_handles_labels()
	by_label = OrderedDict(zip(labels, handles))
	phot.legend(by_label.values(), by_label.keys(), 
				loc=1, prop={'size':8},
			    frameon=False)
			    
    # set labels
	res.set_ylabel( r'$\chi$')
	for plot in resplots: plot.set_ylabel( r'log(f$_{\mathrm{obs}}/$f$_{\mathrm{mod}}$)')
	phot.set_ylabel(r'log($\nu f_{\nu}$)')
	spec_res_spit.set_xlabel(r'log($\lambda_{obs}$) [$\AA$]')
	
	# chill on the number of tick marks
	#res.yaxis.set_major_locator(MaxNLocator(4))
	allres = resplots+[res]
	for plot in allres: plot.yaxis.set_major_locator(MaxNLocator(4))

	# clean up and output
	fig.add_subplot(phot)
	for res in allres: fig.add_subplot(res)
	
	# set second x-axis
	y1, y2=phot.get_ylim()
	x1, x2=phot.get_xlim()
	ax2=phot.twiny()
	ax2.set_xticks(np.arange(0,10,0.2))
	ax2.set_xlim(np.log10((10**(x1))/(1+z_txt)), np.log10((10**(x2))/(1+z_txt)))
	ax2.set_xlabel(r'log($\lambda_{rest}$) [$\AA$]')
	ax2.set_ylim(y1, y2)

	# remove ticks
	phot.set_xticklabels([])
    
	if outname is not None:
		fig.savefig(outname, bbox_inches='tight', dpi=500)
		#os.system('open '+outname)
		plt.close()

	# save chi for photometry
	out = {'chi_magphys': chi_magphys,
	       'chi_prosp': chi,
	       'chisq_prosp': chisq,
	       'chisq_magphys': chisq_magphys,
	       'lam_obs': wave_eff,
	       'z': magphys['metadata']['redshift']
	       }
	residuals['phot'] = out
	return residuals
	
def collate_data(filebase=None,
				   outfolder=os.getenv('APPS')+'/threedhst_bsfh/plots/',
				   sample_results=None,
				   sps=None,
				   plt_sed=True):

	'''
	Driver. Loads output, makes residual plots for a given galaxy, saves collated output.
	'''

	# make sure the output folder exists
	if not os.path.isdir(outfolder):
		os.makedirs(outfolder)

	
	# find most recent output file
	# with the objname
	folder = "/".join(filebase.split('/')[:-1])
	filename = filebase.split("/")[-1]
	files = [f for f in os.listdir(folder) if "_".join(f.split('_')[:-2]) == filename]	
	times = [f.split('_')[-2] for f in files]

	# if we found no files, skip this object
	if len(times) == 0:
		print 'Failed to find any files to extract times in ' + folder + ' of form ' + filename
		return 0

	# load results
	mcmc_filename=filebase+'_'+max(times)+"_mcmc"
	model_filename=filebase+'_'+max(times)+"_model"

	# load if necessary
	if not sample_results:
		try:
			sample_results, powell_results, model = read_results.read_pickles(mcmc_filename, model_file=model_filename,inmod=None)
		except (EOFError,ValueError) as e:
			print e
			print 'Failed to open '+ mcmc_filename +','+model_filename
			return 0
	else:
		import pickle
		try:
			mf = pickle.load( open(model_filename, 'rb'))
		except(AttributeError):
			mf = load( open(model_filename, 'rb'))
       
		powell_results = mf['powell']

	if not sps:
		# load stellar population, set up custom filters
		if np.sum([1 for x in sample_results['model'].config_list if x['name'] == 'pmetals']) > 0:
			sps = threed_dutils.setup_sps(custom_filter_key=sample_results['run_params'].get('custom_filter_key',None))
		else:
			sps = threed_dutils.setup_sps(zcontinuous=1,
										  custom_filter_key=sample_results['run_params'].get('custom_filter_key',None))

	# load magphys
	magphys = read_magphys_output(objname=sample_results['run_params']['objname'])

	# BEGIN PLOT ROUTINE
	print 'MAKING PLOTS FOR ' + filename + ' in ' + outfolder
	alldata = {}

	# sed plot
	if plt_sed:
		print 'MAKING SED COMPARISON PLOT'
 		# plot
 		residuals = sed_comp_figure(sample_results, sps, copy.deepcopy(sample_results['model']),
 						  magphys, maxprob=1,
 						  outname=outfolder+filename.replace(' ','_')+'.sed.png')
 		
	# SAVE OUTPUTS
	if residuals is not None:
		print 'SAVING OUTPUTS for ' + sample_results['run_params']['objname']
		alldata['residuals'] = residuals
		alldata['magphys'] = magphys['pdfs']
		alldata['model'] = magphys['model']
		alldata['pquantiles'] = sample_results['quantiles']
		alldata['pextras'] = sample_results['extras']
		alldata['pquantiles']['parnames'] = np.array(sample_results['model'].theta_labels())
	else:
		alldata = None

	return alldata

def plt_all(runname=None,startup=True,**extras):

	'''
	for a list of galaxies, make all plots

	startup: if True, then make all the residual plots and save pickle file
			 if False, load previous pickle file
	'''
	if runname == None:
		runname = 'brownseds'

	output = outpickle+'/alldata.pickle'
	outfolder = os.getenv('APPS')+'/threedhst_bsfh/plots/'+runname+'/magphys/sed_residuals/'

	if startup == True:
		filebase, parm_basename, ancilname=threed_dutils.generate_basenames(runname)
		alldata = []
		for jj in xrange(len(filebase)):
			print 'iteration '+str(jj) 
			dictionary = collate_data(filebase=filebase[jj],\
			                           outfolder=outfolder,
			                           **extras)
			alldata.append(dictionary)

		pickle.dump(alldata,open(output, "wb"))
	else:
		with open(output, "rb") as f:
			alldata=pickle.load(f)

	plot_all_residuals(alldata)
	plot_comparison(alldata,os.getenv('APPS')+'/threedhst_bsfh/plots/'+runname+'/magphys/')
	plot_mass_metallicity(alldata)
	plot_sfr_mass(alldata)
	