"""
Translators to map the table column names in the input files
into the required column names in our db.
The flux/ang scale needs to be the multiplicative factor
that converts the input flux into mJy and a/b into arcsec.
"""

import numpy as np


tr_aegean = {
    'prefix': 'IM',
    'ra': 'ra',
    'err_ra': 'er_ra',
    'dec': 'dec',
    'err_dec': 'err_dec',
    'pos_err_ang_scale': 1,
    'peak_flux': 'peak_flux',
    'err_peak_flux': 'err_peak_flux',
    'total_flux': 'int_flux',
    'err_total_flux': 'err_int_flux',
    'flux_scale': 1e3,
    'bmaj': 'a',
    'bmin': 'b',
    'ang_scale': 3600,
    'pa': 'pa',
    'freq': 999  # some clearly wrong number
    }
"""
The translator dictionary for a Agean catalogue input. Not complete.
"""

tr_mwacs = {
    'prefix': 'MWACS',
    'ra': 'RAJ2000',
    'err_ra': 'e_RAJ2000',
    'dec': 'DEJ2000',
    'err_dec': 'e_DEJ2000',
    'pos_err_ang_scale': 1,
    'peak_flux': 'S180',
    'err_peak_flux': 'e_S180',
    'total_flux': 'S180',
    'err_total_flux': 'e_S180',
    'flux_scale': 1e3,
    'bmaj': 'MajAxis',
    'bmin': 'MinAxis',
    'ang_scale': 60,
    'pa': 'PABeam',
    'freq': 180  # MHz
    }
"""
The translator dictionary for a MWACS catalogue input. Not complete.
"""

tr_gleam = {
    'prefix': 'MWA',
    'ra': 'RAJ2000',
    'err_ra': 'err_RAJ2000',
    'dec': 'DEJ2000',
    'err_dec': 'err_DEJ2000',
    'pos_err_ang_scale': 1,
    'peak_flux': 'peak_flux_wide',
    'err_peak_flux': 'err_peak_flux_wide',
    'total_flux': 'int_flux_wide',
    'err_total_flux': 'err_int_flux_wide',
    'flux_scale': 1e3, #Jy->mJy
    'bmaj': 'a_wide',
    'bmin': 'b_wide',
    'ang_scale': 1./3600, #asec -> deg
    'pa': 'pa_wide',
    'freq': 200  #MHz (central for deep image)
    }
"""
The translator dictionary for a GLEAM catalogue input. Not complete.
"""

tr_sumss = {
    'prefix':'SUMSS',
    'ra': '_RAJ2000',
    'err_ra': 'e_RAJ2000',
    'dec': '_DEJ2000',
    'err_dec': 'e_DEJ2000',
    'pos_err_ang_scale': 1./3600,
    'peak_flux': 'Sp',
    'err_peak_flux': 'e_Sp',
    'total_flux': 'St',
    'err_total_flux': 'e_St',
    'flux_scale': 1,  # mJy
    'bmaj': 'MajAxis',
    'bmin': 'MinAxis',
    'ang_scale': 1./3600,  # asec -> deg
    'pa': 'PA',
    'freq': 843  # MHz
    }
"""
The translator dictionary for a SUMSS catalogue input. Not complete.
"""

tr_nvss = {
    'prefix':'NVSS',
    'ra': '_RAJ2000',
    'err_ra': 'e_RAJ2000',
    'dec': '_DEJ2000',
    'err_dec': 'e_DEJ2000',
    'pos_err_ang_scale': 1./3600,
    'peak_flux': 'S1.4',
    'err_peak_flux': 'e_S1.4',
    'total_flux': 'S1.4',
    'err_total_flux': 'e_S1.4',
    'flux_scale': 1, #mJy
    'bmaj': 'MajAxis',
    'bmin': 'MinAxis',
    'ang_scale': 1./3600, #asec -> deg
    'pa': 'PA',
    'freq': 1400  # MHz
    }
"""
The translator dictionary for a NVSS catalogue input. Not complete.
"""

# translator for reading data from the Selavy catalogue
# Name -> name of the Source Model fields (see pipeline/models.py)
# Dtype -> the data type as define in the field declaration
tr_selavy = {
    "island_id": {'name': "island_id", 'dtype': np.dtype(str)},
    "component_id": {'name': "component_id", 'dtype': np.dtype(str)},
    "rms_image": {'name': "local_rms", 'dtype': np.dtype(float)},
    "ra_deg_cont": {'name': "ra", 'dtype': np.dtype(float)},
    "ra_err": {'name': "ra_err", 'dtype': np.dtype(float)},
    "dec_deg_cont": {'name': "dec", 'dtype': np.dtype(float)},
    "dec_err": {'name': "dec_err", 'dtype': np.dtype(float)},
    "flux_peak": {'name': "flux_peak", 'dtype': np.dtype(float)},
    "flux_peak_err": {'name': "flux_peak_err", 'dtype': np.dtype(float)},
    "flux_int": {'name': "flux_int", 'dtype': np.dtype(float)},
    "flux_int_err": {'name': "flux_int_err", 'dtype': np.dtype(float)},
    "maj_axis": {'name': "bmaj", 'dtype': np.dtype(float)},
    "maj_axis_err": {'name': "err_bmaj", 'dtype': np.dtype(float)},
    "min_axis": {'name': "bmin", 'dtype': np.dtype(float)},
    "min_axis_err": {'name': "err_bmin", 'dtype': np.dtype(float)},
    "pos_ang": {'name': "pa", 'dtype': np.dtype(float)},
    "pos_ang_err": {'name': "err_pa", 'dtype': np.dtype(float)},
    "maj_axis_deconv": {'name': "psf_bmaj", 'dtype': np.dtype(float)},
    "min_axis_deconv": {'name': "psf_bmin", 'dtype': np.dtype(float)},
    "pos_ang_deconv": {'name': "psf_pa", 'dtype': np.dtype(float)},
    "flag_c4": {'name': "flag_c4", 'dtype': np.dtype(bool)},
    "chi_squared_fit": {'name': "chi_squared_fit", 'dtype': np.dtype(float)},
    "spectral_index": {'name': "spectral_index", 'dtype': np.dtype(float)},
    "spectral_index_from_TT": {'name': "spectral_index_from_TT", 'dtype': np.dtype(bool)},
    "has_siblings": {'name': "has_siblings", 'dtype': np.dtype(bool)},
    "rms_image": {'name': "local_rms", 'dtype': np.dtype(float)},
}
"""
The translator dictionary for a Selavy catalogue input.
"""

translators = {
    'MWACS': tr_mwacs,
    'AEGEAN': tr_aegean,
    'GLEAM': tr_gleam,
    'SUMSS': tr_sumss,
    'NVSS': tr_nvss,
    'SELAVY': tr_selavy,
    'DEFAULT': tr_aegean,
}
"""
Dictionary containing all the translators defined in this module.
"""
