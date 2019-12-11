# This file specifies the pipeline configuration for the current dataset.
# You should review these settings before processing any images - some of the default
# values will probably not be appropriate.

import os

# path of the dataset
DATASET_PATH = os.path.dirname(os.path.realpath(__file__))

# Images settings
IMAGE_FILES = [
    # insert images path here or regex, or both
]

# Selavy catalog files: if passed, skip source find stage
SELAVY_FILES = [
    # insert Selavy file paths here or regex, or both
]

# source finder used for this dataset
SOURCE_FINDER = 'aegean'

###
# OPTIONS THAT ARE PASSED TO AEGEAN FOR SOURCE FINDING AND PRIORIZED FITTING
###
# Max components (sources) in a single island for Aegean (default 3).
# If an island has more components then Aegean will return estimates for all
# of them instead of fitting Gaussians.
AEGEAN_MAXSUMMITS = 5

# Source extraction clipping level for Aegean (in sigmas, default 5).
# Aegean will only find sources in islands with at least one pixel
# above this clipping level.
AEGEAN_SEEDCLIP = 5

# Island filling clipping level for Aegean (in sigmas, default 4).
# Aegean fills out islands with pixels above this clipping level
# and uses those islands for Gaussian fitting.
AEGEAN_FLOODCLIP = 4

# Aegean can find both positive and negative sources. By default we only care about
# the positive ones.
AEGEAN_NONEGATIVE = True
AEGEAN_NOPOSITIVE = False

# If this is true, then the follwing files will be looked for and included
# in the source finding stage:
# <image>_bkg.fits - background map
# <image>_rms.fits - noise map
# <image>.mim      - masking region
# <image>_psf.fits - psf map
# <image>_comp.fits - catalog.

# If <image>_comp.fits is found then no source finding will be done,
# the catalog will just be imported.
# The _bkg/_rms files are still required in this case.
AEGEAN_LOOK_FOR_AUX_FILES = True

# Use a constant background RMS for source finding instead of Aegean's
# variable background feature. Defaults to False if not specified.
CONSTANT_RMS = False

# An average RMS of an image is calculated when it is imported.
# This can be slow, and sometimes meaningless.
# This parameter will cause the imported rms to be set to zero if it is false.
CALCULATE_IMAGE_RMS_ON_IMPORT = False

###
# SOURCE MONITORING OPTIONS (ALSO DONE IN AEGEAN)
###
# Source monitoring can be done both forward and backward in 'time'.
# Monitoring backward means re-opening files that were previously processed and can be slow.
MONITOR = True
MAX_BACKWARDS_MONITOR_IMAGES = 0

###
# OPTIONS THAT CONTROL THE SOURCE ASSOCIATION, ASTROMETRY AND GAIN CORRECTIONS
###
# Enbale/Disble source association, set false to turn off association stage
ASSOCIATE = True
ASSOCIATION_RADIUS = 1.

# Default survey.
# Used by the website for analysis plots.
DEFAULT_SURVEY =  None # 'NVSS'

# The position uncertainty is in reality a combination of the fitting errors and the
# astrometric uncertainty of the image/survey/instrument.
# These two uncertainties are combined in quadrature.
# These two parameters are the astrometric uncertainty in ra/dec and they may be different
ASTROMETRIC_UNCERTAINTY_RA = 5. / 3600.  # Degrees
ASTROMETRIC_UNCERTAINTY_DEC = ASTROMETRIC_UNCERTAINTY_RA  # Degrees

# The reference catalog for doing astrometry and gain corrections.
# If this is None then no astrometry/gain corretion is done.
POSITION_REFERENCE_CATALOG = DEFAULT_SURVEY

# Sources with a SNR greater than this value will be matched to the reference catalog
# and the cross-matched sources will be used to calculate the astrometry and gain models
POSITION_REFERENCE_SNR_CUT = 10

# Cross matching radius for matching sources to the reference catalog for the purpose
# of doing astrometry and gain models
# Units are degrees
POSITION_REFERENCE_MATCHING_RADIUS = 0.1  # Degrees

# Search radius used for source association (degrees).
# This is used to associate sources between epochs, and also to associate sources with the reference catalogue.
# If None, the image beam size is used.
# Units are degrees
SOURCE_ASSOCIATION_SEARCH_RADIUS = None #degrees, or None to use the beam size

# When sources are cross-matched with the above radius, a likelyhood ratio is calculated
# only associates with a probability greater than this value will be accepted.
SOURCE_ASSOCIATION_SEARCH_PROBABILITY = 0.95

# Normally the prior for calculating a cross-match probability is based on the source density
# of the two surveys. This option allows it to be set to some pre-determined value.
# A forced prior is faster, but less accurate than the calculated one.
# A probability 0 < prob < 1
FORCED_PRIOR = 0.95

# Minimum error to apply to all flux measurements. The actual value used will be the measured/
# reported value or this value, whichever is greater.
# This is a fraction, 0 = No minimum error
MIN_ERR_FLUX = 0 #percent 0.05 is 5%

# Prefix for creating source names.
SOURCE_NAME_PREFIX = 'PIPELINE'

# This will turn on the gain correction stage.
# If true, a position dependent gain will be calculated by comparing the sources extracted
# from each image to the DEFAULT_SURVEY (defined above).
# This is NOT primary beam correction (listed below).
DOGAIN = False

# Sources smaller than this are considered point sources, otherwise extended
MAX_POINT_SOURCE_SIZE_BEAMS = 2.0

# Primary beam correction is possible.
# Set this to true to turn it on.
PB_CORRECTION = False

# If primary image mode is true, only sources detected in the primary image in
# each cube will be added to the source list. The "primary image" is currently
# defined as the image with frequency == PRIMARY_IMAGE_FREQUENCY and polarisation == 'I'.
# If primary image mode is false then sources detected in any image will be added.
# This setting has no effect if the input FITS files only contain one image.
PRIMARY_IMAGE_MODE = True

# The frequency of primary images (integer MHz).
# Also used by the website for selecting the default band.
# This is required if PRIMARY_IMAGE_MODE is True
PRIMARY_IMAGE_FREQUENCY = 154

# Size of box for taking peak pixel (pixels)
PEAK_PIXEL_BOX_SIZE = 3

# Tolerance for peak flux check. If the peak flux reported by the source finder is not
# within this tolerance of the peak pixel the measurement is considered invalid.
# NOTE: This valid/notvalid is no longer implemented.
PEAK_FLUX_TOLERANCE = 0.20 #percentage

# Width of border of unused area of image at the edge (pixels)
IMAGE_UNUSED_AREA_WIDTH_PIXELS = 10

###
# THINGS I'M NOT 100% SURE HOW TO DESCRIBE
###
ENTIRE_IMAGE = True# why this??

###
# The following are currently not used by the pipeline
###
# # Minimum peak flux and SNR for sources to be considered in image gain calculation
# IMAGE_GAIN_MIN_FLUX = 40 #mJy
# IMAGE_GAIN_MIN_SNR = 10

# # Source that have peak/total(int) fluxes that are significantly different
# # are probably resolved and may not be a good choice for image gain.
# # This parameter sets the maximum ratio for peak/total for a source to be included.
# IMAGE_GAIN_PEAK_TO_TOTAL_TOLERANCE = 1

# # For snapshot images you want to give higher weight sources closer to the center
# # of the image and less weight to those further from the center. In that case this
# # parameter should be 2.
# # For mosaic images there is no such position dependent weighting that needs to be applied
# # so this parameter should be 0 in that case.
# IMAGE_GAIN_DISTANCE_WEIGHT_EXPONENT = 0

# # Only sources within this distance of the center of the image will be used
# # in the image gain stage.
# IMAGE_GAIN_RADIUS = 20 #Degrees

