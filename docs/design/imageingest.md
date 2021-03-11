# Image & Selavy Catalogue Ingest

This page details the stage of the pipeline that ingests the images to be processed.

When the pipeline encounters an image for the first time (in any pipeline run), the image and accompanying selavy catalogue are uploaded to the pipeline database. The portion of a pipeline log file below shows the messages for the ingestion of three images.

!!! note
    Once an image is uploaded then that image is available for all other runs to use without having to re-upload.

```bash
2021-03-11 12:59:49,751 loading INFO Reading image VAST_0127-73A.EPOCH01.I.cutout.fits ...
2021-03-11 12:59:49,756 utils INFO Adding new frequency band: 887
2021-03-11 12:59:49,771 utils INFO Created sky region 21.838, -73.121
2021-03-11 12:59:49,775 utils INFO Adding new-test-data to sky region 21.838, -73.121
2021-03-11 12:59:50,100 loading INFO Processed measurements dataframe of shape: (203, 40)
2021-03-11 12:59:50,273 loading INFO Bulk created #203 Measurement
2021-03-11 12:59:50,334 loading INFO Reading image VAST_2118+00A.EPOCH01.I.cutout.fits ...
2021-03-11 12:59:50,345 utils INFO Created sky region 322.439, -3.987
2021-03-11 12:59:50,347 utils INFO Adding new-test-data to sky region 322.439, -3.987
2021-03-11 12:59:50,577 loading INFO Processed measurements dataframe of shape: (148, 40)
2021-03-11 12:59:50,708 loading INFO Bulk created #148 Measurement
2021-03-11 12:59:50,736 loading INFO Reading image VAST_2118-06A.EPOCH01.I.cutout.fits ...
2021-03-11 12:59:50,749 utils INFO Created sky region 322.439, -4.487
2021-03-11 12:59:50,752 utils INFO Adding new-test-data to sky region 322.439, -4.487
2021-03-11 12:59:50,977 loading INFO Processed measurements dataframe of shape: (159, 40)
2021-03-11 12:59:51,111 loading INFO Bulk created #159 Measurement
```

## Ingest Steps Summary

1. The FITS file is opened and read (the header is used to obtain meta data) along with the selavy component catalogue text file.
2. The selavy component file is cleaned for erroneous components along with the calculation of extra measurements metrics such as `signal-to-noise ratio`, `compactness` and positional uncertainties. Also, optionally, flux errors are recalculated using the [Condon 1997](https://ui.adsabs.harvard.edu/abs/1997PASP..109..166C/abstract) method. See [Selavy Measurements Processing](#selavy-measurements-processing) for further details.
3. Median, minimum and maxiumn root-mean-squre (RMS) values are read from the accompanying RMS image provided by the user and these values are attached to the image.
4. The image is also attached to a sky region and a frequency band based on its properties (see [Sky Region](#sky-region) and [Frequency Band](#frequency-band)).
5. The cleaned measurements (selavy components) are saved to a parquet file for repeated easy access.
6. The overall image, band and sky region information for the pipeline run are written to a parquet file.

See [Ingest Steps Details](#ingest-steps-details) for further details on the steps.

## Uniqueness

The image uniqueness is defined by the filename. I.e. if you wished to upload a different version of the same image (perhaps different selavy settings were used in the source extraction) then you would have to make sure the image filename was different to the previous entry.

## Ingest Steps Details

### Selavy Measurements Processing

#### Cleaning

The selavy measurements are checked for erroneous values that could cause issues with the source association. Such errors are:

* Sources that have a peak or integrated flux value of 0.
* Sources that have a `bmaj` or `bmin` value of 0.
* Sources that have a `bmaj` or `bmin` value less than half of the respective values of the image restoring beam.

Any sources that are found to have the above properties are removed.

In addition to the above filtering, components are also checked for zero values that can be corrected, where the correction values to apply are defined in the user or overall pipeline configuration files. The field names of these zero checks are defined in the table below.

| Field Name          | Correct with                          | Location      |
| ------------------- | ------------------------------------- | ------------- |
| `flux_int_err`      | `FLUX_DEFAULT_MIN_ERROR`              | `settings.py` |
| `flux_peak_err`     | `FLUX_DEFAULT_MIN_ERROR`              | `settings.py` |
| `ra_err`            | `POS_DEFAULT_MIN_ERROR`               | `settings.py` |
| `dec_err`           | `POS_DEFAULT_MIN_ERROR`               | `settings.py` |
| `local_rms`         | `SELAVY_LOCAL_RMS_ZERO_FILL_VALUE`    | `config.py`   |

#### Condon 1997 Flux & Positional Errors

If selected in the pipeline run configuration file, the flux and positional errors are recalculated using the [Condon 1997](https://ui.adsabs.harvard.edu/abs/1997PASP..109..166C/abstract) method. The following errors are replaced with those that are recalculated:

* `flux_peak_err`
* `flux_int_err`
* `err_bmaj`
* `err_bmin`
* `err_pa`
* `ra_err`
* `dec_err`

#### Positional Errors (de Ruiter method)

Firstly, the systematic astrometry error from the user pipeline run configuration file (`ASTROMETRIC_UNCERTAINTY_RA` and `ASTROMETRIC_UNCERTAINTY_DEC`) are applied to the measurement. These values are saved as `ew_sys_err` and `ns_sys_err`.

!!! warning
    Currently the systematic errors applied at the pipeline run stage are then permanently fixed to the measurements, meaning that all subsequent runs using these measurements will use the fixed astrometic error.
    
    It is recommended to leave the values to the default value of 1.0. 

In order to apply the `TraP` de Ruiter association method, some extra positional error values are calculated. Firstly the `ra_err` and `dec_err` are used to estimate the largest angular uncertainty of the measurement which is recorded as the `error_radius`. It is estimated by finding the largest angular separation between the measurement coordinate and every coordinate combination of $ra \pm \delta ra$ and $dec \pm \delta ra$.

The final uncertainties are then defined as the hypotenuse values of `ew_sys_err`/`ns_sys_err` and the `error_radius`. These are defined as the `uncertainty_ew` and `uncertainty_ns`, respectively. The weights of the errors are defined as $\frac{1}{\text{uncertainty_x}^{2}}$ where `x` is either `ew` or `ns`.

#### Other Metrics

The table below defines extra metrics that are added to the measurements.

| Field Name           | Description |
| -------------------- | ----------- |
| `time`               | The image datetime applied to the measurement. |
| `snr`                | $\frac{\text{flux_peak}}{\text{local_rms}}$. |
| `compactness`        | $\frac{\text{flux_int}}{\text{flux_peak}}$. |
| `flux_int_isl_ratio` | $\frac{\text{flux_int}}{\text{total_island_int_flux}}$. |
| `flux_peak_isl_ratio`| $\frac{\text{flux_peak}}{\text{total_island_peak_flux}}$. |

### Sky Region

The pipeline defines `sky regions` in order to be easily able to find images that cover the same region of the sky. A sky region is defined by:

* The central coodinate.
* The width in both ra and dec (the `physical_bmaj` and `physical_bmin` values are used here, see [Uploaded Image Information](#uploaded-image-information)).
* An extraction radius (`xtr_radius`; `fov_bmin` is used here, again see [Uploaded Image Information](#uploaded-image-information)).

Hence, images that cover the exact same patch of sky will be assigned to the same sky region.

### Frequency Band

The image is associated to a frequency object in the pipeline that represents the observational frequency information of the image. The `frequency` and the `bandwidth` are recorded.

### Image RMS Values

The median, minimum and maximum values are calculated directly from the RMS map supplied by the user as a required input. This is achieved by loading the data from the FITS file and using the respective `numpy` operations on the data array to obtain the values.

## FITS Headers Used

The table below defines which header fields are used to read the image information.

| Header Field           | Used For |
| -------------------- | ----------- |
| `DATE-OBS`               | The date and time of the observation. |
| `TIMESYS`               | The timezone of the date and time. |
| `DURATION`                | Duration of the observation in seconds. |
| `STOKES`        | Stokes parameter of the image. |
| `TELESCOP` | Telescope name. |
| `BMAJ`| Major axis size of the restoring beam. |
| `BMIN`| Minor axis size of the restoring beam. |
| `BPA`| Position angle of the restoring beam. |
| `NAXIS1`| Size of the image axis. |
| `NAXIS2`| Size of the image. |
| `CTYPE3(or 4)`| Check if equal to `FREQ` to use for frequency information. |
| `CRVAL3(or 4)`| Central frequency.  |
| `CDELT3(or 4)`| Bandwidth. |

`RESTFREQ` and `RESTBW` can also be used as fallback options for frequency detection.

The `astropy` method `proj_plane_pixel_scales` is used to obtain the pixel scales.

## Uploaded Image Information

The table below defines what is defined and uploaded using the meta data (FITS header) and other inputs.

| Field Name          | Default | Description                          |
| ------------------- | ------- | ------------------------------------ |
| `measurements_path` | n/a     | The system path to the corresponding selavy components file (saved as a parquet file by the pipeline)  |
| `polarisation`      | `I`     | The polarisation of the image (currently only Stokes `I` is supported). |
| `name`              | n/a     | The name of the image which is taken from the filename. |
| `path`              | n/a     | The system path to the image FITS file. |
| `noise_path`        | `''`    | The system path to the related noise image FITS file. |
| `background_path`   | `''`    | The system path to the related background image FITS file. |
| `datetime`          | n/a     | Observational datetime of the image. |
| `jd`                | n/a     | Observational datetime of the image in Julian days format. |
| `duration`          | `0`     | Duration of the observation (if found in header). Seconds. |
| `ra`                | n/a     | The Right Ascension of the image pointing centre. Degrees. |
| `dec`               | n/a     | The Declination of the image pointing centre. Degrees. |
| `fov_bmaj`          | n/a     | The estimated major axis field-of-view value - the `radius_pixels` multipled by the major axis pixel size. Degrees. |
| `fov_bmin`          | n/a     | The estimated minor axis field-of-view value - the `raidus_pixels` multipled by the minor axis pixel size. Degrees. |
| `physical_bmaj`     | n/a     | The actual major axis on-sky size - the number of pixels on the major axis multiplied by the major axis pixel size. Degrees. |
| `physical_bmin`     | n/a     | The actual minor axis on-sky size - the number of pixels on the minor axis multiplied by the minor axis pixel size. Degrees. |
| `radius_pixels`     | n/a     | Estimated 'diameter' of the useable image area. Pixels. |
| `beam_bmaj`         | n/a     | The size of the major axis of the image restoring beam. Degrees. |
| `beam_bmin`         | n/a     | The size of the minor axis of the image restoring beam. Degrees. |
| `beam_bpa`          | n/a     | The position angle of the image restoring beam. Degrees. |
| `rms_median`        | n/a     | The median RMS value derrived from the RMS map. mJy. |
| `rms_min`           | n/a     | The minimum RMS value derrived from the RMS map (pixel value). mJy. |
| `rms_max`           | n/a     | The maximum RMS value derrived from the RMS map (pixel value). mJy. |