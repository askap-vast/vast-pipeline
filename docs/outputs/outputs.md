<!-- markdownlint-disable html -->
# Outputs Overview

This page gives details on the output files that the pipeline writes to disk.

## Pipeline Run Output Overview

The output for a pipeline run will be located in the pipeline working directory, which is defined at the pipeline configuration stage (see [Pipeline Configuration](../gettingstarted/configuration.md#pipeline-configuration)).
A sub-directory will exist for each pipeline run that contains the output products for the run.

!!! note
    If you do not administrate your system or do not have access to a `vast-tools` notebook interface, please contact your system admin to confirm the working directory and how to best access the files.

The pipeline uses the [Apache Parquet](https://parquet.apache.org){:target="_blank"} file format to write results to disk. Details on how to read these files can be found below in [Reading the Outputs](#reading-the-outputs).

Below is the output structure for a pipeline run named `new-test-data` when the pipeline run option `measurements.write_parquet_files` has been set to `True` and the working directory is named `pipeline-runs` (see [File Details](#file-details) for descriptions):

```bash
pipeline-runs
├── new-test-data
│   ├── associations.parquet
│   ├── bands.parquet
│   ├── config.yaml
│   ├── config_prev.yaml
│   ├── forced_measurements_VAST_0127-73A_EPOCH01_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_0127-73A_EPOCH05x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_0127-73A_EPOCH06x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118+00A_EPOCH01_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118+00A_EPOCH02_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118+00A_EPOCH03x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118+00A_EPOCH05x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118+00A_EPOCH06x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118-06A_EPOCH01_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118-06A_EPOCH02_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118-06A_EPOCH03x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118-06A_EPOCH05x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118-06A_EPOCH06x_I_cutout_fits.parquet
│   ├── forced_measurements_VAST_2118-06A_EPOCH12_I_cutout_fits.parquet
│   ├── images.parquet
│   ├── YYYY-MM-DD-HH-MM-SS_log.txt
│   ├── measurements.parquet
│   ├── measurement_pairs.parquet
│   ├── measurement_pairs.parquet
│   ├── relations.parquet
│   ├── skyregions.parquet
│   └── sources.parquet
```

### Image Data

The data for the images [ingested](../design/imageingest.md) into the pipeline is also stored in the pipeline working directory under the subdirectory `images`:

```bash
pipeline-runs
├── images
│   ├── VAST_0127-73A_EPOCH01_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_0127-73A_EPOCH05x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_0127-73A_EPOCH06x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118+00A_EPOCH01_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118+00A_EPOCH02_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118+00A_EPOCH03x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118+00A_EPOCH05x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118+00A_EPOCH06x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118-06A_EPOCH01_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118-06A_EPOCH02_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118-06A_EPOCH03x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118-06A_EPOCH05x_I_cutout_fits
│   │   └── measurements.parquet
│   ├── VAST_2118-06A_EPOCH06x_I_cutout_fits
│   │   └── measurements.parquet
│   └── VAST_2118-06A_EPOCH12_I_cutout_fits
│       └── measurements.parquet
```

Here, for each image, the selavy measurements that have been ingested are stored in the parquet format under a subdirectory of the respective image name.

## File Details

| File<img width=300/>  | Description |
| ---- | ----------- |
| `associations.parquet` | Contains the association information between sources and measurements.  |
| `bands.parquet` | Contains the information of the bands associated with the pipeline run. |
| `config.yaml` | The pipeline run configuration file. |
| `config_prev.yaml` | The previous pipeline run configuration file used by the [add image](../using/addtorun.md) mode. |
| `forced_measurements*.parquet` | Multiple files that contain the forced measurements extracted from the respective image denoted in the filename. |
| `images.parquet` | Contains the information of the images processed in the pipeline run. |
| `YYYY-MM-DD-HH-MM-SS_log.txt` | The log file of the pipeline run. It is timestamped with the date and time of the run start. |
| `measurements.parquet` | A [Parquet](https://docs.dask.org/en/latest/dataframe-parquet.html/){:target="_blank"} format file containing all the measurements associated with the pipeline run (see [Arrow Files](#parquet-files)).|
| `measurement_pairs.parquet` | An [Parquet](https://docs.dask.org/en/latest/dataframe-parquet.html){:target="_blank"} format file containing all the measurement pair metrics (see [Arrow Files](#parquet-files)). |
| `measurement_pairs.parquet` | Contains all the measurement pairs metrics. |
| `relations.parquet` | Contains the relation information between sources. |
| `skyregions.parquet` | Contains the sky region information of the pipeline run. |
| `sources.parquet` | Contains all the sources resulting from teh pipeline run. |
