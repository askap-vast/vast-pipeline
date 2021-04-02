# New Sources

This page details the new source analysis performed by the pipeline.

## Definition

A `new source` is defined as a source that is detected during the pipeline run that was **not detected** in any previous epoch of the location of the source, and has a peak flux such that it should have been detected.

!!! note
    Remember that pipeline runs are self-contained - i.e. a run does not have any knowledge of another run, hence new sources are local to their pipeline run.

## New Source Process

The pipeline identifies new sources by using the following steps:

1. Sources are found that have 'incomplete' light curves, i.e. there are epochs in the pipeline run of the source location where the source is not detected.
    The would-be 'ideal' coverage is then calculated to determine which images contain the source location but have a non-detection.
2. Remove sources where the epoch of the first detection is also the earliest possible detection epoch.
3. For the remaining sources a general rms check is made to answer the question of should this source be expected to be detected at all in the previous epochs. This is done by taking the minimum $\text{rms}_{min}$ of all the non-detection images and making sure that 

    $$
    \frac{f_{peak,det}}{\text{minimum rms}_{min}} > \text{new_sources.min_sigma},
    $$

    where $f_{peak,det}$ is the peak flux density of the first detection of the source. The default value of `new_sources.min_sigma` is 5.0, but the parameter can be controlled by the user in the pipeline run configuration file.

4. The sources that meet the above criteria are marked as a `new source`.
5. The `new source high sigma` value is calculated for all new sources.

## New Source High Sigma

In the process detailed above, the rms check is made against the minimum rms of the previous non-detection images. This might not be an accurate representation of the rms at the source's actual location in the image, for example, the rms might be high at the source location such that a detection of the source wouldn't be expected at the $5\sigma$ level.

To account for this the `new source high sigma` value is calculated for all new sources. For each non-detection image for a source, the true signal-to-noise ratio the source would have in the non-detection image is calculated, i.e.

$$
\text{new source true sigma}_i = \frac{f_{peak,det}}{\text{rms}_{location,i}}
$$

where $\text{rms}_{location,i}$ is the rms at the source location for each non-detection image, $i$.

The `new source high sigma` is then equal to the maximum $\text{rms}_{location,i}$. The value can be used to filter those new sources which would be borderline detections, or not expected to be detected at all, at the actual location in the previous images. This allows users to concentrate on the significant new sources.

## Viewing New Sources

New sources are marked as new on the website interface (see [Source Pages](../exploringwebsite/sourcepages.md)) and in the source parquet file output there is a boolean column named `new`.
