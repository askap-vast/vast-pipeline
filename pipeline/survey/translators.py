# translators to map the table column names in the input files
# into the required column names in our db
# the flux/ang scale needs to be the multiplicative factor
# that converts the input flux into mJy and a/b into arcsec

tr_aegean = {
    'prefix': 'IM',
    'ra': 'ra',
    'err_ra': 'er_ra',
    'dec': 'dec',
    'err_dec': 'err_dec',
    'pos_err_ang_scale': 1,
    'peak_flux': 'peak_flux',
    'err_peak_flux': 'err_peak_flux',
    'flux': 'int_flux',
    'err_flux': 'err_int_flux',
    'flux_scale': 1e3,
    'bmaj': 'a',
    'bmin': 'b',
    'ang_scale': 3600,
    'pa': 'pa',
    'freq': 999  # some clearly wrong number
    }

tr_mwacs = {
    'prefix': 'MWACS',
    'ra': 'RAJ2000',
    'err_ra': 'e_RAJ2000',
    'dec': 'DEJ2000',
    'err_dec': 'e_DEJ2000',
    'pos_err_ang_scale': 1,
    'peak_flux': 'S180',
    'err_peak_flux': 'e_S180',
    'flux': 'S180',
    'err_flux': 'e_S180',
    'flux_scale': 1e3,
    'bmaj': 'MajAxis',
    'bmin': 'MinAxis',
    'ang_scale': 60,
    'pa': 'PABeam',
    'freq': 180  # MHz
    }

tr_gleam = {
    'prefix': 'MWA',
    'ra': 'RAJ2000',
    'err_ra': 'err_RAJ2000',
    'dec': 'DEJ2000',
    'err_dec': 'err_DEJ2000',
    'pos_err_ang_scale': 1,
    'peak_flux': 'peak_flux_wide',
    'err_peak_flux': 'err_peak_flux_wide',
    'flux': 'int_flux_wide',
    'err_flux': 'err_int_flux_wide',
    'flux_scale': 1e3, #Jy->mJy
    'bmaj': 'a_wide',
    'bmin': 'b_wide',
    'ang_scale': 1./3600, #asec -> deg
    'pa': 'pa_wide',
    'freq': 200  #MHz (central for deep image)
    }

tr_sumss = {
    'prefix':'SUMSS',
    'ra': '_RAJ2000',
    'err_ra': 'e_RAJ2000',
    'dec': '_DEJ2000',
    'err_dec': 'e_DEJ2000',
    'pos_err_ang_scale': 1./3600,
    'peak_flux': 'Sp',
    'err_peak_flux': 'e_Sp',
    'flux': 'St',
    'err_flux': 'e_St',
    'flux_scale': 1,  # mJy
    'bmaj': 'MajAxis',
    'bmin': 'MinAxis',
    'ang_scale': 1./3600,  # asec -> deg
    'pa': 'PA',
    'freq': 843  # MHz
    }

tr_nvss = {
    'prefix':'NVSS',
    'ra': '_RAJ2000',
    'err_ra': 'e_RAJ2000',
    'dec': '_DEJ2000',
    'err_dec': 'e_DEJ2000',
    'pos_err_ang_scale': 1./3600,
    'peak_flux': 'S1.4',
    'err_peak_flux': 'e_S1.4',
    'flux': 'S1.4',
    'err_flux': 'e_S1.4',
    'flux_scale': 1, #mJy
    'bmaj': 'MajAxis',
    'bmin': 'MinAxis',
    'ang_scale': 1./3600, #asec -> deg
    'pa': 'PA',
    'freq': 1400  # MHz
    }


translators = {
    'MWACS': tr_mwacs,
    'AEGEAN': tr_aegean,
    'GLEAM': tr_gleam,
    'SUMSS': tr_sumss,
    'NVSS': tr_nvss,
    'DEFAULT': tr_aegean
}
