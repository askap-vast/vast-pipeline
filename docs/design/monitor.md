# Forced Measurements

This page details the forced measurements obtained by the pipeline.

## Definition

When `source_monitoring.monitor: true` is set in the pipeline run configuration file, any sources that have non-detections in their lightcurve will have these measurements 'filled in' by performing `forced measurements`. This means that the flux at the source's current average position in the non-detection image is forcefully measured by fitting a Gaussian with the same shape as the respective image restoring beam.

Forced measurements are labelled in the measurements table and parquet files by the column `forced`.

!!! note
    Forced measurements are local to a pipeline run - they will not appear in any other pipeline run.

!!! warning
    Forced measurements are not performed within 3 beamwidths of the image edge.

## Minimum Sigma Filter

Before forced measurements are processed, a minimum sigma check is made to make sure that the forced measurements would provide useful information. For example, a dataset may contain an image that has significantly less sensitivity than the other images. In this case a faint source in the more sensitive images will not be expected to be seen in the less sensitive image. To avoid unnecessary computation, this source is not forcefully measured.

The check is performed like that which is made in the [New Sources](newsources.md) process where the signal-to-noise ratio is calculated using the rms$_{min}$ of the image it is to be extracted from. Hence, for a forced measurement to take place the following condition must be met:

$$
\frac{f_{peak,det}}{\text{rms}_{min,i}} > \text{source_monitoring.min_sigma},
$$

where $i$ is the image for which the measurement is to be forcefully measured.

`source_monitoring.min_sigma` is able to be controlled by the user in the pipeline run configuration file. By default the value is set to 3.0.

!!! tip
    Setting `source_monitoring.min_sigma: 0.0` will ensure that all forced measurements are performed regardless of signal-to-noise.

## Configuration File Options

The following options are present in the pipeline run configuration file to users along with their defaults:

```yaml
source_monitoring:
  monitor: false
  min_sigma: 3.0
  edge_buffer_scale: 1.2
  cluster_threshold: 3.0
  allow_nan: false
```

* `source_monitoring.monitor` turns forced measurements on (`true`) or off (`false`).
* `source_monitoring.min_sigma` controls the the minimum sigma check threshold as explained in [Minimum Sigma Filter](#minimum-sigma-filter).
* `source_monitoring.edge_buffer_scale` controls the size of the buffer from the image edge where forced measurements are not performed (`source_monitoring.edge_buffer_scale` $\times 3\theta_{beam}$). An error can sometimes occur that increasing this value can solve.
* `source_monitoring.cluster_threshold` is directly passed to the [forced photometry package](#software-forced_phot) used by the pipeline. It defines the multiple of `major_axes` to use for identifying clusters.
* `source_monitoring.allow_nan` is directly passed to the [forced photometry package](#software-forced_phot) used by the pipeline. It defines whether `NaN` values are allowed to be present in the extraction area in the rms or background maps, i.e. `true` would mean that `NaN` values are allowed.

## Software - forced_phot

The software used to perform the forced measurements, `forced_phot`, was written by David Kaplan and can be found on the VAST GitHub [here](https://github.com/askap-vast/forced_phot).
