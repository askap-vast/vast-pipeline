# Outputs Overview

This page gives details on the physical files that the pipeline produces.

## Pipeline Run Output Overview

The output for a pipeline run will be located in the pipeline working directory, which is defined at the pipeline configuration stage (see [Pipeline Configuration](../quickstart/configuration.md#pipeline-configuration)).
A sub-directoy will exist for each pipeline run that contains the output products for the run. 

!!! note
    If you do not administrate your system or do not have access to a `vast-tools` notebook interface, please contact your system admin to confirm the working directory and how to best access the files.

The pipeline uses the [Apache Parquet](https://parquet.apache.org){:target="_blank"} file format to write results to disk. Details on how to read these files can be found below in [Reading the Outputs](#reading-the-outputs).

Below is the output structure for a pipeline run named `new-test-data` when the pipeline run option `CREATE_MEASUREMENTS_ARROW_FILES` has been set to `True` and the working directory is named `pipeline-runs` (see [File Details](#file-details) for descriptions):

```bash
pipeline-runs
├── new-test-data
│   ├── associations.parquet
│   ├── bands.parquet
│   ├── config.py
│   ├── config_prev.py
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
│   ├── log.txt
│   ├── measurements.arrow
│   ├── measurement_pairs.arrow
│   ├── measurement_pairs.parquet
│   ├── relations.parquet
│   ├── skyregions.parquet
│   └── sources.parquet
```

### Arrow Files
Large pipeline runs (hundreds of images) mean that to read the measurements, hundreds of parquet files need to be read in, and can contain millions of rows. 
This can be slow using libraries such as pandas, and also consumes a lot of system memory. 
A solution to this is to save all the measurements associated with the pipeline run into one single file in the [Apache Arrow](https://arrow.apache.org/overview/){:target="_blank"} format.

The library `vaex` is able to open `.arrow` files in an out-of-core context so the memory footprint is hugely reduced along with the reading of the file being very fast.
The two-epoch measurement pairs are also saved to arrow format due to the same reasons. See [Reading with vaex](usingoutputs.md#reading-with-vaex) for further details on using `vaex`.

!!! note
    At the time of development `vaex` could not open parquets in an out-of-core context. This will be reviewed in the future if such functionality is added to `vaex`.

To enable the arrow files to be produced, the option `CREATE_MEASUREMENTS_ARROW_FILES` is required to be set to `True` in the pipeline run config.

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
| `config.py` | The pipeline run configuration file. |
| `config_prev.py` | The previous pipeline run configuration file used by the [add image](../using/addtorun.md) mode. |
| `forced_measurements*.parquet` | Multiple files that contain the forced measurements extracted from the respective image denoted in the filename. |
| `images.parquet` | Contains the information of the images processed in the pipeline run. |
| `log.txt` | The log file of the pipeline run. |
| `measurements.arrow` | An [Apache Arrow](https://arrow.apache.org/overview/){:target="_blank"} format file containing all the measurements associated with the pipeline run (see [Arrow Files](#arrow-files)).|
| `measurement_pairs.arrow` | An [Apache Arrow](https://arrow.apache.org/overview/){:target="_blank"} format file containing all the measurement pair metrics (see [Arrow Files](#arrow-files)). |
| `measurement_pairs.parquet` | Contains all the measurement pairs metrics. |
| `relations.parquet` | Contains the relation information between sources. |
| `skyregions.parquet` | Contains the sky region information of the pipeline run. |
| `sources.parquet` | Contains all the sources resulting from teh pipeline run. |
