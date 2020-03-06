# This file specifies the pipeline configuration for the current pipeline run.
# You should review these settings before processing any images - some of the default
# values will probably not be appropriate.

import os

# path of the pipeline run
PIPE_RUN_PATH = os.path.dirname(os.path.realpath(__file__))

# Images settings
IMAGE_FILES = [
    # insert images path here or regex, or both
]

# Selavy catalogue files: if passed, skip source find stage
SELAVY_FILES = [
    # insert Selavy file paths here or regex, or both
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
MAX_BACKWARDS_MONITOR_IMAGES = 0

# The position uncertainty is in reality a combination of the fitting errors and the
# astrometric uncertainty of the image/survey/instrument.
# These two uncertainties are combined in quadrature.
# These two parameters are the astrometric uncertainty in ra/dec and they may be different
ASTROMETRIC_UNCERTAINTY_RA = 5. / 3600.  # Degrees
ASTROMETRIC_UNCERTAINTY_DEC = ASTROMETRIC_UNCERTAINTY_RA  # Degrees

###
# OPTIONS THAT CONTROL THE SOURCE ASSOCIATION
###
# Enbale/Disble source association, set false to turn off association stage
ASSOCIATION_METHOD = 'basic'   # 'basic' or 'advanced'

# options that apply to basic
ASSOCIATION_RADIUS = 5. # units is arcsec, basic only

#options that apply to advanced
ASSOCIATION_DE_RUITER_RADIUS = 5.68
ASSOCIATION_BEAMWIDTH_LIMIT = 1.0

# Default survey.
# Used by the website for analysis plots.
DEFAULT_SURVEY =  None # 'NVSS'

# Minimum error to apply to all flux measurements. The actual value used will be the measured/
# reported value or this value, whichever is greater.
# This is a fraction, 0 = No minimum error
MIN_ERR_FLUX = 0 #percent 0.05 is 5%
