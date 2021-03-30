# Run Configuration

This page gives an overview of the configuration options available for a pipeline run.

## Default Configuration File
Below is an example of a default `config.py` file. Note that no images or other input files have been provided. The file can be either edited directly or through the editor available on the run detail page.

```python
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
    ]

# Selavy catalogue files
SELAVY_FILES = [
    # insert Selavy file path(s) here
    ]

# Noise or RMS files
NOISE_FILES = [
    # insert RMS file path(s) here
    ]

# background map files
BACKGROUND_FILES = [
    # insert background map file path(s) here
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
ASTROMETRIC_UNCERTAINTY_RA = 1.0 # arcsec
ASTROMETRIC_UNCERTAINTY_DEC = 1.0  # arcsec

###
# OPTIONS THAT CONTROL THE SOURCE ASSOCIATION
###
ASSOCIATION_METHOD = 'basic' # 'basic', 'advanced' or 'deruiter'

# options that apply to basic and advanced association
ASSOCIATION_RADIUS = 10.0 # arcsec, basic and advanced only

# options that apply to deruiter association
ASSOCIATION_DE_RUITER_RADIUS = 5.68 # unitless, deruiter only
ASSOCIATION_BEAMWIDTH_LIMIT = 1.5   # multiplicative factor, deruiter only

# If ASSOCIATION_PARALLEL is set to 'True' then the input images will be split into
# 'sky region groups' and association run on these groups in parallel and combined at the end.
# Setting to 'True' is best used when you have a large dataset with multiple patches of the sky, 
# for smaller searches of only 3 or below sky regions it is recommened to keep as 'False'.
ASSOCIATION_PARALLEL = False

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
FLUX_PERC_ERROR = 0.0 #percent 0.05 is 5%

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
```

## Configuration Options

### Images and Selavy Files
**`IMAGE_FILES`**  
List or Dictionary. The full paths to the image FITS files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types.

=== "Normal mode"

    ```python
    IMAGE_FILES = [
        "/full/path/to/image1.fits", "/full/path/to/image2.fits", "/full/path/to/image3.fits"
    ]
    ```

=== "Epoch mode"

    ```python
    IMAGE_FILES = {
        "epoch01": ["/full/path/to/image1.fits", "/full/path/to/image2.fits"],
        "epoch02": ["/full/path/to/image3.fits"],
    }
    ```

!!! tip
    Use `glob` to easily list a large amount of files. E.g.  
    ```python
    from glob import glob
    ...
    IMAGE_FILES = glob("/full/path/to/image*.fits")
    ```
    This can also be applied to any of the input options below.
    
**`SELAVY_FILES`**  
List or Dictionary. The full paths to the selavy text files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types.

=== "Normal mode"

    ```python
    SELAVY_FILES = [
        "/full/path/to/image1_selavy.txt", "/full/path/to/image2_selavy.txt", "/full/path/to/image3_selavy.txt"
    ]
    ```

=== "Epoch mode"

    ```python
    SELAVY_FILES = {
        "epoch01": ["/full/path/to/image1_selavy.txt", "/full/path/to/image2_selavy.txt"], 
        "epoch02": ["/full/path/to/image3_selavy.txt"],
    }
    ```

**`NOISE_FILES`**  
List or Dictionary. The full paths to the image noise (RMS) FITS files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types.

=== "Normal mode"

    ```python
    NOISE_FILES = [
        "/full/path/to/image1_rms.fits", "/full/path/to/image2_rms.fits", "/full/path/to/image3_rms.fits"
    ]
    ```

=== "Epoch mode"

    ```python
    NOISE_FILES = {
        "epoch01": ["/full/path/to/image1_rms.fits", "/full/path/to/image2_rms.fits"], 
        "epoch02": ["/full/path/to/image3_rms.fits"],
    }
    ```

**`BACKGROUND_FILES`**  
List or Dictionary. The full paths to the image background (mean) FITS files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types. Only required to be defined if `MONITOR` is set to `True`.

=== "Normal mode"

    ```python
    BACKGROUND_FILES = [
        "/full/path/to/image1_bkg.fits", "/full/path/to/image2_bkg.fits", "/full/path/to/image3_bkg.fits"
    ]
    ```

=== "Epoch mode"

    ```python
    BACKGROUND_FILES = {
        "epoch01": ["/full/path/to/image1_bkg.fits", "/full/path/to/image2_bkg.fits"], 
        "epoch02": ["/full/path/to/image3_bkg.fits"],
    }
    ```

### Source Finder Format
**`SOURCE_FINDER`**  
String. Signifies the format of the source finder text file read by the pipeline. Currently only supports `"selavy"`.

!!! warning
    Source finding is not performed by the pipeline and must be completed prior to processing.

### Source Monitoring
**`MONITOR`**  
Boolean. Turns on or off forced extractions for non detections. If set to `True` then `BACKGROUND_IMAGES` must also be defined. Defaults to `False`.

**`MONITOR_MIN_SIGMA`**  
Float. For forced extractions to be performed they must meet a minimum signal-to-noise threshold with respect to the minimum rms value of the respective image. If the proposed forced measurement does not meet the threshold then it is not performed. I.e.

$$
\frac{f_{peak}}{\text{rms}_{image, min}} \geq \small{\text{MONITOR_MIN_SIGMA}}\text{,}
$$

where $f_{peak}$ is the initial detection peak flux measurement of the source in question and $\text{rms}_{image, min}$ is the minimum RMS value of the image where the forced extraction is to take place. Defaults to `3.0`.

**`MONITOR_EDGE_BUFFER_SCALE`**  
Float. Monitor forced extractions are not performed when the location is within 3 beamwidths of the image edge. This parameter scales this distance by the value set, which can help avoid errors when the 3 beamwidth limit is insufficient to avoid extraction failures. Defaults to 1.2.

**`MONITOR_CLUSTER_THRESHOLD`**  
Float. A argument directly passed to the [forced photometry package](https://github.com/askap-vast/forced_phot/) used by the pipeline. It defines the multiple of `major_axes` to use for identifying clusters. Defaults to 3.0.

**`MONITOR_ALLOW_NAN`**  
Boolean. A argument directly passed to the [forced photometry package](https://github.com/askap-vast/forced_phot/) used by the pipeline. It defines whether `NaN` values are allowed to be present in the extraction area in the rms or background maps. `True` would mean that `NaN` values are allowed. Defaults to False.

### Association

!!! tip
    Refer to the association documentation for full details on the association methods.

**`ASTROMETRIC_UNCERTAINTY_RA`**  
Float. Defines an uncertainty error to the RA that will be added in quadrature to the existing source extraction error. Used to represent a systematic positional error. Unit is arcseconds. Defaults to 1.0.

**`ASTROMETRIC_UNCERTAINTY_DEC`**  
Float. Defines an uncertainty error to the Dec that will be added in quadrature to the existing source extraction error. Used to represent systematic positional error. Unit is arcseconds. Defaults to 1.0.

**`ASSOCIATION_METHOD`**  
String. Select whether to use the `basic`, `advanced` or `deruiter` association method, entered as a string of the method name. Defaults to `"basic"`.

**`ASSOCIATION_RADIUS`**   
Float. The distance limit to use during `basic` and `advanced` association. Unit is arcseconds. Defaults to `10.0`.

**`ASSOCIATION_DE_RUITER_RADIUS`**  
Float. The de Ruiter radius limit to use during `deruiter` association only. The parameter is unitless. Defaults to `5.68`.

**`ASSOCIATION_BEAMWIDTH_LIMIT`**  
Float. The beamwidth limit to use during `deruiter` association only. Multiplicative factor. Defaults to `1.5`.

**`ASSOCIATION_PARALLEL`**  
Boolean. When `True`, association is performed in parallel on non-overlapping groups of sky regions. Defaults to `False`.

**`ASSOCIATION_EPOCH_DUPLICATE_RADIUS`**  
Float. Applies to epoch based association only. Defines the limit at which a duplicate source is identified. Unit is arcseconds. Defaults to `2.5` (commonly one pixel for ASKAP images).

### New Sources

**`NEW_SOURCE_MIN_SIGMA`**  
Float. Defines the limit at which a source is classed as a new source based upon the would-be significance of detections in previous images where no detection was made. I.e.

$$
\frac{f_{peak}}{\text{rms}_{image, min}} \geq \small{\text{NEW_SOURCE_MIN_SIGMA}}\text{,}
$$

where $f_{peak}$ is the initial detection peak flux measurement of the source in question and $\text{rms}_{image, min}$ is the minimum RMS value of the previous image(s) where no detection was made. If the requirement is met in any previous image then the source is flagged as new. Defaults to `5.0`.

### General

**`DEFAULT_SURVEY`**  
Currently not used hence this option can be safely ignored.

**`FLUX_PERC_ERROR`**  
Define a percentage flux error that will be added in quadrature to the extracted sources. Note that this will be reflected in the final source statistics and will not be applied directly to the measurements. Entered as a float between 0 - 1.0 which represents 0 - 100%. Defaults to `0.0`.

**`USE_CONDON_ERRORS`**  
Boolean. Calculate the Condon errors of the extractions when read in from the source extraction file. If `False` then the errors directly from the source finder output are used. Recommended to set to `True` for selavy extractions. Defaults to `True`.

**`SELAVY_LOCAL_RMS_ZERO_FILL_VALUE`**  
Float. Value to substitute for the `local_rms` parameter in selavy extractions if a `0.0` value is found. Unit is mJy. Defaults to `0.2`.

**`CREATE_MEASUREMENTS_ARROW_FILES`**  
Boolean. When `True` then two `arrow` format files are produced:

* `measurements.arrow` - an arrow file containing all the measurements associated with the run.
* `measurement_pairs.arrow` -  an arrow file containing the measurement pairs information pre-merged with extra information from the measurements.

Producing these files for large runs (200+ images) is recommended for post-processing. Defaults to `False`.

!!! note
    The arrow files can be produced after the run has completed by an administrator.

**`SUPPRESS_ASTROPY_WARNINGS`**  
Boolean. Astropy warnings are suppressed in the logging output if set to `True`. Defaults to `True`.

**`SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS`**  
Float. Defines the minimum `Vs` two-epoch metric value threshold used to attach the most significant pair value to the source. Defaults to `4.3`.
