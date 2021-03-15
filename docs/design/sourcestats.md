# Source Statistics

This page details the source statistics that are calculated by the pipeline.

## Overview

The table below provides a summary of all the statistic and counts provided by the pipeline. See the [Variability Statistics](#variability-statistics) section for the table containing the variability metrics.

!!! note
    Remember that all source statistics and counts are calculated from the invidiual measurements that are associated with the source.

| Parameter                        | Includes Forced Meas. | Description      | 
| ------------------------------ | ------------------------ | ----------------- |
| `wavg_ra`          |  No    |  The weighted average of the Right Ascension, degrees.  |
| `wavg_dec`                |  No    |  The weighted average of the Declination, degrees.  |
| `wavg_uncertainty_ew`          |  No   |         The weighted average uncertainty in the east-west (RA) direction, degrees. |
| `wavg_uncertainty_ns`          |  No    |         The weighted average uncertainty in the north-south (Dec) direction, degrees. |
| `avg_flux_int`          |  Yes   |         The average integrated flux, mJy. |
| `max_flux_int`          |  Yes    |         The maximum integrated flux value, mJy. |
| `min_flux_int`         |  Yes     |         The minimum integrated flux value, mJy. |
| `avg_flux_peak`         |  Yes    |         The average peak flux, mJy. |
| `max_flux_peak`         |  Yes     |         The maximum peak flux value, mJy. |
| `min_flux_peak`        |  Yes      |         The minimum peak flux value, mJy. |
| `min_flux_int_isl_ratio`        |  Yes      |   The minimum integrated flux value island ratio (int_flux / total_isl_int_flux). |
| `min_flux_peak_isl_ratio`        |  Yes      |   The minimum peak flux value island ratio (peak_flux / total_isl_peak_flux). |
| `avg_compactness`        |  No      |         The average compactness of the source (compactness is defined by int_flux / peak_flux). |
| `min_snr`        |  No      |         The minimum signal-to-noise ratio of the source. |
| `max_snr`        |  No      |         The maximum signal-to-noise ratio of the source. |
| `n_neighbour_dist`        |  N/A      |         On sky separation distance to the nearest neighbour within the same run, degrees (arcmin on webserver). |
| `new_high_sigma`        |  N/A      |        The largest sigma value a new source would have if it was placed at its location in the previous images it was not detected in. See [New Sources](newsources.md#new-source-high-sigma) for more information. New sources only. |
| `n_meas`        |  Yes      |         The total number of measurements associated to the source. Named `Total Datapoints` on the webserver. |
| `n_meas_sel`        |  No      |         The total number of selavy measurements associated to the source. Named `Selavy Datapoints` on the webserver. |
| `n_meas_forced`        |  Yes      |         The total number of forced measurements associated to the source. Named `Forced Datapoints` on the webserver. |
| `n_rel`        |  N/A      |        The total number of relations the source has. See [Source Association](association#relations). Named `Relations` on the webserver. |
| `n_sibl`        |  N/A      |        The total number measurements that has a sibling. On the webserver tables this is firstly presented as a boolean column of if the source contains measurements that have a sibling. |

## Variability Statistics

Below is a table describing the variability metrics of the source. See the following sections for further explanation of these metrics. 

| Parameter                       | Includes Forced Meas. | Description      | 
| ------------------------------- | ------------------------ | ----------------- |
| `v_int`                         |  Yes   |  The $V$ metric for the integrated flux.  |
| `v_peak`                        |  Yes   |  The $V$ metric for the peak flux.  |
| `eta_int`                       |  Yes   |  The $\eta$ metric for the integrated flux. |
| `eta_peak`                      |  Yes   | The $\eta$ metric for the peak flux.|
| `vs_abs_significant_max_int`    |  Yes   | The $\mid V_{s}\mid$ value of the most significant two-epoch pair using the integrated fluxes. Will be `0` if no significant pair. |
| `m_abs_significant_max_int`     |  Yes   |  The $\mid m \mid$ value of the most significant two-epoch pair using the integrated fluxes. Will be `0` if no significant pair.|
| `vs_abs_significant_max_peak`   |  Yes   |  The $\mid V_s \mid$ value of the most significant two-epoch pair using the peak fluxes. Will be `0` if no significant pair.|
| `m_abs_significant_max_peak`    |  Yes   |  The $\mid m \mid$ value of the most significant two-epoch pair using the peak fluxes. Will be `0` if no significant pair.|


### $V$ and $\eta$ Metrics

The $V$ and $\eta$ metrics are the same as those used by the [LOFAR Transients Pipeline (TraP)](https://tkp.readthedocs.io/en/latest/), for a complete description please refer to [Swinbank et al. 2015](https://ui.adsabs.harvard.edu/abs/2015A%26C....11...25S/abstract). In the VAST Pipeline, the metrics are calculated twice, for both the integrated and peak fluxes.

$V$ is the proportional flux variability of the source and is given by the ratio of the sample standard deviation ($s$) and mean of the flux, $I$:

$$
V = \frac{s}{\overline{I}} = \frac{1}{\overline{I}} \sqrt{\frac{N}{N - 1}\left(\overline{I^{2}}-\overline{I}^{2}\right)}.
$$

The $\eta$ value is the significane of the variability, based on $\chi^{2}$ statistics, and is given by:

$$
\eta = \frac{N}{N - 1}\left(\overline{wI^{2}} - \frac{\overline{wI}^{2}}{\overline{w}}\right)
$$

where $w$ is the uncertainty ($e$) in $I$ of a measurement, and is given by $w=\frac{1}{e}$.

### Two-Epoch Metrics

Alternative variability metrics, $V_s$ and $m$, are also calculated which we refer to as the 'two-epoch metrics'. 
They are calculated for each unique pair of measurements assoicated with the source, with the most significant pair of values attached to the source (see section below). Please refer to [Mooley et al. 2016](https://ui.adsabs.harvard.edu/abs/2016ApJ...818..105M/abstract) for further details.

!!! note
    All the two-epoch pair $V_s$ and $m$ values for a run are saved in the output file `measurement_pairs.parquet` for offline analysis.

$V_s$ is a statistic to compare the flux densities of a source between two-epochs and is given by:

$$
V_s = \frac{\Delta S}{\sigma} = \frac{S_1 - S_2}{\sqrt{\sigma_{1}^{2} + \sigma_{2}^{2}}}
$$

where $S$ is the flux and $\sigma$ is the associated error. This metric is known to follow a Student-t distribution. Typically, in the literature, a source is defined as variable if this parameter is beyond the 95% confidence interval, i.e.:

$$
\mid V_s \mid \geq 4.3.
$$

$m$ is a moduluation index variable given by:

$$
m = \frac{\Delta S}{\overline{S}}
$$

where $\overline{S}$ is the mean of the flux densities $S_1$ and $S_2$. Typically, in the literature, the threshold for this value for a source to be considered variable is:

$$
\mid m \mid \gt 0.26,
$$

which equates to a variability of 30%. However the user is free to set their own level to define variablity.

#### Significant Source Values

The $V_s$ and $m$ metrics of the 'maximum signficant pair' is attached to the source. 
The maximum significant pair is determind by selecting the most significant $\mid m \mid$ value given a minimum $V_s$ threshold which is defined in the pipeline configuration file `SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS`. 
By default this value is set to 4.3. For example, if a source with three associatied measurements gave the following pair metrics:

| Pair | $\mid V_s \mid$ | $\mid m \mid$ |
| ---- | --------------- | ------------- |
| A-B  |       4.5       |      0.1      |
| B-C  |       2.5       |      0.05     |
| A-C  |       4.3       |      0.4      |

then the `A-C` pair metrics are attached to the source as the most significant. This can be used to quickly determine significant two-epoch variability for a source. 
If there are no pair values above the minimum $V_s$ threshold then these values attached to the source will be 0. The `measurement_pairs.parquet` file can be used to manually explore the measurement pairs if one wishes to lower the threshold.
