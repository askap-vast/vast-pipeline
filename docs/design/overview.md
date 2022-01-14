# Pipeline Steps Overview

This page gives an overview of the processing steps of a pipeline run. Each section contains a link to a feature page that contains more details.

## Terminology

**`Run`**  
A single pipeline dataset defined by a configuration file.

**`Image`**  
A FITS image that is being processed as part of a pipeline run. It also has related inputs of the selavy source catalogue, and the noise and background images also produced by selavy.

**`Measurement`**  
An extracted measurement read from the selavy source catalogue from an associated image. The only measurements produced by the pipeline are `forced measurements` which are performed when monitoring is used.

**`Source`**  
A group of measurements that have been identified as the same astrophysical source by a pipeline association method.

## Pipeline Processing Steps

!!! note
    Each pipeline run is self-aware only, which means that each run does not draw on the results of other runs. However, since images and their measurements don't change, subsequent runs that use any image that was ingested as part of a previous run will not be ingested again.

### 1. Image & Selavy Catalogue Ingest
Full details: [Image & Selavy Catalogue Ingest](imageingest.md).

The first stage of the pipeline is to read and ingest to the database the input data that has been provided in the configuration file. This includes determing statistics about the image footprint and properties, and also importing and cleaning the associated measurements from the selavy file. The errors on the measurements can also be recalculated at this stage based upon the [Condon (1997)](https://doi.org/10.1086/133871){:target="_blank"} method.

Image uniqueness is determined by the filename, and once the image is ingested, it is available for other pipeline runs to use without having to re-ingest.

### 2. Source Association
Full details: [Source Association](association.md).

Once all images and measurments have been ingested the source association step is performed, where measurements over time are associated to a unique astrophysical source. Images are arranged chronologically and association is performed on an image by image basis, or as a grouped "epoch" if epoch based association is used. The association is performed as per the settings entered in the run configuration file.

### 3. Ideal Coverage & New Source Analysis
Full details: [New Sources](newsources.md).

With the measurements associated the sources are analysed to check for non-detections over time and whether the source should have been seen in any non-detection images. The ideal coverage calculation is also used to determine any sources that should be marked as `new`, i.e. a source that has appeared over time that was not detected in the first image of its location on the sky. The non-detections are then passed to the forced monitoring step.

### 4. Monitoring Forced Measurements
Full details: [Forced Measurements](monitor.md).

This step is optional. The non-detections which form gaps in the lightcurves of each source are filled in by forcefully extracting a flux measurement at the location of the source.

### 5. Source Statistics Calculation
Full details: [Source Statistics](sourcestats.md).

Statistics are calculated for each source such as the weighted average sky position, average flux values, variability metrics (including two-epoch pair metrics) and various counts.

### 6. Database Upload
All the results from the pipeline run are uploaded to the database. Specifically at the end of the run the following is written to the database:

* Sources and their statistics.
* Relations between sources.
* Associations.

For large runs this can be a substantial component of the pipeline run time.
`Bulk upload` statements will be seen in the pipeline run log file such as these shown below:

!!! example "2021-03-11-12-48-21_log.txt"
    ```console
    2021-03-11 13:00:04,893 loading INFO Bulk created #557 Source
    2021-03-11 13:00:04,910 loading INFO Populate "related" field of sources...
    2021-03-11 13:00:04,919 loading INFO Bulk created #29 RelatedSource
    2021-03-11 13:00:04,943 loading INFO Upload associations...
    2021-03-11 13:00:05,650 loading INFO Bulk created #3276 Association
    ```
