# Column Descriptions

This page details the columns contained in each output file.

## assocications

| Column | Unit | Description |
| ------ | ---- | ----------- |
| `source_id` | n/a | The database `id` of the source for the association. |
| `meas_id` | n/a | The database `id` of the measurement for the association. |
| `d2d` | arcsec | The on-sky separation of the measurement to the source at the iteration stage the assocation was created. |
| `dr` | n/a | The de Ruiter radius of the measurement to the source at the iteration stage the assocation was created. Will be 0 if de Ruiter assocation is not being used. |

## bands

| Column | Unit | Description |
| ------ | ---- | ----------- |
|`id`| n/a | The database `id` of the band. |
|`name`| n/a | The string name of the band, equal to the frequency value. |
|`frequency`| MHz | The band central frequency. |
|`bandwidth`| MHz | The bandwidth of the frequency band, will be 0 if not known. |

## images

| Column <img width=200/>| Unit | Description |
| ------ | ---- | ----------- |
|`id`| n/a | The database `id` of the image. |
|`band_id`| n/a | The database `id` of the associated band. |
|`skyreg_id`| n/a | The database `id` of the associated sky region. |
|`measurements_path`| n/a | The system path to the measurements parquet file. |
|`polarisation`| n/a | The polarisation of the image. |
|`name`| n/a | The name of the image, taken from the filename. |
|`path`| n/a | The system path to the image FITS file. |
|`noise_path`| n/a | The system path to the associated noise image FITS file. |
|`background_path`| n/a | The system path to the associated background image FITS file. |
|`datetime`| n/a | The date and time of the observation, read from the FITS header. |
|`jd`| days | The date and time of the observation in Julian Days. |
|`duration`| s | The duration of the observation taken from the FITS header, if available. |
|`ra`| deg | The central Right Ascension coordinate of the image. |
|`dec`| deg | The central Declination coordinate of the image. |
|`fov_bmaj`| deg | The estimated major axis field-of-view value - the `radius_pixels` multipled by the major axis pixel size. |
|`fov_bmin`| deg | The estimated minor axis field-of-view value - the `raidus_pixels` multipled by the minor axis pixel size. |
|`physical_bmaj`| deg | The actual major axis on-sky size - the number of pixels on the major axis multiplied by the major axis pixel size. |
|`physical_bmin`| deg | The actual minor axis on-sky size - the number of pixels on the minor axis multiplied by the minor axis pixel size. |
|`radius_pixels`| pixels | Estimated 'diameter' of the useable image area. |
|`beam_bmaj`| deg | The size of the major axis of the image restoring beam. |
|`beam_bmin`| deg | The size of the minor axis of the image restoring beam. |
|`beam_bpa`| deg | The position angle of the image restoring beam. |
|`rms_median`| mJy | The median RMS value derrived from the RMS map. |
|`rms_min`| mJy | The minimum RMS value derrived from the RMS map (pixel value). |
|`rms_max`| mJy | The maximum RMS value derrived from the RMS map (pixel value). |

## measurements

!!! tip
    Some columns are the same as that defined in the [Selavy source finder output](https://www.atnf.csiro.au/computing/software/askapsoft/sdp/docs/current/analysis/postprocessing.html#output-files){:target="_blank"}.

| Column <img width=200/>| Unit | Description |
| ------ | ---- | ----------- |
|`island_id`| n/a | The Selavy assigned island_id. |
|`component_id`| n/a | The Selavy assigned component_id. |
|`local_rms`| mJy | The rms value at the location of the measurement. |
|`ra`| deg | The right ascension coordinate of the measurement. |
|`ra_err`| deg | The error of the right ascension coordinate of the measurement. |
|`dec`| deg | The declination coordinate of the measurement. |
|`dec_err`| deg | The error of the declination coordinate of the measurement. |
|`flux_peak`| mJy | The measured peak flux of the component. |
|`flux_peak_err`| mJy | The error of the measured peak flux of the component. |
|`flux_int`| mJy | The measured integrated flux of the component. |
|`flux_int_err`| mJy | The error of the measured integrated flux of the component. |
|`bmaj`| arcsec | The major axis size of the fitted Gaussian (FWHM). |
|`err_bmaj`| deg | The error of the major axis size of the fitted Gaussian (FWHM). |
|`bmin`| arcsec | The minor axis size of the fitted Gaussian (FWHM). |
|`err_bmin`| deg | The error of the minor axis size of the fitted Gaussian (FWHM). |
|`pa`| deg | The position angle of the fitted Gaussian (FWHM). |
|`err_pa`| deg | The error of the position angle of the fitted Gaussian (FWHM). |
|`psf_bmaj`| arcsec | The Selavy deconvolved size of the major axis of the fitted Gaussian. |
|`psf_bmin`| arcsec | The Selavy deconvolved size of the minor axis of the fitted Gaussian. |
|`psf_pa`| deg | The Selavy deconvolved position angle of the fitted Gaussian. |
|`flag_c4`| n/a | Selavy flag denoting whether the component is considered formally bad (doesn't meet chi-squared criterion). |
|`chi_squared_fit`| n/a  | The Selavy quality of the fit. |
|`spectral_index`| n/a | The fitted Selavy spectral index of the component. |
|`spectral_index_from_TT`| n/a | Selavy flag to denote if the spectral index has been derived from the Taylor-term images (`True`). |
|`has_siblings`| n/a | Selavy flag to denote whether the component is one of many fitted to the same island. |
|`image_id`| n/a | The database `id` of the image the measurement is from. |
|`time`| n/a | The date and time of observation the measurement is from (obtained from the image). |
|`name`| n/a | The string name of the measurement. |
|`snr`| n/a | The signal-to-noise ratio of the measurement. |
|`compactness`| n/a | The compactness of the measurement (`flux_int`/`flux_peak`). |
|`ew_sys_err`| deg | The systematic right ascension error assigned to the measurement. |
|`ns_sys_err`| deg | The systematic declination error assigned to the measurement. |
|`error_radius`| deg | The pipeline estimated error radius of the measurement. |
|`uncertainty_ew`| deg | Total RA positional error of the measurement. |
|`uncertainty_ns`| deg | Total Dec positional error of the measurement. |
|`weight_ew`| deg$^{-1}$ | The weight of the RA error (1/e). |
|`weight_ns`| deg$^{-1}$ | The weight of the Dec error (1/e). |
|`forced`| n/a | Flag to denote whether the measurement is produced from the forced fitting procedure (`True`). |
|`flux_int_isl_ratio`| n/a | The ratio of the measurements integrated flux to the total island integrated flux. |
|`flux_peak_isl_ratio`| n/a | The ratio of the measurements peak flux to the total island peak flux. |
|`id`| n/a | The database `id` of the measurement. |

## measurement_pairs

| Column | Unit | Description |
| ------ | ---- | ----------- |
|`meas_id_a`| n/a | The database `id` of measurement `a` of the pair. |
|`meas_id_b`| n/a | The database `id` of measurement `b` of the pair. |
|`flux_int_a`| mJy | The integrated flux of measurement `a` of the pair. |
|`flux_int_err_a`| mJy | The error of the integrated flux of measurement `a` of the pair. |
|`flux_peak_a`| mJy | The peak flux of measurement `a` of the pair. |
|`flux_peak_err_a`| mJy | The error of the peak flux of measurement `a` of the pair. |
|`image_name_a`| n/a | The `image name` of measurement `a` of the pair. |
|`flux_int_b`| mJy | The integrated flux of measurement `b` of the pair. |
|`flux_int_err_b`| mJy | The error of the integrated flux of measurement `b` of the pair. |
|`flux_peak_b`| mJy | The peak flux of measurement `b` of the pair. |
|`flux_peak_err_b`| mJy | The error of the peak flux of measurement `b` of the pair. |
|`image_name_b`| n/a | The `image name` of measurement `b` of the pair. |
|`vs_peak`| n/a | The pair $V_s$ value using the peak flux. |
|`vs_int`| n/a | The pair $V_s$ value using the integrated flux. |
|`m_peak`| n/a | The pair $m$ value using the peak flux. |
|`m_int`| n/a | The pair $m$ value using the integrated flux. |
|`source_id`| n/a | The database `id` of the source the pair is associated to. |
|`id`| n/a | The database `id` of the measurement pair. |

## relations

| Column | Unit | Description |
| ------ | ---- | ----------- |
|`from_source_id`| n/a | The database `id` of the first source in the relation pair. |
|`to_source_id`| n/a | The database `id` of the second source in the relation pair. |

## skyregions

| Column | Unit | Description |
| ------ | ---- | ----------- |
|`id`| n/a | The database `id` of the sky region. |
|`centre_ra`| deg | The right ascension value of the sky region central coordinate. |
|`centre_dec`| deg | The declination value of the sky region central coordinate. |
|`width_ra`| deg | The width of the area covered by the sky region. |
|`width_dec`| deg | The height of the area covered by the sky region. |
|`xtr_radius`| deg | The hypotenuse radius of the sky region. |
|`x`| rad | The central cartesian x coordinate of the sky region. |
|`y`| rad | The central cartesian y coordinate of the sky region. |
|`z`| rad | The central cartesian z coordinate of the sky region. |

## sources

!!! note
    The index column of the sources parquet is set to the database `id` of the source.

| Column <img width=550/>| Unit | Description |
| ------ | ---- | ----------- |
|`n_meas`| n/a | The total number of measurements associated to the source (selavy and forced). |
|`n_meas_sel`| n/a | The total number of selavy measurements associated to the source. |
|`n_meas_forced`| n/a | The total number of forced measurements associated to the source. |
|`n_sibl`| n/a | The total number of measurements that have a `has_sibling` value of `True`. |
|`n_rel`| n/a | The total number of relations the source has. |
|`wavg_ra`| deg | The weighted average of the Right Ascension of the measurements, that acts as the source position. |
|`wavg_dec`| deg | The weighted average of the Declination of the measurements, that acts as the source position. |
|`wavg_uncertainty_ew`| deg | The error of the weighted average right ascension value. |
|`wavg_uncertainty_ns`| deg | The error of the weighted average declination value. |
|`new`| n/a | Flag to signify the source is classed as a [`new source`](../design/newsources.md) (`True`). |
|`new_high_sigma`| n/a | The largest sigma value a new source would have if it was placed at its location in the previous images it was not detected in. See [New Sources](newsources.md#new-source-high-sigma) for more information. Set to 0 for non-new sources.|
|`n_neighbour_dist`| deg | The on-sky separation to the nearest source with in the same pipeline run. |
|`avg_compactness`| n/a | The average compactness value of the associated measurements. |
|`min_snr`| n/a | The minimum signal-to-noise ratio of the associated measurements. |
|`max_snr`| n/a | The maximum signal-to-noise ratio of the associated measurements. |
|`avg_flux_int`| mJy | The average integrated flux value of the measurements associated to the source (inc. forced measurements). |
|`max_flux_int`| mJy | The maximum integrated flux value of the measurements associated to the source (inc. forced measurements). |
|`min_flux_int`| mJy | The minimum integrated flux value of the measurements associated to the source (inc. forced measurements). |
|`avg_flux_peak`| mJy | The average peak flux value of the measurements associated to the source (inc. forced measurements). |
|`max_flux_peak`| mJy | The maximum peak flux value of the measurements associated to the source (inc. forced measurements). |
|`min_flux_peak`| mJy | The minimum peak flux value of the measurements associated to the source (inc. forced measurements). |
|`min_flux_peak_isl_ratio`| n/a | The minimum ratio of the peak flux to the total island peak flux of the measurements associated to the source. |
|`min_flux_int_isl_ratio`| n/a | The minimum ratio of the integrated flux to the total island integrated flux of the measurements associated to the source. |
|`v_int`| n/a | The calculated variability $V$ metric using the integrated flux values. See [variability statistics](../design/sourcestats.md#variability-statistics). |
|`v_peak`| n/a | The calculated variability $V$ metric using the peak flux values. See [variability statistics](../design/sourcestats.md#variability-statistics). |
|`eta_int`| n/a | The calculated variability $\eta$ metric using the integrated flux. See [variability statistics](../design/sourcestats.md#variability-statistics). |
|`eta_peak`| n/a | The calculated variability $\eta$ metric using the peak flux. See [variability statistics](../design/sourcestats.md#variability-statistics). |
|`vs_abs_significant_max_peak`| n/a | The $\mid V_{s}\mid$ value of the most significant two-epoch pair using the peak fluxes. Will be `0` if no significant pair. See [variability statistics](../design/sourcestats.md#variability-statistics). |
|`m_abs_significant_max_peak`| n/a | The $\mid m \mid$ value of the most significant two-epoch pair using the peak fluxes. Will be `0` if no significant pair. See [variability statistics](../design/sourcestats.md#variability-statistics). |
|`vs_abs_significant_max_int`| n/a | The $\mid V_{s}\mid$ value of the most significant two-epoch pair using the integrated fluxes. Will be `0` if no significant pair. See [variability statistics](../design/sourcestats.md#variability-statistics).|
|`m_abs_significant_max_int`| n/a | The $\mid m \mid$ value of the most significant two-epoch pair using the integrated fluxes. Will be `0` if no significant pair. See [variability statistics](../design/sourcestats.md#variability-statistics). |
