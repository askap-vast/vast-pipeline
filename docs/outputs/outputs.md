# Pipeline Outputs

This page gives details on the physical files that the pipeline produces and how to access and read them.

## Pipeline Run Output Overview

The output for a pipeline run will be located in the pipeline working directory, which is defined at the pipeline configuration stage (see [Pipeline Configuration](../quickstart/configuration.md#pipeline-configuration)).
A sub-directoy will exist for each pipeline run that contains the output products for the run. 

!!! note
    If you do not administrate your system or do not have access to a `vast-tools` notebook interface, please contact your system admin to confirm the working directory and how to best access the files.

The pipeline uses the [Apache Parquet](https://parquet.apache.org) file format to write results to disk. Details on how to read these files can be found below in [Reading the Outputs](#reading-the-outputs).

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
A solution to this is to save all the measurements associated with the pipeline run into one single file in the [Apache Arrow](https://arrow.apache.org/overview/) format.

The library `vaex` is able to open `.arrow` files in an out-of-core context so the memory footprint is hugely reduced along with the reading of the file being very fast.
The two-epoch measurement pairs are also saved to arrow format due to the same reasons. See [Reading with vaex](#reading-with-vaex) for further details on using `vaex`.

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

| File | Description |
| ---- | ----------- |
| `associations.parquet` | Contains the association information between sources and measurements.  |
| `bands.parquet` | Contains the information of the bands associated with the pipeline run. |
| `config.py` | The pipeline run configuration file. |
| `config_prev.py` | The previous pipeline run configuration file used by the [add image](../using/addtorun.md) mode. |
| `forced_measurements*.parquet` | Multiple files that contain the forced measurements extracted from the respective image denoted in the filename. |
| `images.parquet` | Contains the information of the images processed in the pipeline run. |
| `log.txt` | The log file of the pipeline run. |
| `measurements.arrow` | An [Apache Arrow](https://arrow.apache.org/overview/) format file containing all the measurements associated with the pipeline run (see [Arrow Files](#arrow-files)).|
| `measurement_pairs.arrow` | An [Apache Arrow](https://arrow.apache.org/overview/) format file containing all the measurement pair metrics (see [Arrow Files](#arrow-files)). |
| `measurement_pairs.parquet` | Contains all the measurement pairs metrics. |
| `relations.parquet` | Contains the relation information between sources. |
| `skyregions.parquet` | Contains the sky region information of the pipeline run. |
| `sources.parquet` | Contains all the sources resulting from teh pipeline run. |

## Reading the Outputs

It is recommended to use `pandas` or `vaex` to read the pipeline results from the parquet files. See the sections below for more information on using each library.

!!! note
    It is also possible to use [`Dask`](https://docs.dask.org/en/latest/) to read the parquets in an out-of-core context but the general performace can sometimes be poor with many parquet files. 
    `vaex` is the preferred out-of-core method.
    
!!! tip
    Be sure to look at [`vast-tools`](#vast-tools), a ready-made library for exploring pipeline results!

### Reading with pandas

[pandas documentation](https://pandas.pydata.org/docs/).

!!! warning
    `pyarrow` will be required to open parquets with `pandas`. We recommend using this instead of `fastparquet`.

To open a parquet using `pandas` use the `read_parquet` method:
    
```python
import pandas as pd

sources = pd.read_parquet('pipeline-runs/new-test-data/sources.parquet')

sources.head()
    n_meas_forced  n_meas  ...  vs_abs_significant_max_int  m_abs_significant_max_int
id                         ...
1               0       3  ...                   55.050146                   0.191083
2               1       3  ...                   29.367098                   0.525999
3               0       3  ...                    4.388447                   0.199877
4               1       3  ...                   20.000058                   1.047998
5               0       3  ...                    0.000000                   0.000000

[5 rows x 31 columns]
```

To read multiple parquets at once using `pandas` a loop must be used:

```python
import glob
import pandas as pd

files = glob.glob("pipeline-runs/images/*/measurements.parquet")
data = [pd.read_parquet(f) for f in files]
measurements = pd.concat(data, ignore_index=True)
```

!!! tip
    If you don't require all the columns you can specify which columes to read using the `columns` variable.
    
    ```python
    sources = pd.read_parquet('pipeline-runs/new-test-data/sources.parquet', columns=['id', 'n_meas'])
    ```

### Reading with vaex

[vaex documentation](https://vaex.io/docs/index.html).

!!! warning
    vaex is a young project so bugs may be expected along with frequent updates. It has currently been tested with version `3.0.0`. 
    Version `4.0.0` promises opening parquet files in an out-of-core context.

!!! warning
    Some pipeline `parquet` format files do not open with vaex 3.0.0. `arrow` format files should open successfully.

A parquet, or arrow file, can be opened using the `open()` method:

```python
import vaex

measurements = vaex.open('pipeline-runs/new-test-data/measurements.arrow')

measurements.head()
  #    source  island_id         component_id            local_rms       ra       ra_err       dec      dec_err    flux_peak    flux_peak_err    flux_int    flux_int_err    bmaj     err_bmaj    bmin     err_bmin      pa      err_pa    psf_bmaj    psf_bmin    psf_pa  flag_c4      chi_squared_fit    spectral_index  spectral_index_from_TT    has_siblings      image_id  time                           name                                    snr    compactness    ew_sys_err    ns_sys_err    error_radius    uncertainty_ew    uncertainty_ns    weight_ew    weight_ns  forced      flux_int_isl_ratio    flux_peak_isl_ratio    id
  0       730  SB00004_island_1  SB00004_component_1a     0.463596  321.902  4.42819e-06  -4.20097  2.2637e-06       307.991         0.4742       425.175        1.04728    20.95  1.08838e-05   12.28  4.32359e-06  108.19  0.00160065       15.58        0       -73.86  False                3516.59               -99  True                      True                     2  2019-08-27 13:38:38.810000000  VAST_2118+00A_SB00004_component_1a  664.352       1.38048    0.000277778   0.000277778     5.05099e-06       0.000277824       0.000277824  1.29557e+07  1.29557e+07  False                 0.651019               0.709182   204
  1       730  SB00009_island_1  SB00009_component_1a     0.463422  321.902  3.52062e-06  -4.20103  2.45968e-06      318.544         0.472982     349.471        0.87264    21.4   8.50698e-06   12.78  5.46908e-06  107.02  0.0020224         5.72        0        46.03  True                15427.1                -99  True                      True                     3  2019-08-27 18:52:00.556000000  VAST_2118-06A_SB00009_component_1a  687.374       1.09709    0.000277778   0.000277778     4.26887e-06       0.000277811       0.000277811  1.29569e+07  1.29569e+07  False                 0.721399               0.7483     352
  2       730  SB00006_island_1  SB00006_component_1a     0.627357  321.901  4.58076e-06  -4.20086  2.92861e-06      310.503         0.662503     421.137        1.4171     17.05  1.07873e-05   12.42  6.89559e-06   90.71  0.00438684       10.51        4.24    -82.52  False                4483.74               -99  True                      True                     5  2019-10-29 10:28:07.911000000  VAST_2118+00A_SB00006_component_1a  494.938       1.35631    0.000277778   0.000277778     5.46682e-06       0.000277832       0.000277832  1.2955e+07   1.2955e+07   False                 0.677562               0.721427   670
  3       730  SB00011_island_1  SB00011_component_1a     0.627496  321.901  3.92144e-06  -4.20087  3.21715e-06      310.998         0.643049     350.901        1.21083    17.06  9.23494e-06   12.43  7.57501e-06   91.19  0.00481863        6.43        0        27.62  False                4405.81               -99  True                      True                     4  2019-10-29 13:39:33.996000000  VAST_2118-06A_SB00011_component_1a  495.618       1.12831    0.000277778   0.000277778     5.05099e-06       0.000277824       0.000277824  1.29557e+07  1.29557e+07  False                 0.677576               0.721816   511
  4       730  SB00005_island_1  SB00005_component_1a     0.346147  321.901  1.83032e-06  -4.20051  1.71797e-06      299.072         0.342783     288.462        0.579893   14.13  4.37963e-06   12.14  3.97013e-06   65.14  0.00546325        2.86        0         6.42  False                2661.49               -99  True                      True                     7  2019-10-30 09:10:04.340000000  VAST_2118+00A_SB00005_component_1a  864.004       0.964524   0.000277778   0.000277778     2.69987e-06       0.000277791       0.000277791  1.29588e+07  1.29588e+07  False                 0.659887               0.719556   976
  5       730  SB00010_island_1  SB00010_component_1a     0.347692  321.901  1.97328e-06  -4.20052  1.75466e-06      300.969         0.360198     353.643        0.695754   14.16  4.76862e-06   12.16  3.99059e-06   65.77  0.00546515        6.12        3.95     49.18  False                2412.18               -99  True                      True                     6  2019-10-30 10:11:56.913000000  VAST_2118-06A_SB00010_component_1a  865.62        1.17502    0.000277778   0.000277778     2.56132e-06       0.00027779        0.00027779   1.29589e+07  1.29589e+07  False                 0.664605               0.723765   816
  6       730  SB00007_island_1  SB00007_component_1a     0.387605  321.901  2.03947e-06  -4.20032  1.77854e-06      317.014         0.392106     332.662        0.701451   14.56  4.96382e-06   11.54  3.99573e-06   64.78  0.00375775        4.81        0        24.08  False                1486.99               -99  True                      True                    10  2020-01-11 05:27:24.605000000  VAST_2118+00A_SB00007_component_1a  817.88        1.04936    0.000277778   0.000277778     2.83165e-06       0.000277792       0.000277792  1.29587e+07  1.29587e+07  False                 0.666924               0.716339  1493
  7       730  SB00012_island_1  SB00012_component_1a     0.391978  321.901  2.12442e-06  -4.20032  1.81129e-06      318.042         0.404457     365.987        0.770202   14.57  5.18203e-06   11.53  4.0454e-06    65.33  0.00378202        5.75        3.63     46.53  False                1328.58               -99  True                      True                     9  2020-01-11 05:40:11.007000000  VAST_2118-06A_SB00012_component_1a  811.376       1.15075    0.000277778   0.000277778     2.69987e-06       0.000277791       0.000277791  1.29588e+07  1.29588e+07  False                 0.667317               0.717746  1330
  8       730  SB00008_island_1  SB00008_component_1a     0.432726  321.901  2.98443e-06  -4.20052  2.32201e-06      293.737         0.436863     309.072        0.784657   18.35  7.14713e-06   12.12  5.31097e-06  105.78  0.00261377        4.82        0        18.62  False                2448.82               -99  True                      True                    13  2020-01-12 05:23:07.478000000  VAST_2118+00A_SB00008_component_1a  678.807       1.05221    0.000277778   0.000277778     3.81819e-06       0.000277804       0.000277804  1.29576e+07  1.29576e+07  False                 0.63994                0.725001  1889
  9       730  SB00013_island_1  SB00013_component_1a     0.437279  321.901  3.14407e-06  -4.20052  2.36161e-06      294.141         0.451346     340.92         0.864347   18.38  7.55055e-06   12.12  5.36009e-06  106.18  0.00262701        6.01        4        51.55  False                2368.93               -99  True                      True                    12  2020-01-12 05:36:03.834000000  VAST_2118-06A_SB00013_component_1a  672.663       1.15903    0.000277778   0.000277778     4.00455e-06       0.000277807       0.000277807  1.29573e+07  1.29573e+07  False                 0.640807               0.72508   1740
```

Multiple parquet files can be opened at once using the `open_many()` method:

```python
import glob
import vaex

files = glob.glob("pipeline-runs/images/*/measurements.parquet")
measurements = vaex.open_many(files)
```

!!! tip
    You can convert a vaex dataframe to pandas by using the `to_pandas_df()` method:
    ```python
    import vaex

    sources = vaex.open('pipeline-runs/new-test-data/sources.parquet')
    sources = sources.to_pandas_df()
    ```

### Linking the Results

The table below shows what parameters act as keys to link data from the different results tables.

!!! tip
    If loading the measurements via the `.arrow` file, then the measurements already have the `source` column in-place.

!!! tip
    The `images.parquet` file contains the column `measurements_path` which can be used to get the filepaths for all the selavy `parquet` files.

| Data | Column | Linked to | Column |
| ---- | ------ | --------- | ------ |
| `associations.parquet` | `meas_id` | `measurements.parquet`, `forced_measurements*.parquet` | `id` |
| `associations.parquet` | `source_id` | `sources.parquet` | `id` |
| `measurements.parquet`, `forced_measurements*.parquet` | `image_id` | `images.parquet` | `id` |
| `images.parquet` | `band_id` | `bands.parquet` | `id` |
| `images.parquet` | `skyreg_id` | `skyregions.parquet` | `id` |
| `measurement_pairs.parquet` | `meas_id_a`, `meas_id_b` | `measurements.parquet`, `forced_measurements*.parquet` | `id` |
| `relations.parquet` | `from_source_id`, `to_source_id` | `measurements.parquet`, `forced_measurements*.parquet` | `id` |

## vast-tools

[Link to the `vast-tools` repository](https://github.com/askap-vast/vast-tools).

VAST has developed a python library called `vast-tools` that makes the exploration of results from the pipeline simple and efficient, in addition to being designed to be used in a [Jupyter Notebook](https://jupyter.org) environment. 

For full details, refer to the repository located on [GitHub](https://github.com/askap-vast/vast-tools) and be sure to take a look at the [example notebooks](https://github.com/askap-vast/vast-tools/tree/master/notebook-examples).
