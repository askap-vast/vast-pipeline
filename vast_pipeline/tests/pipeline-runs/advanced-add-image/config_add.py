# This file specifies the pipeline configuration for the current pipeline run.
# You should review these settings before processing any images - some of the default
# values will probably not be appropriate.

import os

# path of the pipeline run
PIPE_RUN_PATH = os.path.dirname(os.path.realpath(__file__))
data_path = './vast_pipeline/tests/regression-data'
epochs = ['01', '01', '02', '03x', '05x', '06x']
fields = ['+00']
fields.extend(['-06' for _ in range(5)])

# Images settings
# NOTE: all the paths !!!MUST!!! match with each other, e.g.
# IMAGE_FILES[0] image matches SELAVY_FILES[0] file
image_path = 'COMBINED/STOKESI_IMAGES'
IMAGE_FILES = [
    # insert images file path(s) here
    os.path.join(
        data_path, 
        'EPOCH' + epoch, 
        image_path, 
        'VAST_2118' + field + 'A.EPOCH' + epoch + '.I.fits'
    ) for epoch, field in zip(epochs, fields)
]

# Selavy catalogue files
selavy_path = 'COMBINED/STOKESI_SELAVY'
SELAVY_FILES = [
    # insert Selavy file path(s) here
    os.path.join(
        data_path, 
        'EPOCH' + epoch, 
        selavy_path, 
        'VAST_2118' + field + 'A.EPOCH' + epoch + '.I.selavy.components.txt'
    ) for epoch, field in zip(epochs, fields)
]

# Noise or RMS files
maps_path = 'COMBINED/STOKESI_RMSMAPS'
NOISE_FILES = [
    # insert RMS file path(s) here
    os.path.join(
        data_path, 
        'EPOCH' + epoch, 
        maps_path, 
        'VAST_2118' + field + 'A.EPOCH' + epoch + '.I_rms.fits'
    ) for epoch, field in zip(epochs, fields)
]

# background map files
BACKGROUND_FILES = [
    # insert background map file path(s) here
    os.path.join(
        data_path, 
        'EPOCH' + epoch, 
        maps_path, 
        'VAST_2118' + field + 'A.EPOCH' + epoch + '.I_bkg.fits'
    ) for epoch, field in zip(epochs, fields)
]

###
# SOURCE FINDER OPTIONS
###
# source finder used for this pipeline run
SOURCE_FINDER = 'selavy'

###
# SOURCE MONITORING OPTIONS
###
# Source monitoring can be done both forward and backward in 'time'.
# Monitoring backward means re-opening files that were previously processed and can be slow.
MONITOR = False
# MONITOR_MIN_SIGMA defines the minimum SNR ratio a source has to be if it was placed in the
# area of minimum rms in the image from which it is to be extracted from. If lower than this
# value it is skipped
MONITOR_MIN_SIGMA = 3.0
# MONITOR_EDGE_BUFFER_SCALE is a multiplicative scaling factor to the buffer size of the
# forced photometry from the image edge.
MONITOR_EDGE_BUFFER_SCALE = 1.2
# MONITOR_CLUSTER_THRESHOLD represents the cluster_threshold parameter used in the forced
# extraction. If unsure leave as default.
MONITOR_CLUSTER_THRESHOLD = 3.0
# MONITOR_ALLOW_NAN governs whether a source is attempted to be fit even if there are NaN's
# present in the rms or background maps.
MONITOR_ALLOW_NAN = False

# The position uncertainty is in reality a combination of the fitting errors and the
# astrometric uncertainty of the image/survey/instrument.
# These two uncertainties are combined in quadrature.
# These two parameters are the astrometric uncertainty in ra/dec and they may be different
ASTROMETRIC_UNCERTAINTY_RA = 1 # arcsec
ASTROMETRIC_UNCERTAINTY_DEC = 1  # arcsec

###
# OPTIONS THAT CONTROL THE SOURCE ASSOCIATION
###
ASSOCIATION_METHOD = 'advanced' # 'basic', 'advanced' or 'deruiter'

# options that apply to basic and advanced association
ASSOCIATION_RADIUS = 10.0 # arcsec, basic and advanced only

# options that apply to deruiter association
ASSOCIATION_DE_RUITER_RADIUS = 5.68 # unitless, deruiter only
ASSOCIATION_BEAMWIDTH_LIMIT = 1.5   # multiplicative factor, deruiter only

# If ASSOCIATION_PARALLEL is set to 'True' then the input images will be split into
# 'sky region groups' and association run on these groups in parallel and combined at the end.
# Setting to 'True' is best used when you have a large dataset with multiple patches of the sky, 
# for smaller searches of only 3 or below sky regions it is recommened to keep as 'False'.
ASSOCIATION_PARALLEL =  False

# If images have been submitted in epoch dictionaries then an attempt will be made by the pipeline to
# remove duplicate sources. To do this a crossmatch is made between catalgoues to match 'the same'
# measurements from different catalogues. This parameter governs the distance for which a match is made.
# Default is 2.5 arcsec (which is typically 1 pixel in ASKAP images).
ASSOCIATION_EPOCH_DUPLICATE_RADIUS = 2.5  # arcsec

###
# OPTIONS THAT CONTROL THE NEW SOURCE ANALYSIS
###

# controls whether a source is labelled as a new source. The source in question
# must meet the requirement of:
# MIN_NEW_SOURCE_SIGMA > (source_peak_flux / lowest_previous_image_min_rms)
NEW_SOURCE_MIN_SIGMA = 5.0

# Default survey.
# Used by the website for analysis plots.
DEFAULT_SURVEY = None # 'NVSS'

# Minimum error to apply to all flux measurements. The actual value used will be the measured/
# reported value or this value, whichever is greater.
# This is a fraction, 0 = No minimum error
FLUX_PERC_ERROR = 0 #percent 0.05 is 5%

# Replace the selavy errors with
USE_CONDON_ERRORS = True

# Sometimes the local rms for a source is reported as 0 by selavy.
# Choose a value to use for the local rms in these cases
SELAVY_LOCAL_RMS_ZERO_FILL_VALUE = 0.2  # mJy

# Create 'measurements.arrow' and 'measurement_pairs.arrow' files at the end of 
# a successful run
CREATE_MEASUREMENTS_ARROW_FILES = False

# Hide astropy warnings
SUPPRESS_ASTROPY_WARNINGS = True

# Only measurement pairs where the Vs metric exceeds this value are selected for the
# aggregate pair metrics that are stored in Source objects.
SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS = 4.3