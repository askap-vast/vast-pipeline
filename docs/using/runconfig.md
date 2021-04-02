# Run Configuration

This page gives an overview of the configuration options available for a pipeline run.

## Default Configuration File

Below is an example of a default `config.yaml` file. Note that no images or other input files have been provided. The file can be either edited directly or through the editor available on the run detail page.

```yaml
# This file specifies the pipeline configuration for the current pipeline run.
# You should review these settings before processing any images - some of the default
# values will probably not be appropriate.

run:
  # Path of the pipeline run
  path: ... # auto-filled by pipeline initpiperun command

  # Default survey used by the website for analysis plots. Currently not used.
  default_survey: None

  # Hide astropy warnings during the run execution.
  suppress_astropy_warnings: True

inputs:
  # NOTE: all the inputs must match with each other, i.e. the catalogue for the first
  # input image (inputs.image[0]) must be the first input catalogue (inputs.selavy[0])
  # and so on.
  image:
  # list input images here, e.g. (note the leading hyphens)
  # - /path/to/image1.fits
  # - /path/to/image2.fits

  selavy:
  # list input selavy catalogues here, as above with the images

  noise:
  # list input noise (rms) images here, as above with the images

  # Required only if source_monitoring.monitor is true, otherwise optional. If not providing
  # background images, remove the entire background section below.
  background:
  # list input background images here, as above with the images


source_monitoring:
  # Source monitoring can be done both forward and backward in 'time'.
  # Monitoring backward means re-opening files that were previously processed and can be slow.
  monitor: True

  # Minimum SNR ratio a source has to be if it was placed in the area of minimum rms in
  # the image from which it is to be extracted from. If lower than this value it is skipped
  min_sigma: 3.0
  
  # Multiplicative scaling factor to the buffer size of the forced photometry from the
  # image edge
  edge_buffer_scale: 1.2

  # Passed to forced-phot as `cluster_threshold`. See docs for details. If unsure, leave
  # as default.
  cluster_threshold: 3.0

  # Attempt forced-phot fit even if there are NaN's present in the rms or background maps.
  allow_nan: False

source_association:
  # basic, advanced, or deruiter
  method: basic

  # Maximum source separation allowed during basic and advanced association in arcsec
  radius: 10.0

  # Options that apply only to deruiter association
  deruiter_radius: 5.68  # unitless
  deruiter_beamwidth_limit: 1.5  # multiplicative factor

  # Split input images into sky region groups and run the association on these groups in
  # parallel. Best used when there are a large number of input images with multiple
  # non-overlapping patches of the sky.
  # Not recommended for smaller searches of <= 3 sky regions.
  parallel: False

  # If images have been submitted in epoch dictionaries then an attempt will be made by
  # the pipeline to remove duplicate sources. To do this a crossmatch is made between
  # catalgoues to match 'the same' measurements from different catalogues. This
  # parameter governs the distance for which a match is made in arcsec. Default is 2.5
  # arcsec which is typically 1 pixel in ASKAP images.
  epoch_duplicate_radius: 2.5  # arcsec

new_sources:
  # Controls when a source is labelled as a new source. The source in question must meet
  # the requirement of: min sigma > (source_peak_flux / lowest_previous_image_min_rms)
  min_sigma: 5.0

measurements:
  # Source finder used to produce input catalogues. Only selavy is currently supported.
  source_finder: selavy

  # Minimum error to apply to all flux measurements. The actual value used will either
  # be the catalogued value or this value, whichever is greater. This is a fraction, e.g.
  # 0.05 = 5% error, 0 = no minimum error.
  flux_fractional_error: 0.0

  # Replace the selavy errors with Condon (1997) errors.
  condon_errors: True

  # Sometimes the local rms for a source is reported as 0 by selavy.
  # Choose a value to use for the local rms in these cases in mJy/beam.
  selavy_local_rms_fill_value: 0.2

  # Create 'measurements.arrow' and 'measurement_pairs.arrow' files at the end of 
  # a successful run.
  write_arrow_files: False

  # The positional uncertainty of a measurement is in reality the fitting errors and the
  # astrometric uncertainty of the image/survey/instrument combined in quadrature.
  # These two parameters are the astrometric uncertainty in RA/Dec and they may be different.
  ra_uncertainty: 1.0 # arcsec
  dec_uncertainty: 1.0  # arcsec

variability:
  # Only measurement pairs where the Vs metric exceeds this value are selected for the
  # aggregate pair metrics that are stored in Source objects.
  source_aggregate_pair_metrics_min_abs_vs: 4.3

```

!!! note
    Similarly to Python files, the indentation in the run configuration YAML file is important as it defines nested parameters.
    Throughout the documentation we use dot-notation to refer to nested parameters, for example `inputs.image` refers to the list of input images.
    This page on [YAML syntax](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html) from the Ansible documentation is a good brief primer on the basics.

## Configuration Options

### General Run Options

**`run.path`**
Path to the directory for the pipeline run. This parameter will be automatically filled if the configuration file is generate with the [`initpiperun` management command](../adminusage/cli.md#initpiperun) or if the run was created with the web interface.

**`run.default_survey`**
Currently not used hence this option can be safely ignored.

**`run.suppress_astropy_warnings`**
Boolean. Astropy warnings are suppressed in the logging output if set to `True`. Defaults to `True`.

### Input Images and Selavy Files

**`inputs.image`**
List or dictionary. The full paths to the image FITS files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types.

<!-- markdownlint-disable MD046 -->
=== "Normal mode"

    ```yaml
    inputs:
      image:
      - /full/path/to/image1.fits
      - /full/path/to/image2.fits
      - /full/path/to/image3.fits
    ```

=== "Epoch mode"

    ```yaml
    inputs:
      image:
        epoch01:
        - /full/path/to/image1.fits
        - /full/path/to/image2.fits
        epoch02:
        - /full/path/to/image3.fits
    ```
<!-- markdownlint-enable MD046 -->

**`inputs.selavy`**
List or Dictionary. The full paths to the selavy text files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types.

<!-- markdownlint-disable MD046 -->
=== "Normal mode"

    ```yaml
    inputs:
      selavy:
      - /full/path/to/image1_selavy.txt
      - /full/path/to/image2_selavy.txt
      - /full/path/to/image3_selavy.txt
    ```

=== "Epoch mode"

    ```yaml
    inputs:
      selavy:
        epoch01:
        - /full/path/to/image1_selavy.txt
        - /full/path/to/image2_selavy.txt
        epoch02:
        - /full/path/to/image3_selavy.txt
    ```
<!-- markdownlint-enable MD046 -->

**`inputs.noise`**
List or Dictionary. The full paths to the image noise (RMS) FITS files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types.

<!-- markdownlint-disable MD046 -->
=== "Normal mode"

    ```yaml
    inputs:
      noise:
      - /full/path/to/image1_rms.fits
      - /full/path/to/image2_rms.fits
      - /full/path/to/image3_rms.fits
    ```

=== "Epoch mode"

    ```yaml
    inputs:
      noise:
        epoch01:
        - /full/path/to/image1_rms.fits
        - /full/path/to/image2_rms.fits
        epoch02:
        - /full/path/to/image3_rms.fits
    ```
<!-- markdownlint-enable MD046 -->

**`inputs.background`**
List or Dictionary. The full paths to the image background (mean) FITS files to be processed. Also accepts a dictionary format that will activate _epoch mode_ (see [Epoch Based Association](../design/association.md#epoch-based-association)) in which case all inputs must also be in dictionary format. The order of the entries must be consistent with the other input types. Only required to be defined if `source_monitoring.monitor` is set to `True`.

<!-- markdownlint-disable MD046 -->
=== "Normal mode"

    ```yaml
    inputs:
      background:
      - /full/path/to/image1_bkg.fits
      - /full/path/to/image2_bkg.fits
      - /full/path/to/image3_bkg.fits
    ```

=== "Epoch mode"

    ```yaml
    inputs:
      background:
        epoch01:
        - /full/path/to/image1_bkg.fits
        - /full/path/to/image2_bkg.fits
        epoch02:
        - /full/path/to/image3_bkg.fits
    ```
<!-- markdownlint-enable MD046 -->

### Source Monitoring

**`source_monitoring.monitor`**
Boolean. Turns on or off forced extractions for non detections. If set to `True` then `inputs.background` must also be defined. Defaults to `False`.

**`source_monitoring.min_sigma`**
Float. For forced extractions to be performed they must meet a minimum signal-to-noise threshold with respect to the minimum rms value of the respective image. If the proposed forced measurement does not meet the threshold then it is not performed. I.e.

$$
\frac{f_{peak}}{\text{rms}_{image, min}} \geq \small{\text{source_monitoring.min_sigma}}\text{,}
$$

where $f_{peak}$ is the initial detection peak flux measurement of the source in question and $\text{rms}_{image, min}$ is the minimum RMS value of the image where the forced extraction is to take place. Defaults to `3.0`.

**`source_monitoring.edge_buffer_scale`**
Float. Monitor forced extractions are not performed when the location is within 3 beamwidths of the image edge. This parameter scales this distance by the value set, which can help avoid errors when the 3 beamwidth limit is insufficient to avoid extraction failures. Defaults to 1.2.

**`source_monitoring.cluster_threshold`**
Float. A argument directly passed to the [forced photometry package](https://github.com/askap-vast/forced_phot/) used by the pipeline. It defines the multiple of `major_axes` to use for identifying clusters. Defaults to 3.0.

**`source_monitoring.allow_nan`**
Boolean. A argument directly passed to the [forced photometry package](https://github.com/askap-vast/forced_phot/) used by the pipeline. It defines whether `NaN` values are allowed to be present in the extraction area in the rms or background maps. `True` would mean that `NaN` values are allowed. Defaults to False.

### Association

!!! tip
    Refer to the association documentation for full details on the association methods.

**`source_association.method`**
String. Select whether to use the `basic`, `advanced` or `deruiter` association method, entered as a string of the method name. Defaults to `"basic"`.

**`source_association.radius`**
Float. The distance limit to use during `basic` and `advanced` association. Unit is arcseconds. Defaults to `10.0`.

**`source_association.deruiter_radius`**
Float. The de Ruiter radius limit to use during `deruiter` association only. The parameter is unitless. Defaults to `5.68`.

**`source_association.deruiter_beamwidth_limit`**
Float. The beamwidth limit to use during `deruiter` association only. Multiplicative factor. Defaults to `1.5`.

**`source_association.parallel`**
Boolean. When `True`, association is performed in parallel on non-overlapping groups of sky regions. Defaults to `False`.

**`source_association.epoch_duplicate_radius`**
Float. Applies to epoch based association only. Defines the limit at which a duplicate source is identified. Unit is arcseconds. Defaults to `2.5` (commonly one pixel for ASKAP images).

### New Sources

**`new_sources.min_sigma`**
Float. Defines the limit at which a source is classed as a new source based upon the would-be significance of detections in previous images where no detection was made. i.e.

$$
\frac{f_{peak}}{\text{rms}_{image, min}} \geq \small{\text{new_sources.min_sigma}}\text{,}
$$

where $f_{peak}$ is the initial detection peak flux measurement of the source in question and $\text{rms}_{image, min}$ is the minimum RMS value of the previous image(s) where no detection was made. If the requirement is met in any previous image then the source is flagged as new. Defaults to `5.0`.

### Measurements

**`measurements.source_finder`**
String. Signifies the format of the source finder text file read by the pipeline. Currently only supports `"selavy"`.

!!! warning
    Source finding is not performed by the pipeline and must be completed prior to processing.

**`measurements.flux_fractional_error`**
Define a fractional flux error that will be added in quadrature to the extracted sources. Note that this will be reflected in the final source statistics and will not be applied directly to the measurements. Entered as a float between 0 - 1.0 which represents 0 - 100%. Defaults to `0.0`.

**`measurements.condon_errors`**
Boolean. Calculate the Condon errors of the extractions when read in from the source extraction file. If `False` then the errors directly from the source finder output are used. Recommended to set to `True` for selavy extractions. Defaults to `True`.

**`measurements.selavy_local_rms_fill_value`**
Float. Value to substitute for the `local_rms` parameter in selavy extractions if a `0.0` value is found. Unit is mJy. Defaults to `0.2`.

**`measurements.write_arrow_files`**
Boolean. When `True` then two `arrow` format files are produced:

* `measurements.arrow` - an arrow file containing all the measurements associated with the run.
* `measurement_pairs.arrow` -  an arrow file containing the measurement pairs information pre-merged with extra information from the measurements.

Producing these files for large runs (200+ images) is recommended for post-processing. Defaults to `False`.

!!! note
    The arrow files can optionally be produced after the run has completed by an administrator.

**`measurements.ra_uncertainty`**
Float. Defines an uncertainty error to the RA that will be added in quadrature to the existing source extraction error. Used to represent a systematic positional error. Unit is arcseconds. Defaults to 1.0.

**`measurements.dec_uncertainty`**
Float. Defines an uncertainty error to the Dec that will be added in quadrature to the existing source extraction error. Used to represent systematic positional error. Unit is arcseconds. Defaults to 1.0.

### Variability

**`variability.source_aggregate_pair_metrics_min_abs_vs`**
Float. Defines the minimum $V_s$ two-epoch metric value threshold used to attach the most significant pair value to the source. Defaults to `4.3`.
