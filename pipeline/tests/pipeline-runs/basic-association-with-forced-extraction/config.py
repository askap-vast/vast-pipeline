# This file specifies the pipeline configuration for the current pipeline run.
# You should review these settings before processing any images - some of the default
# values will probably not be appropriate.

import os

# path of the pipeline run
PIPE_RUN_PATH = os.path.dirname(os.path.realpath(__file__))

# Images settings
# NOTE: all the paths !!!MUST!!! match with each other, e.g.
# IMAGE_FILES[0] image matches SELAVY_FILES[0] file
IMAGE_FILES = [
    # insert images file path(s) here
    './pipeline/tests/data/epoch01.fits',
    './pipeline/tests/data/epoch02.fits',
    './pipeline/tests/data/epoch03.fits',
    './pipeline/tests/data/epoch04.fits',
]

# Selavy catalogue files
SELAVY_FILES = [
    # insert Selavy file path(s) here
    './pipeline/tests/data/epoch01.selavy.components.txt',
    './pipeline/tests/data/epoch02.selavy.components.txt',
    './pipeline/tests/data/epoch03.selavy.components.txt',
    './pipeline/tests/data/epoch04.selavy.components.txt',
]

# background map files
BACKGROUND_FILES = [
    # insert background map file path(s) here
    './pipeline/tests/data/epoch01.meanMap.fits',
    './pipeline/tests/data/epoch02.meanMap.fits',
    './pipeline/tests/data/epoch03.meanMap.fits',
    './pipeline/tests/data/epoch04.meanMap.fits',
]

# Noise or RMS files
NOISE_FILES = [
    # insert RMS file path(s) here
    './pipeline/tests/data/epoch01.noiseMap.fits',
    './pipeline/tests/data/epoch02.noiseMap.fits',
    './pipeline/tests/data/epoch03.noiseMap.fits',
    './pipeline/tests/data/epoch04.noiseMap.fits',
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
MONITOR = True
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
ASSOCIATION_METHOD = 'basic' # 'basic', 'advanced' or 'deruiter'

# options that apply to basic and advanced association
ASSOCIATION_RADIUS = 15.0 # arcsec, basic and advanced only

# options that apply to deruiter association
ASSOCIATION_DE_RUITER_RADIUS = 5.68 # unitless, deruiter only
ASSOCIATION_BEAMWIDTH_LIMIT = 1.5   # multiplicative factor, deruiter only

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

# Replace the selavy errors witht
USE_CONDON_ERRORS = True

# Sometimes the local rms for a source is reported as 0 by selavy.
# Choose a value to use for the local rms in these cases
SELAVY_LOCAL_RMS_ZERO_FILL_VALUE = 0.2  # mJy
