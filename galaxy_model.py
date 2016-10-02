#!/usr/bin/python
"""
Calculate the AGN fraction and luminosity distribution as a function of M_* 
and z, using the pdfs from Aird et al. (2012) [1107.4368], Eq. 12 and Table 2.
"""
import numpy as np
import pylab as P
import scipy.integrate
import scipy.interpolate
from scipy.special import erf, erfinv
from halomodel import HaloModel

# Central wavelength (in Angstroms) of a given band.
band_wavelength = {
    'u':    3543.,
    'g':    4770.,
    'r':    6231.,
    'i':    7625.,
    'z':    9134.,
}

default_cosmo_params = {
    'omega_M_0':        0.316,
    'omega_lambda_0':   0.684,
    'omega_b_0':        0.049,
    'h':                0.67,
    'ns':               0.962,
    'sigma_8':          0.834,
    'gamma':            0.55,
    'w0':               -1.,
    'wa':               0.,
}

default_params = {
            
    # SFR - stellar mass relation
    # (Derived from Table 2 of Wang, Farrah, Oliver et al. 2013, Table 2)
    #'sfr_alpha0':   -3.47, #-9. illustris
    #'sfr_alpha1':   1.07, # 0.5
    #'sfr_beta':     0.37, # 0.9
    
    # SFR - stellar mass relation (SFMS)
    'sfr_sfms_alpha0':      -3.47, # -5, De Lucia
    'sfr_sfms_alpha1':      1.07,
    'sfr_sfms_beta':        0.37, # 0.45, De Lucia
    'sfr_sfms_sigma':       0.3,  # scatter [dex]
    
    # SFR - stellar mass relation (passive)
    #'sfr_pass_logu':        False, # log-uniform or log-normal passive SF pop.?
    'sfr_pass_type':        'indep', # Type of passive sequence
    # (log-uniform, 'log uniform')
    'sfr_pass_pthres':      0.05, # Threshold of SFMS pdf at which to set SFR_max
    'sfr_pass_sfrmin':      1e-7, # Minimum SFR [M_sun/yr]
    # (log-normal, shifted, 'shifted sfms')
    'sfr_pass_sigma':       0.4,
    'sfr_pass_mshift':      1e-3, # Mean is SFMS mean scaled by this factor
    # (log-normal, independent, 'indep', default)
    'sfr_pass_alpha0':      -4.5,
    'sfr_pass_alpha1':      1.07,
    'sfr_pass_beta':        0.37,
    'sfr_pass_sigma':       0.4,
    
    
    # Stellar mass - halo mass relation
    # (Default values from Moster et al. 2010, Table 7)
    'ms_cen_logM1':         11.88,
    'ms_cen_norm':          0.0282,
    # (redshift dependence)
    'ms_cen_mu':            0.019,
    'ms_cen_nu':            -0.72,
    'ms_cen_beta0':         1.06,
    'ms_cen_beta1':         0.17,
    'ms_cen_gamma0':        0.556,
    'ms_cen_gamma1':        -0.26,
    # (scatter parameters)
    'ms_cen_sigmainf':      0.1592,
    'ms_cen_sigma1':        0.0460,
    'ms_cen_logM2':         11.8045,
    'ms_cen_xi':            4.2503,
    #'ms_sigma':             0.15, # Scatter, in dex
    
    # Fraction of passive (vs. star-forming) galaxies
    'fpass_alpha0':         10.2,
    'fpass_alpha1':         0.5,
    'fpass_beta':           -1.3,
    'fpass_zeta':           -20.,
    
    # Grid resolution parameters
    'mass_mstar_min':       6.,
    'mass_mstar_max':       14.,
    'mass_mhalo_min':       5.,
    'mass_mhalo_max':       16.,
    'sfr_min':              -5.,
    'sfr_max':              4.,
    
    'nsamp_mstar':          200,
    'nsamp_mhalo':          200,
    'nsamp_sfr':            200,
    
    # HI mass - halo mass relation
    'mhi_omegaHI':          1e-4,
    'mhi_vc0':              50.,
    'mhi_vc1':              200.,
    
    # Optical magnitude fitting function (parameters specified per-band)
    'opt_bands':            ['u', 'g', 'r', 'i', 'z'],
    'opt_cross_amp':        [-3.61194266, -2.70027825, -2.01635745, -1.72575487,
                             -1.56393268],
    'opt_cross_beta':       -0.262636097,
    'opt_cross_gamma':      0.290177366,
    'opt_mstar_amp':        3876.55879,
    'opt_mstar_beta':       -0.000242854097,
    'opt_mstar_c':          -1.0108709,
    'opt_offset':           [-27.3176081, -25.9445857, -25.2836569, -24.981922, 
                             -24.8096689],
    'opt_pdf_mean':         [-0.065874811689195914, -0.053777765775930214,
                             -0.018547128851928552, -0.0085386560954659688,
                             -0.0087323005037165322],
    'opt_pdf_sigma':        [0.28122634653850337, 0.25232918833346546, 
                             0.2468073941298409, 0.25273681573440887,
                             0.27245133519998282],
    
    # Guo (2010)
    #'opt_bands':        ['u', 'g', 'r', 'i', 'z'],
    #'opt_Amstar':       [1.2498e+04, 1.0426e+04, 7.2791e+03, 6.0470e+03, 
    #                     2.5695e+04],
    #'opt_Across':       [-4.1036e+00, -2.9742e+00, -2.2223e+00, -1.9305e+00, 
    #                     -1.2898e+04],
    #'opt_beta':         [-6.5246e-05, -8.4736e-05, -1.2782e-04, -1.5775e-04, 
    #                     1.1491e-03],
    #'opt_delta':        [-2.4003e-01, -2.5516e-01, -2.6497e-01, -2.6615e-01, 
    #                     2.3634e-03],
    #'opt_gamma':        [3.1723e-01, 3.1895e-01, 3.2399e-01, 3.2504e-01, 
    #                     6.7098e-06],
    #'opt_c':            [-1.2512e+04, -1.0443e+04, -7.2960e+03, -6.0642e+03,
    #                     -1.2815e+04],
    #'opt_sigma':        [2.7963e-01, 2.7666e-01, 2.4629e-01, 2.3056e-01,
    #                     2.7222e-01],
    # De Lucia (2006)
    #'opt_bands':        ['B', 'V', 'R', 'I', 'K'], # De Lucia
    #'opt_Amstar':       [-2.4227e+02, 2.5189e+03, 5.4991e+02, -7.0327e+03, 
    #                     -9.7559e+03],
    #'opt_Across':       [-3.1989e+00, -2.4842e+00, -2.0832e+00, -1.8321e+00, 
    #                     -1.5064e+00],
    #'opt_beta':         [3.8688e-03, -3.8545e-04, -1.8032e-03, 1.4392e-04, 
    #                     1.0981e-04],
    #'opt_delta':        [-2.4241e-01, -2.5447e-01, -2.5594e-01, -2.5203e-01, 
    #                     -2.1210e-01],
    #'opt_gamma':        [2.6720e-01, 2.6709e-01, 2.6306e-01, 2.5988e-01, 
    #                     2.2515e-01],
    #'opt_c':            [2.2667e+02, -2.5354e+03, -5.6709e+02, 7.0150e+03, 
    #                     9.7367e+03],
    #'opt_sigma':        [2.4427e-01, 2.2503e-01, 2.0935e-01, 1.9636e-01, 
    #                     1.8812e-01],
}


def mass_stellar_cen(Mh, z, params):
    """
    Fitting function for the central galaxy stellar mass of a given halo, 
    using Eq.2 of Moster, B. P. et al. 2010, ApJ, 710, 903.
    [Mvir should be in Msun]
    """
    # Best-fit parameters
    logM1 = params['ms_cen_logM1']
    norm0 = params['ms_cen_norm'] # (m/M)_0
    mu = params['ms_cen_mu']
    nu = params['ms_cen_nu']
    beta0 = params['ms_cen_beta0']
    beta1 = params['ms_cen_beta1']
    gamma0 = params['ms_cen_gamma0']
    gamma1 = params['ms_cen_gamma1']
    
    # Redshift-dependent functions (Eqs. 23-26 of Moster et al.)
    logM1 = logM1 * (1. + z)**mu
    M1 = 10.**logM1
    norm = norm0 * (1. + z)**nu
    beta = beta0 + beta1*z
    gamma = gamma0 * (1. + z)**gamma1
    
    return 2.*Mh * norm / ((Mh/M1)**(-beta) + (Mh/M1)**gamma)


def mass_stellar_sat(Mh, z, params):
    """
    Fitting function for the satellite galaxy stellar mass of a given halo, 
    using Eq.13 of Moster, B. P. et al. 2010, ApJ, 710, 903.
    [Mvir should be in Msun]
    """
    logM1 = params['ms_sat_logM1']
    norm0 = params['ms_sat_norm'] # (m/M)_0
    beta = params['ms_sat_beta']
    gamma = params['ms_sat_gamma']
    
    # FIXME: Assumed no redshift dependence for satellite parameters!
    logM1 = logM1
    M1 = 10.**logM1
    norm = norm0
    return 2.*Mh * norm / ((Mh/M1)**(-beta) + (Mh/M1)**gamma)


def pdf_mass_stellar_cen(Ms, Mh, z, params):
    """
    Prob. density function for stellar mass, given halo mass and redshift. Uses 
    the form from Moster et al. (2010). Central galaxies.
    """
    sigma_inf = params['ms_cen_sigmainf']
    sigma1 = params['ms_cen_sigma1']
    M2 = 10.**params['ms_cen_logM2']
    xi = params['ms_cen_xi']
    
    # Mean stellar mass as fn. of halo mass
    mean_ms = mass_stellar_cen(Mh, z, params=params)
    
    # Scatter as a fn. of halo mass [Eq. 12 of Moster et al. (2010)]
    sigma = sigma_inf + sigma1*(1. - 2./np.pi * np.arctan(xi*np.log10(Mh/M2)))
    sigma *= np.log(10.) # sigma in dex
    
    # Return pdf
    return np.exp(-np.log(Ms/mean_ms)**2./(2.*sigma**2.)) \
         / (np.sqrt(2.*np.pi)*sigma*Ms)


def pdf_mass_stellar_sat(Ms, Mh, z, params):
    """
    Prob. density function for stellar mass, given halo mass and redshift. Uses 
    the form from Moster et al. (2010). Satellite galaxies.
    """
    sigma_inf = params['ms_sat_sigmainf']
    sigma1 = params['ms_sat_sigma1']
    M3 = 10.**params['ms_sat_logM3']
    xi = params['ms_sat_xi']
    
    # Mean stellar mass as fn. of halo mass
    mean_ms = mass_stellar_sat(Mh, z, params=params)
    
    # Schechter function exponent [Eq. 15 of Moster et al. (2010)]
    alpha = alpha_inf + alpha1*(1. - 2./np.pi * np.arctan(xi*np.log10(Mh/M3)))
    
    # Return pdf [Eq. 9]
    return phi0 * (Mh)**lam / mean_ms * (Ms/mean_ms)**alpha \
         * np.exp(-(Ms/mean_ms)**2.)


def pdf_mass_stellar(Ms, Mh, z, params):
    # FIXME: Uses centrals only
    return pdf_mass_stellar_cen(Ms, Mh, z, params=params)


def stellar_mass_fn(hm, mstar, z, params):
    """
    Calculate the stellar mass function, dn/dlog(M*), as a function of stellar 
    mass and redshift.
    """
    # Halo mass function, n(M_h) = dn/dlogM
    Mh = np.logspace(params['mass_mhalo_min'], params['mass_mhalo_max'], 
                     params['nsamp_mhalo'])
    dndlogm = hm.dndlogm(Mh, z)
    
    # Integrate mass fn. over halo mass, weighted by p(M* | M_h), to get n(M*)
    n_mstar = [ scipy.integrate.simps(
                  dndlogm * pdf_mass_stellar(_mstar, Mh, z, 
                                             params=params),
                  np.log(Mh) ) for _mstar in mstar]
    return mstar * np.array(n_mstar) # Convert to dn/dlog(M*)


def f_passive(mstar, z, params):
    """
    Fraction of passive galaxies at a given stellar mass and redshift.
    """
    alpha0 = params['fpass_alpha0']
    alpha1 = params['fpass_alpha1']
    beta = params['fpass_beta']
    c = 0.5 * (1. + np.tanh(params['fpass_zeta']))
    
    return c + (1. - c) / ( 1. + (mstar / (10.**(alpha0 + alpha1*z)))**beta )


def sfr_sfms(mstar, z, params):
    """
    Mean SFR of the star-formation main sequence.
    """
    alpha0 = params['sfr_sfms_alpha0']
    alpha1 = params['sfr_sfms_alpha1']
    beta = params['sfr_sfms_beta']
    sfr = 10.**(alpha0 + alpha1*z) * (mstar/1e10)**beta
    return sfr

def sfr_pass(mstar, z, params):
    """
    Mean SFR of the passive sequence (assuming a power-law like the SFMS).
    """
    alpha0 = params['sfr_pass_alpha0']
    alpha1 = params['sfr_pass_alpha1']
    beta = params['sfr_pass_beta']
    return 10.**(alpha0 + alpha1*z) * (mstar/1e10)**beta

def sfrmax_passive(mstar, z, params, pthres=0.05):
    """
    Get maximum SFR for the passive SF population, which is defined to be some 
    value in the lower wing of the SFMS distribution. For example, pthres=0.05 
    places the maximum at the 5% level of the SFMS distribution.
    """
    sigma = params['sfr_sfms_sigma'] * np.log(10.)
    mean_sfr = sfr_sfms(mstar, z)
    # cdf of log-normal distribution is function of erf; need erfinv to invert
    return mean_sfr * np.exp(np.sqrt(2.)*sigma * erfinv(2.*pthres - 1.))


def pdf_sfr_sfms(sfr, mstar, z, params):
    """
    Prob. density function for SFR on the SF main sequence, given stellar mass 
    and redshift, p(SFR | M_*, z).
    """
    sigma = params['sfr_sfms_sigma'] * np.log(10.)
    mean_sfr = sfr_sfms(mstar, z, params=params)
    
    # FIXME
    if 'sfr_sfms_mscale' in params.keys() \
    and 'sfr_sfms_gamma' in params.keys():
        mscale = 10.**params['sfr_sfms_mscale']
        gamma = params['sfr_sfms_gamma']
        mean_sfr *= (1. - np.exp(-(mstar/mscale)**gamma))
    
    return np.exp(-np.log(sfr/mean_sfr)**2./(2.*sigma**2.)) \
         / (np.sqrt(2.*np.pi)*sigma*sfr)


def pdf_sfr_passive_loguniform(sfr, mstar, z, params):
    """
    Prob. density function for SFR for passive SF galaxies, given stellar mass 
    and redshift, p(SFR | M_*, z). [log-uniform version]
    """
    sfrmax = sfrmax_passive(mstar, z, pthres=params['sfr_pass_pthres'])
    sfrmin = params['sfr_pass_sfrmin'] * np.ones(sfrmax.shape)
    
    idxs = np.where(np.logical_or(sfr < sfrmin, sfr > sfrmax))
    p = 1./sfr / np.log(sfrmax / sfrmin)
    p[idxs] = 0. # Remove values outside of bounds
    return p


def pdf_sfr_passive_lognormal(sfr, mstar, z, params, type='shifted'):
    """
    Prob. density function for SFR on the SF main sequence, given stellar mass 
    and redshift, p(SFR | M_*, z). [log-normal version]
    """
    if type == 'shifted':
        # Take the SFMS powerlaw, shift it by some factor, and change scatter
        assert params['sfr_pass_mshift'] >= 0.
        sigma = params['sfr_pass_sigma'] * np.log(10.) # sigma in dex
        mean_sfr = sfr_sfms(mstar, z, params=params) * params['sfr_pass_mshift']
        
        # FIXME
        if 'sfr_sfms_mscale' in params.keys() \
        and 'sfr_sfms_gamma' in params.keys():
            mscale = 10.**params['sfr_pass_mscale']
            gamma = params['sfr_pass_gamma']
            mean_sfr *= (1. - np.exp(-(mstar/mscale)**gamma))
    else:
        # Use a different powerlaw to the SFMS, and a different scatter
        sigma = params['sfr_pass_sigma'] * np.log(10.) # sigma in dex
        mean_sfr = sfr_pass(mstar, z, params=params)
    
    return np.exp(-0.5 * (np.log(sfr/mean_sfr) / sigma)**2.) \
         / (np.sqrt(2.*np.pi)*sigma*sfr)


def pdf_sfr_passive(sfr, mstar, z, params):
    """
    Prob. density function for SFR on the SF main sequence, given stellar mass 
    and redshift, p(SFR | M_*, z).
    """
    if params['sfr_pass_type'] == 'log uniform':
        return pdf_sfr_passive_loguniform(sfr, mstar, z, params)
    elif params['sfr_pass_type'] == 'shifted sfms':
        return pdf_sfr_passive_lognormal(sfr, mstar, z, params, type='shifted')
    else:
        return pdf_sfr_passive_lognormal(sfr, mstar, z, params, type='indep')


def sfr_fn(hm, sfr, z, params):
    """
    Number density for a given SFR, found by integrating the stellar mass 
    function weighted by p(SFR|M*).
    """
    mstar = np.logspace(params['mass_mstar_min'], params['mass_mstar_max'],
                        params['nsamp_mstar'])
    
    # Calculate passive fraction and stellar mass function
    fpass = f_passive(mstar, z, params=params)
    dndlogms = stellar_mass_fn(hm, mstar, z, params=params)
    
    # Integrate over stellar mass function, weighted by p(SFR | M_*), 
    # to get n(SFR); do this for each population
    n_sfr_sfms = [ scipy.integrate.simps(
                    (1.-fpass) * dndlogms * pdf_sfr_sfms(_sfr, mstar, z, 
                                                     params=params),
                    np.log(mstar) ) for _sfr in sfr]
    n_sfr_pass = [ scipy.integrate.simps(
                    fpass * dndlogms * pdf_sfr_passive(_sfr, mstar, z, 
                                                     params=params),
                    np.log(mstar) ) for _sfr in sfr]
    n_sfr_sfms = np.array(n_sfr_sfms)
    n_sfr_pass = np.array(n_sfr_pass)
    
    # Return total function (dn/dlog(SFR))
    #return sfr * (n_sfr_sfms + n_sfr_pass)
    return sfr * n_sfr_sfms, sfr * n_sfr_pass


def mhalo_mstar_plane(hm, mhalo, mstar, z, params):
    """
    Convenience function to return M_halo vs. M* grid, assuming log bins.
    """
    # Calculate halo mass function
    dndlogm = hm.dndlogm(mhalo, z=z)
    
    # Calculate number density in each population
    n_mstar = np.array([_mstar * pdf_mass_stellar(_mstar, mhalo, z,
                                                  params=params) 
                                 for _mstar in mstar]) * dndlogm
    return n_mstar


def sfr_mstar_plane(hm, sfr, mstar, z, params):
    """
    Convenience function to return SFR vs. M* grid, assuming log bins.
    """
    # Calculate passive fraction and stellar mass function
    fpass = f_passive(mstar, z, params)
    dndlogms = stellar_mass_fn(hm, mstar, z, params)
    
    # Calculate number density in each population
    n_sfr_mstar_sfms = np.array([_sfr * pdf_sfr_sfms(_sfr, mstar, z, 
                                                      params=params) 
                                 for _sfr in sfr]) * (1.-fpass) * dndlogms
    n_sfr_mstar_pass = np.array([_sfr * pdf_sfr_passive(_sfr, mstar, z, 
                                                      params=params) 
                                 for _sfr in sfr]) * fpass * dndlogms
    return n_sfr_mstar_sfms, n_sfr_mstar_pass
    
    
def sfr_to_luminosity(sfr, type, z, params):
    """
    Convert the SFR to a luminosity. Expects SFR in M_sun/yr, outputs 
    luminosity in erg/s.
    """
    type = type.lower()
    
    # Choose which Kennicut-Schmidt law to use
    if type == 'halpha':
        # H-alpha line
        return sfr / 7.9e-42 # astro-ph/9807187, Eq. 2
        
    elif type == '24um':
        # Infrared, 24 micron
        return sfr / 4.5e-44
        
    elif type == '1.4ghz':
        # Radio (SF only) 1.4 GHz
        #return sfr * 4.324e29 # arXiv:0810.4150, Eq. 17
        return sfr / 5.52e-29 # erg/s/Hz, Bell (2003), Eq. 6
    
    elif type == 'yun1.4ghz':
        # Radio (SF only) 1.4 GHz
        return sfr / 5.9e-29 # erg/s/Hz, Yun (2001), Eq. 14
    else:
        raise ValueError("Luminosity type '%s' not recognised." % type)


def luminosity_sfr(hm, z, params, 
                   pkfile="camb_pk_z0.dat"):
    """
    Return luminosity function as a function of log-SFR, i.e. dn/dlog(SFR).
    """
    # Load my halo model
    hm = HaloModel(pkfile, h=0.67, om=0.32) # FIXME

    # Number density as a function of halo mass, dn/dlog(mhalo)
    mhalo = np.logspace(params['mass_mhalo_min'], params['mass_mhalo_max'], 
                        params['nsamp_mhalo'])
    dndlogm = hm.dndlogm(mhalo, z=z)

    # Number density as a function of stellar mass, dn/dlog(mstar)
    mstar = np.logspace(params['mass_mstar_min'], params['mass_mstar_max'], 
                        params['nsamp_mstar'])
    dndlogms = stellar_mass_fn(hm, mstar, z=z, params=params)

    # Number density as a function of sfr, dn/dlog(sfr)
    sfr = np.logspace(params['sfr_min'], params['sfr_max'], params['nsamp_sfr'])
    dndlogsfr_sfms, dndlogsfr_pass = sfr_fn(hm, sfr, z=z, params=params)
    
    return sfr, dndlogsfr_sfms, dndlogsfr_pass

"""
def optical_mag_old(sfr, mstar, band, z, params):
    \"""
    Return the predicted optical magnitude given the stellar mass and SFR. 
    Calculated using an ansatz with best-fit parameters calibrated against 
    the De Lucia catalogue.
    \"""
    # Figure out which band to use
    if band in params['opt_bands']:
        i = params['opt_bands'].index(band)
    else:
        raise KeyError("Band '%s' not recognised; available bands are: %s" % \
                       (band, params['opt_bands']))
    
    # Ansatz, roughly taking into account 2 sources of stellar light: star 
    # formation (SFR as proxy) and older stars (via stellar mass)
    mag = params['opt_Amstar'][i] * (mstar/1e9)**params['opt_beta'][i] \
        + params['opt_Across'][i] * (mstar/1e9)**params['opt_delta'][i] \
          * (sfr)**params['opt_gamma'][i] + params['opt_c'][i]
    return mag


def pdf_optical_mag_old(mag, sfr, mstar, band, z, params):
    \"""
    Intrinsic optical magnitude pdf, conditioned on Mstar and SFR: 
    p(mag_X | M_*, SFR, z). 
    Assumed to be Gaussian with scatter measured from Guo et al. simulations.
    \"""
    # Figure out which band to use
    if band in params['opt_bands']:
        i = params['opt_bands'].index(band)
    else:
        raise KeyError("Band '%s' not recognised; available bands are: %s" % \
                       (band, params['opt_bands']))
    
    # Mean and standard deviation
    mu = optical_mag(sfr, mstar, band, z=z, params=params)
    sigma = params['opt_sigma'][i]
    
    # Return Gaussian PDF
    return np.exp(-(mag - mu)**2. / (2. * sigma**2.)) \
           / (np.sqrt(2.*np.pi) * sigma)
"""

def tau_extinction(sintheta, mstar, band, z, params):
    """
    Dust extinction optical depth as a function of inclination angle.
    """
    # Extinction parameters
    A = params['extinction_amp']
    beta = params['extinction_beta']
    kappa = params['extinction_diskfac']
    alpha = params['extinction_alpha']
    
    # Get band wavelength
    l = band_wavelength[band]
    
    # Calculate optical depth and return
    return A * (mstar / 1e10)**beta * (1. + kappa*sintheta) \
             * (l / 5000.)**alpha

def optical_mag(sfr, mstar, band, z, params):
    """
    Return the predicted optical magnitude given the stellar mass and SFR. 
    Calculated using an ansatz with best-fit parameters calibrated against 
    the Guo et al. catalogue.
    """
    # Figure out which band to use
    if band in params['opt_bands']:
        i = params['opt_bands'].index(band)
    else:
        raise KeyError("Band '%s' not recognised; available bands are: %s" % \
                       (band, params['opt_bands']))
    
    # Ansatz, roughly taking into account 2 sources of stellar light: star 
    # formation (SFR as proxy) and older stars (via stellar mass)
    p = params
    mag = p['opt_mstar_amp'] * ( p['opt_mstar_c'] \
                                + (mstar/1e9)**p['opt_mstar_beta'] ) \
        + p['opt_cross_amp'][i] * (mstar/1e9)**p['opt_cross_beta'] \
                                * sfr**p['opt_cross_gamma'] \
        - p['opt_offset'][i]
    return mag


def pdf_optical_mag(mag, sfr, mstar, band, z, params):
    """
    Intrinsic optical magnitude pdf, conditioned on Mstar and SFR: 
        p(mag_X | M_*, SFR, z). 
    Assumed to be lognormal, with scatter measured from Guo et al. simulations.
    """
    # Figure out which band to use
    if band in params['opt_bands']:
        i = params['opt_bands'].index(band)
    else:
        raise KeyError("Band '%s' not recognised; available bands are: %s" % \
                       (band, params['opt_bands']))
    
    # Central value (mu), and mean and standard deviation of residual
    mu = optical_mag(sfr, mstar, band, z=z, params=params)
    mean = params['opt_pdf_mean'][i]
    sigma = params['opt_pdf_sigma'][i]
    
    # Return shifted log-normal pdf (handle negative arguments)
    #u = 1. - mag + mu # FIXME: Should this be +/-mu?
    u_mean = np.exp( mean + 0.5*sigma**2. ) # Mean of shifted log-normal
    u = mu + u_mean - mag # Linear shift 
    idxs = np.where(u > 0.)
    pdf = np.zeros(u.shape)
    pdf[idxs] = np.exp(-0.5 * ((np.log(u[idxs]) - mean) / sigma)**2.) \
                / (np.sqrt(2.*np.pi) * u[idxs] * sigma)
    return pdf


def pdf_optical_mag_atten(mag, sfr, mstar, band, z, params):
    """
    Dust-attenuated optical magnitude pdf, conditioned on Mstar and SFR: 
        p(mag_X | M_*, SFR, z). 
    This is an analytic marginalisation of the dust model over the lognormal 
    intrinsic optical magnitude pdf.
    """
    # Figure out which band to use
    if band in params['opt_bands']:
        i = params['opt_bands'].index(band)
    else:
        raise KeyError("Band '%s' not recognised; available bands are: %s" % \
                       (band, params['opt_bands']))
    
    # Central value (mu), and mean and standard deviation of residual, for the
    # intrinsic optical magnitude pdf
    mu = optical_mag(sfr, mstar, band, z=z, params=params)
    mean = params['opt_pdf_mean'][i]
    sigma = params['opt_pdf_sigma'][i]
    
    # Terms in analytically-marginalised pdf
    u_mean = np.exp(mean + 0.5*sigma**2.) # shifted mean of log-normal
    dm0 = 1.086 * tau_extinction(0., mstar, band, z, params) # theta=0
    dmpi2 = 1.086 * tau_extinction(0.5*np.pi, mstar, band, z, params) # th=pi/2
    
    # Sanitise erf arguments so that x +ve, i.e. take max(x, 0)
    x0 = mu + dm0 + u_mean - mag
    xpi2 = mu + dmpi2 + u_mean - mag
    # Insensitive to 1e-4 even for quite large values of sigma
    x0[np.where(x0 < 1e-4)] = 1e-4
    xpi2[np.where(xpi2 < 1e-4)] = 1e-4
    
    y0 = (np.log(x0) - mean) / (np.sqrt(2.) * sigma)
    ypi2 = (np.log(xpi2) - mean) / (np.sqrt(2.) * sigma)
    
    # Construct pdf, p(m_int | M*, SFR)
    pdf = 0.5 * (erf(ypi2) - erf(y0)) / (dmpi2 - dm0)
    return pdf
    

def optical_mag_fn(hm, mag, band, z, params):
    """
    Number density per unit optical magnitude, in a given band.
    """
    mstar = np.logspace(params['mass_mstar_min'], params['mass_mstar_max'],
                        params['nsamp_mstar'])
    sfr = np.logspace(params['sfr_min'], params['sfr_max'], params['nsamp_sfr'])
    
    # Calculate passive fraction and stellar mass function
    fpass = f_passive(mstar, z, params=params)
    dndlogms = stellar_mass_fn(hm, mstar, z, params=params)
    
    # Loop over magnitude values
    n_mag_sfms = []; n_mag_pass = []
    for m in mag:
        # Evaluate p(mag | SFR, M*) . p(SFR | M*) n(M*) and integrate over M*
        n_sfms = [scipy.integrate.simps(
                    (1. - fpass) * dndlogms 
                    * pdf_sfr_sfms(_sfr, mstar, z, params=params)
                    * pdf_optical_mag(m, _sfr, mstar, band, z=z, params=params),
                  np.log(mstar) ) for _sfr in sfr]
        n_pass = [scipy.integrate.simps(
                    fpass * dndlogms 
                    * pdf_sfr_passive(_sfr, mstar, z, params=params)
                    * pdf_optical_mag(m, _sfr, mstar, band, z=z, params=params),
                  np.log(mstar) ) for _sfr in sfr]
        
        # Integrate over SFR to get n(mag)
        n_mag_sfms.append( scipy.integrate.simps(n_sfms, sfr) )
        n_mag_pass.append( scipy.integrate.simps(n_pass, sfr) )
    
    # Return total function (dn/dmag) ~ Mpc^-3 mag^-1
    return np.array(n_mag_sfms), np.array(n_mag_pass)

"""
def optical_mag_fn_dust(hm, obsmag, mag, band, z, params,
                         include_intrinsic=False):
    " ""
    Number density per unit optical magnitude, in a given band, with intrinsic 
    dust attenuation marginalised.
    OBSOLETE?
    " ""
    # Get dust-uncorrected number density and interpolate
    n_mag_sfms, n_mag_pass = optical_mag_fn(hm, mag, band, z=z, params=params)
    nsfms = scipy.interpolate.interp1d(mag, n_mag_sfms, kind='linear', 
                               bounds_error=False, fill_value=0.)
    npass = scipy.interpolate.interp1d(mag, n_mag_pass, kind='linear', 
                               bounds_error=False, fill_value=0.)
    
    # Integrate over dust attenuation
    dm = np.concatenate(([0.,], np.logspace(-6., np.log10(3.), 1e4)))
    n_mag_sfms_dust = []; n_mag_pass_dust = []
    for omag in obsmag:
        m = omag - dm
        pdf = pdf_optical_dust_atten(omag, m, z=z, params=params)
        n_mag_sfms_dust.append( -scipy.integrate.trapz((nsfms(m)*pdf), m) )
        n_mag_pass_dust.append( -scipy.integrate.trapz((npass(m)*pdf), m) )
    
    # Return total function (dn/dmag) ~ Mpc^-3 mag^-1
    if include_intrinsic:
        return np.array(n_mag_sfms_dust), np.array(n_mag_pass_dust), \
               np.array(n_mag_sfms), np.array(n_mag_pass)
    else:
        return np.array(n_mag_sfms_dust), np.array(n_mag_pass_dust)
"""

def optical_mag_fn_atten(hm, mag, band, z, params):
    """
    Number density per unit observed (extincted) optical magnitude, in a given 
    band. Uses an analytic marginalisation to reduce the number of integrals.
    """
    mstar = np.logspace(params['mass_mstar_min'], params['mass_mstar_max'],
                        params['nsamp_mstar'])
    sfr = np.logspace(params['sfr_min'], params['sfr_max'], params['nsamp_sfr'])
    
    # Calculate passive fraction and stellar mass function
    fpass = f_passive(mstar, z, params=params)
    dndlogms = stellar_mass_fn(hm, mstar, z, params=params)
    
    # Loop over magnitude values
    n_mag_sfms = []; n_mag_pass = []
    for m in mag:
        # Evaluate p(mag | SFR, M*) . p(SFR | M*) n(M*) and integrate over M*
        n_sfms = [scipy.integrate.simps(
                    (1. - fpass) * dndlogms 
                    * pdf_sfr_sfms(_sfr, mstar, z, params=params)
                    * pdf_optical_mag_atten(m, _sfr, mstar, band, z, params),
                  np.log(mstar) ) for _sfr in sfr]
        n_pass = [scipy.integrate.simps(
                    fpass * dndlogms 
                    * pdf_sfr_passive(_sfr, mstar, z, params=params)
                    * pdf_optical_mag_atten(m, _sfr, mstar, band, z, params),
                  np.log(mstar) ) for _sfr in sfr]
        
        # Integrate over SFR to get n(mag)
        n_mag_sfms.append( scipy.integrate.simps(n_sfms, sfr) )
        n_mag_pass.append( scipy.integrate.simps(n_pass, sfr) )
    
    # Return total function (dn/dmag) ~ Mpc^-3 mag^-1
    return np.array(n_mag_sfms), np.array(n_mag_pass)
 
"""
def optical_mag_fn_extinction(hm, mag, band, z, params):
    " ""
    Number density per unit observed (extincted) optical magnitude, in a given 
    band.
    " ""
    mstar = np.logspace(params['mass_mstar_min'], params['mass_mstar_max'],
                        100) #params['nsamp_mstar']) # FIXME
    sfr = np.logspace(params['sfr_min'], params['sfr_max'], params['nsamp_sfr'])
    
    # Calculate passive fraction and stellar mass function
    fpass = f_passive(mstar, z, params=params)
    dndlogms = stellar_mass_fn(hm, mstar, z, params=params)
    
    # Loop over stellar mass and calculate integrand for stellar mass for each 
    # value of observed magntiude, 'mag'
    grid_sfms = []; grid_pass = []
    for _mstar in mstar:
        
        print _mstar
        
        # Get m_int integration limits (factor of 1.086 comes from conversion 
        # of exp(-tau) -> delta mag).
        dm_max = 1.086 * tau_extinction(1., _mstar, band, z, params)
        dm_min = 1.086 * tau_extinction(0., _mstar, band, z, params)
        dm = np.linspace(dm_max, dm_min, 500) # FIXME: resolution
        
        # Choose a wide enough range to get all viable m_int
        # FIXME: Check this
        m_int = np.linspace(np.min(mag) - dm_max, np.max(mag) - dm_min, 500)
        
        # Integrate over SFR for each m_int, to get p(m_int | M_*)
        p_mint_sfms = scipy.interpolate.interp1d( m_int,
                          [scipy.integrate.simps( 
                               pdf_sfr_sfms(sfr, _mstar, z, params)
                             * pdf_optical_mag(m, sfr, _mstar, band, z, params),
                           sfr) for m in m_int],
                      kind='linear' )
        
        #p_mint_pass = scipy.interpolate.interp1d( m_int,
        #                  [scipy.integrate.simps( 
        #                       pdf_sfr_passive(sfr, _mstar, z, params)
        #                     * pdf_optical_mag(m, sfr, _mstar, band, z, params),
        #                   sfr) for m in m_int],
        #              kind='linear' )
        
        # Integrate over m_int (weighted by uniform pdf) for each m_obs value
        grid_sfms.append( [  scipy.integrate.simps(p_mint_sfms(m - dm), m - dm) 
                              / (dm_max - dm_min)
                           for m in mag] )
        #grid_pass.append( [  scipy.integrate.simps(p_mint_pass(m - dm), m - dm) 
        #                      / (dm_max - dm_min)
        #                   for m in mag] )
    
    # Make into arrays so we can
    grid_sfms = np.array(grid_sfms)
    #grid_pass = np.array(grid_pass)
    
    # Integrate over M* for SFMS and passive galaxies
    dndmobs_sfms = [scipy.integrate.simps(
                        grid_sfms[:,i] * (1. - fpass) * dndlogms,
                        np.log(mstar)) 
                    for i in range(len(mag))]
    #dndmobs_pass = [scipy.integrate.simps(
    #                    grid_pass[:,i] * fpass * dndlogms,
    #                    np.log(mstar))
    #                for i in range(len(mag))]
    
    # Return total function (dn/dmag) ~ Mpc^-3 mag^-1
    return np.array(dndmobs_sfms) #, np.array(dndmobs_pass)

def optical_mag_fn_dust_broken(hm, obsmag, mag, band, z, params,
                        include_intrinsic=False):
    " ""
    Number density per unit optical magnitude, in a given band, with intrinsic 
    dust attenuation marginalised. # FIXME: Doesn't work for some reason!
    " ""
    # Get dust-uncorrected number density and interpolate
    n_mag_sfms, n_mag_pass = optical_mag_fn(hm, mag, band, z=z, params=params)
    interp_sfms = scipy.interpolate.interp1d(mag, np.log(n_mag_sfms), 
                               kind='linear', bounds_error=False, fill_value=0.)
    interp_pass = scipy.interpolate.interp1d(mag, np.log(n_mag_pass), 
                               kind='linear', bounds_error=False, fill_value=0.)
    n_sfms = lambda mag: np.exp(interp_sfms(mag)) # Convert back from log space
    n_pass = lambda mag: np.exp(interp_pass(mag))
    
    # Integrate over dust attenuation to convert intrinsic -> observed mag.
    n_mag_sfms_dust = []; n_mag_pass_dust = []
    for omag in obsmag:
        dm = np.concatenate(([0.,], 
                   np.logspace(-6., np.log10(3.), 1e4))) # FIXME
        m = (omag - dm)
        pdf_dust = pdf_optical_dust_atten(omag, m, z=z, params=params)
        
        #P.plot(m, n_sfms(m), 'b-', lw=1.8)
        #P.plot(m, pdf_dust, 'r-', lw=1.8)
        #P.plot(m, n_sfms(m) * pdf_dust, 'k-', lw=1.8)
        
        print "norm =", scipy.integrate.trapz(pdf_dust, m)
        
        n_mag_sfms_dust.append( scipy.integrate.trapz(
                                   n_sfms(m) * pdf_dust, m) )
        n_mag_pass_dust.append( scipy.integrate.trapz(
                                   n_pass(m) * pdf_dust, m) )
    
    #P.yscale('log')
    #P.show()
    #exit()
    
    # Return total function (dn/dmag) ~ Mpc^-3 mag^-1
    if include_intrinsic:
        return np.array(n_mag_sfms_dust), np.array(n_mag_pass_dust), \
               np.array(n_mag_sfms), np.array(n_mag_pass)
    else:
        return np.array(n_mag_sfms_dust), np.array(n_mag_pass_dust)
"""
#-------------------------------------------------------------------------------
# Luminosity functions from other sources
#-------------------------------------------------------------------------------

def dndlogL_sfradio(L):
    """
    Radio (1.4 GHz) luminosity of star-forming galaxies per channel bandwidth 
    (Hz), from Sect. 5.3 of Yun et al. [astro-ph/0102154].
    """
    nstar = 3.2e-4 # Mpc^-3 mag^-1
    nstar *= 2.5/np.log(10.) # convert from mag^-1 to logL
    Lstar = 2.1e22 * 1e7 # erg/s/Hz
    alpha = -0.633
    x = L / Lstar
    return nstar * x**alpha * np.exp(-x)


def dndlogL_sbradio(L):
    """
    Radio (1.4 GHz) luminosity of starburst galaxies per channel bandwidth 
    (Hz), from Sect. 5.3 of Yun et al. [astro-ph/0102154].
    """
    nstar = 8.3e-6 # Mpc^-3 mag^-1
    nstar *= 2.5/np.log(10.) # convert from mag^-1 to logL
    Lstar = 1.4e23 * 1e7 # erg/s/Hz
    alpha = -0.63
    x = L / Lstar
    return nstar * x**alpha * np.exp(-x)


def dndlogL_halpha(L, type='geach'):
    """
    From Geach (2010). L ~ erg/s.
    """
    if type == 'geach':
        # From Geach et al. (2010)
        nstar = 10.**-2.8 # Mpc^-3
        Lstar = 1e42 # erg/s/Hz
        alpha = -1.35 + 1. # +1 converts from phi(L)dL -> (dn/dlogL).dlogL
    else:
        # From Pozzetti et al. (2016)
        nstar = 10.**-2.8 # Mpc^-3
        Lstar = 10**41.5 # erg/s
        alpha = -1.35 + 1.
    
    # Gallego 1995
    #nstar = 10.**-2.78
    #Lstar = 10.**41.47
    #alpha = -1.3 + 1.
    x = L / Lstar
    return nstar * x**alpha * np.exp(-x)

def dndlogL_24um(L):
    """
    xxx
    """
    # FIXME
    nstar = 10.**-2.8 # Mpc^-3
    Lstar = 1e42 # erg/s/Hz
    alpha = -1.35
    x = L / Lstar
    return nstar * x**alpha * np.exp(-x)

