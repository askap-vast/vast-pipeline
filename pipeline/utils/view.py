# Functions and variables used in pipeline/views.py

# Defines the float format and scaling for all
# parameters presented in DATATABLES via AJAX call
FLOAT_FIELDS = {
    'ra': {
        'precision': 4,
        'scale': 1,
    },
    'ra_err': {
        'precision': 4,
        'scale': 3600.,
    },
    'uncertainty_ew': {
        'precision': 4,
        'scale': 3600.,
    },
    'dec': {
        'precision': 4,
        'scale': 1,
    },
    'dec_err': {
        'precision': 4,
        'scale': 3600,
    },
    'uncertainty_ns': {
        'precision': 4,
        'scale': 3600.,
    },
    'flux_int': {
        'precision': 3,
        'scale': 1,
    },
    'flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'flux_int_err': {
        'precision': 3,
        'scale': 1,
    },
    'flux_peak_err': {
        'precision': 3,
        'scale': 1,
    },
    'v_int': {
        'precision': 2,
        'scale': 1,
    },
    'eta_int': {
        'precision': 2,
        'scale': 1,
    },
    'v_peak': {
        'precision': 2,
        'scale': 1,
    },
    'eta_peak': {
        'precision': 2,
        'scale': 1,
    },
    'avg_flux_int': {
        'precision': 3,
        'scale': 1,
    },
    'avg_flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'max_flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'rms_median': {
        'precision': 3,
        'scale': 1,
    },
    'rms_min': {
        'precision': 3,
        'scale': 1,
    },
    'rms_max': {
        'precision': 3,
        'scale': 1,
    },
    'new_high_sigma': {
        'precision': 3,
        'scale': 1
    },
    'compactness': {
        'precision': 3,
        'scale': 1,
    },
    'avg_compactness': {
        'precision': 3,
        'scale': 1,
    },
    'n_neighbour_dist': {
        'precision': 2,
        'scale': 60.,
    },
}
