import os
import logging
import datetime
import gc
import numpy as np
import pandas as pd
import dask.dataframe as dd
import dask.bag as db
from glob import glob

from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from django.db import transaction
from pyarrow.parquet import read_schema
from typing import List, Tuple, Dict, Optional
from dask.delayed import delayed
from dask.distributed import wait

from vast_pipeline.models import Image, Measurement, Run
from vast_pipeline.pipeline.loading import copy_upload_measurements

from forced_phot import ForcedPhot
from ..utils.utils import (
    StopWatch,
    generate_shortuuid,
    UUID_LEN_MEAS
)
from vast_pipeline.image.utils import open_fits

# NOTE: We check here to see if we're in a testing environment.
# This is done since the django does all its testing inside an
# 'atomic' transaction to separate the tests from one another.
# This has the unfortunate side-effect of causing uploads to
# the database to fail in threaded/multiprocessing applications
# since only the original thread can see whats previously been
# uploaded to the database. The solution is to check if we are
# inside a test environment and disable the database upload in
# that case.
__TESTING__ = settings.TESTING

logger = logging.getLogger(__name__)

def remove_forced_meas(run_path: str) -> None:
    """
    Remove forced measurements from the database if forced parquet files
    are found.

    Args:
        run_path:
            The run path of the pipeline run.

    Returns:
        None
    """
    path_glob = glob(os.path.join(run_path, "forced_measurements_*.parquet"))
    if path_glob:
        ids = dd.read_parquet(path_glob, columns="id").values.compute().tolist()
        obj_to_delete = Measurement.objects.filter(id__in=ids)
        del ids
        if obj_to_delete.exists():
            with transaction.atomic():
                n_del, detail_del = obj_to_delete.delete()
                logger.info(
                    (
                        "Deleting all previous forced measurement and association"
                        " objects for this run. Total objects deleted: %i"
                    ),
                    n_del,
                )
                logger.debug("(type, #deleted): %s", detail_del)


def get_data_from_parquet(
    file_and_image_id: Tuple[str, int], p_run_path: str, add_mode: bool = False
) -> Dict:
    """
    Get the prefix, max id and image id from the measurements parquets

    Args:
        file_and_image_id:
            a tuple containing the path of the measurements parquet file and
            the image ID.
        p_run_path:
            Pipeline run path to get forced parquet in case of add mode.
        add_mode:
            Whether image add mode is being used where the forced parquet
            needs to be used instead.

    Returns:
        Dictionary with prefix string, an interger max_id and a string with the
            id of the image.
    """
    file, image_id = file_and_image_id
    if add_mode:
        image_name = file.split("/")[-2]
        forced_parquet = os.path.join(
            p_run_path, f"forced_measurements_{image_name}.parquet"
        )
        if os.path.isfile(forced_parquet):
            file = forced_parquet
    # get max component id from parquet file
    df = pd.read_parquet(file, columns=["island_id", "image_id"])
    if len(df) > 0:
        prefix = df["island_id"].iloc[0].rsplit("_", maxsplit=1)[0] + "_"
        max_id = (
            df["island_id"].str.rsplit("_", n=1).str.get(-1).astype(int).values.max()
            + 1
        )
    else:
        prefix = "island_"
        max_id = 1
    return {"prefix": prefix, "max_id": max_id, "id": image_id}


def _forcedphot_preload(image: str,
                        background: str,
                        noise: str,
                        memmap: Optional[bool] = False
                        ):
    """
    Load the relevant image, background and noisemap files.

    Args:
        image: a string with the path of the image file
        background: a string with the path of the background map
        noise: a string with the path of the noise map

    Returns:
        A tuple containing the HDU lists
    """

    image_hdul = open_fits(image, memmap=memmap)
    background_hdul = open_fits(background, memmap=memmap)
    noise_hdul = open_fits(noise, memmap=memmap)

    return image_hdul, background_hdul, noise_hdul


def extract_from_image(
    df: pd.DataFrame,
    data: pd.DataFrame,
    edge_buffer: float,
    cluster_threshold: float,
    allow_nan: bool,
    **kwargs,
) -> Dict:
    """
    Extract the flux, its errors and chi squared data from the image
    files (image FIT, background and noise files) and return a dictionary
    with the dataframe and image name

    Args:
        df:
            input dataframe with columns [source_tmp_id, wavg_ra, wavg_dec,
            image_name, flux_peak]
        data:
            dataframe with columns pointing to image paths
        edge_buffer:
            flag to pass to ForcedPhot.measure method
        cluster_threshold:
            flag to pass to ForcedPhot.measure method
        allow_nan:
            flag to pass to ForcedPhot.measure method

    Returns:
        Dictionary with input dataframe with added columns (flux_int,
            flux_int_err, chi_squared_fit) and image name.
    """
    timer = StopWatch()

    data = data.to_dict(orient='records')[0]
    image = data.pop('path')
    # create the skycoord obj to pass to the forced extraction
    # see usage https://github.com/dlakaplan/forced_phot
    P_islands = SkyCoord(
        df["wavg_ra"].to_numpy(), df["wavg_dec"].to_numpy(), unit=(u.deg, u.deg)
    )

    num_sources = len(df)
    logger.debug("Will fit %d sources for %s...", num_sources, image)

    # load the image, background and noisemaps into memory
    # a dedicated function may seem unneccesary, but will be useful if we
    # split the load to a separate thread.
    forcedphot_input = _forcedphot_preload(image,
                                           data.pop('background_path'),
                                           data.pop('noise_path'),
                                           memmap=False
                                           )
    FP_timer = StopWatch()
    FP = ForcedPhot(*forcedphot_input, use_numba=True)
    logger.debug("%s - Time to init FP: %.3f s", image,  FP_timer.reset())

    # This should ultimately be removed in v2, but for now I am keeping the
    # option to use clustering in order to keep things backward-compatible.
    # NOTE: PR #816 is the V2 upgrade - but I'm leaving this as is for now
    # while the best way to do this is worked out.
    use_clusters = True
    if cluster_threshold == 0:
        use_clusters = False

    flux, flux_err, chisq, DOF, cluster_id = FP.measure(
        P_islands,
        cluster_threshold=cluster_threshold,
        allow_nan=allow_nan,
        edge_buffer=edge_buffer,
        use_clusters=use_clusters
    )
    logger.debug("%s - Time to measure FP: %.3fs", image, FP_timer.reset())
    
    num_fits = np.sum(flux>0.0)

    logger.debug("%s: Obtained %d measurements "
                 "(%d sources outside of image range)."
                 ,image ,num_fits ,num_sources-num_fits)

    df['flux_int'] = flux * 1.e3
    df['flux_int_err'] = flux_err * 1.e3
    df['chi_squared_fit'] = chisq
    
    values = {
        'flux_int': 0,
        'flux_int_err': 0
    }
    df = df.fillna(value=values)

    df = df[
        (df['flux_int'] != 0)
        & (df['flux_int_err'] != 0)
        & (df['chi_squared_fit'] != np.inf)
        & (df['chi_squared_fit'] != np.nan)
    ]

    df = finalise_forced_dfs(df, **data)

    logger.debug("%s - Total extraction time: %ds", image, timer.reset())

    return df


def finalise_forced_dfs(
    df: pd.DataFrame,
    prefix: str,
    max_id: int,
    beam_bmaj: float,
    beam_bmin: float,
    beam_bpa: float,
    id: int,
    datetime: datetime.datetime,
) -> pd.DataFrame:
    """
    Compute populate leftover columns for the dataframe with forced
    photometry data given the input parameters

    Args:
        df:
            input dataframe with columns [source_tmp_id, wavg_ra, wavg_dec,
            image_name, flux_peak, flux_int, flux_int_err, chi_squared_fit]
        prefix:
            string to use to generate the 'island_id' column
        max_id:
            integer to use to generate the 'island_id' column
        beam_bmaj:
            image beam major axis
        beam_bmin:
            image beam minor axis
        beam_bpa:
            image beam position angle
        id:
            image id in database
        datetime:
            timestamp of the image file (from header)

    Returns:
        Input dataframe with added columns island_id, component_id,
            name, bmaj, bmin, pa, image_id, time.
    """

    image = df['image_name'].iloc[0]
    # make up the measurements name from the image island_id and component_id
    df["island_id"] = np.char.add(
        prefix, np.arange(max_id, max_id + df.shape[0]).astype(str)
    )
    df["component_id"] = df["island_id"].str.replace("island", "component") + "a"
    img_prefix = image.split(".")[0] + "_"
    df["name"] = img_prefix + df["component_id"]
    # assign all the other columns
    # convert fluxes to mJy
    # store source bmaj and bmin in arcsec
    df["bmaj"] = beam_bmaj * 3600.0
    df["bmin"] = beam_bmin * 3600.0
    df["pa"] = beam_bpa
    # add image id and time
    df["image_id"] = id
    df["time"] = datetime

    df = df.rename(columns={'wavg_ra': 'ra', 'wavg_dec': 'dec', 'image_name': 'image'})

    return df


def parallel_extraction(
    df: pd.DataFrame,
    df_images: pd.DataFrame,
    df_sources: pd.DataFrame,
    min_sigma: float,
    edge_buffer: float,
    cluster_threshold: float,
    allow_nan: bool,
    add_mode: bool,
    p_run_path: str,
    io_workers: List[str],
) -> dd.DataFrame:
    """
    Parallelize forced extraction with Dask

    Args:
        df:
            dataframe with columns 'wavg_ra', 'wavg_dec', 'img_diff',
            'detection'
        df_images:
            dataframe with the images data and columns 'id',
            'measurements_path', 'path', 'noise_path', 'beam_bmaj',
            'beam_bmin', 'beam_bpa', 'background_path', 'rms_min', 'datetime',
            'skyreg__centre_ra', 'skyreg__centre_dec', 'skyreg__xtr_radius'
            and 'name' as the index.
        df_sources:
            dataframe derived from the measurement data with columns 'source',
            'image', 'flux_peak'.
        min_sigma:
            minimum sigma value to drop forced extracted measurements.
        edge_buffer:
            flag to pass to ForcedPhot.measure method.
        cluster_threshold:
            flag to pass to ForcedPhot.measure method.
        allow_nan:
            flag to pass to ForcedPhot.measure method.
        add_mode:
            True when the pipeline is running in add image mode.
        p_run_path:
            The system path of the pipeline run output.
        io_workers:
            List of dask worker addresses to use for `extract_from_image`
            This is the output of `DaskManager.get_n_random_workers()`, or similar.

    Returns:
        Dataframe with forced extracted measurements data, columns are
            'source_tmp_id', 'ra', 'dec', 'image', 'flux_peak', 'island_id',
            'component_id', 'name', 'flux_int', 'flux_int_err'
    """

    logger.info("Starting parallel extraction")

    # explode the lists in 'img_diff' column (this will make a copy of the df)
    # NOTE: Need to persist here since Dask loses futures after all the
    # previous merges. Ideally this should be removed and we only persist at the
    # end of new_sources.
    out = (
        df.rename(columns={"img_diff": "image", "source": "source_tmp_id"})
        # merge the rms_min column from df_images
        .merge(df_images[["rms_min"]], left_on="image", right_on="name", how="left")
        .rename(columns={"rms_min": "image_rms_min"})
        # merge the measurements columns 'source', 'image', 'flux_peak'
        .merge(
            df_sources,
            left_on=["source_tmp_id", "detection"],
            right_on=["source", "image"],
            how="left",
        )
        .drop(columns=["image_y", "source"])
        .rename(columns={"image_x": "image"})
        .persist()
    )

    logger.info("Generated out df")

    # drop the source for which we would have no hope of detecting
    max_snr = out["flux_peak"].values / out["image_rms_min"].values
    out = out.loc[max_snr > min_sigma].reset_index(drop=True)

    # drop some columns that are no longer needed and the df should look like
    # out
    # |   | source_tmp_id | wavg_ra | wavg_dec | image_name       | flux_peak |
    # |--:|--------------:|--------:|---------:|:-----------------|----------:|
    # | 0 |  223b8Lp4Sdp3 | 317.607 | -8.66952 | VAST_2118-06A... |    11.555 |
    # | 1 |  22LyLU54pBPm | 323.803 | -2.6899  | VAST_2118-06A... |     2.178 |
    # | 2 |  23Vif6cLMQ5C | 316.147 | -3.11408 | VAST_2118-06A... |     6.815 |
    # | 3 |  zzyc7GFJreMg | 322.094 | -4.44977 | VAST_2118-06A... |     1.879 |
    # | 4 |  225RNzDTJ3MR | 321.734 | -6.82934 | VAST_2118-06A... |     1.61  |

    out = out.drop(["image_rms_min", "detection"], axis=1).rename(
        columns={"image": "image_name"}
    )
    logger.info("Dropped low S/N detections")

    # get the unique images to extract from
    unique_images_to_extract = out["image_name"].unique().compute().tolist()

    # create a list of all the measurements parquet files to extract data from,
    # such as prefix and max_id
    list_meas_parquets = list(
        map(
            lambda image_name: (
                df_images.at[image_name, "measurements_path"],
                df_images.at[image_name, "id"],
            ),
            unique_images_to_extract,
        )
    )

    # Get a map of the columns that have a fixed value from the measurements parquets
    # in list_meas_parquets. This generates a list of delayed futures that will only
    # compute at the next persist.
    df_cols = ["id", "path", "background_path", "noise_path", "beam_bmaj", "beam_bmin", "beam_bpa", "datetime"]
    measurements_parquet_data = (
        db.from_sequence(list_meas_parquets, npartitions=len(list_meas_parquets))
        .map(get_data_from_parquet, p_run_path, add_mode)
        .to_dataframe()
        .merge(df_images[df_cols], on="id", how="left")
        .to_delayed()
    )
    logger.info("Generated delayed measurements_parquet_Data")

    # Create a list of dataframes containing the relevant data from out per image
    # This generates a list of delayed futures that will only  compute at the next persist.
    generate_df = lambda name, out: out[out["image_name"] == name]
    df_per_image=[delayed(generate_df)(n, out) for n in unique_images_to_extract]

    # Do the forced extraction work by combining the two delayed lists above then
    # running extract_from_image on the tuple of delayed futures.
    # Persist at this point uning the number of io workers.
    image_data_list = zip(df_per_image, measurements_parquet_data)
    func_d = [
        delayed(extract_from_image)(image_df, meas_data, edge_buffer=edge_buffer,
                                    cluster_threshold=cluster_threshold, allow_nan=allow_nan)
        for image_df, meas_data in image_data_list
        ]
    logger.info("Generated forced extraction delayed")

    # Persist at this point uning the number of io workers.
    # df_out will contain the forced extraction measurments per image.
    # df_out should be sorted and partitioned by image at this point.
    df_out = dd.from_delayed(func_d).persist(workers=io_workers)
    
    logger.info("Persisted forced extraction df")

    del out, func_d, df_per_image, measurements_parquet_data
    
    wait(df_out)
    
    logger.info("Waiting for forced extraction df to finish compute")

    return df_out


def save_and_upload_forced_df(forced_df: pd.DataFrame,
                              p_run_path: str,
                              p_run_id: str,
                              add_mode: bool,
                              columns: List[str],
                              output_columns: List[str],
                              cfg_err_ra: float,
                              cfg_err_dec: float,
                              do_upload: bool = True):
    """
    Upload the forced extraction measurements to the database and save
    them to parquets.

    Args:
        forced_df:
            Dataframe containing the forced extracted measurements.
            This should be sorted and partitioned by filename.
        p_run_path:
            The system path of the pipeline run output.
        p_run_id:
            ID of the pipeline run.
            Used to generate forced extraction source names.
        add_mode:
            True when the pipeline is running in add image mode.
        columns:
            List of expected columns from the database schema.
        output_columns:
            List of output columns expected for concat into sources_df
        cfg_err_ra:
            The minimum RA error from the config file (in degrees).
        cfg_err_dec:
            The minimum declination error from the config file (in degrees).
        do_upload:
            If True - do the db upload step.
    """

    def _update_forced_measurements(df: pd.DataFrame) -> pd.DataFrame:
        """
        Update forced extraction dataframe with defaults.

        Args:
            df:
                The forced extraction dataframe.

        Returns:
            The forced extraction dataframe updated with defaults.
        """
        df["name"] = df["name"] + f"_f_{p_run_id}"
        df["id"] = df.apply(lambda _: generate_shortuuid(UUID_LEN_MEAS), axis=1)
        default_pos_err = settings.POS_DEFAULT_MIN_ERROR / 3600.0
        df["ra_err"] = default_pos_err
        df["dec_err"] = default_pos_err
        df["err_bmaj"] = 0.0
        df["err_bmin"] = 0.0
        df["err_pa"] = 0.0
        df["ew_sys_err"] = cfg_err_ra
        df["ns_sys_err"] = cfg_err_dec
        df["error_radius"] = 0.0

        df["uncertainty_ew"] = np.hypot(cfg_err_ra, default_pos_err)
        df["weight_ew"] = 1.0 / df["uncertainty_ew"].values ** 2
        df["uncertainty_ns"] = np.hypot(cfg_err_dec, default_pos_err)
        df["weight_ns"] = 1.0 / df["uncertainty_ns"].values ** 2

        df["flux_peak"] = df["flux_int"]
        df["flux_peak_err"] = df["flux_int_err"]
        df["local_rms"] = df["flux_int_err"]
        df["snr"] = df["flux_peak"].values / df["local_rms"].values
        df["spectral_index"] = 0.0
        df["dr"] = 0.0
        df["d2d"] = 0.0
        df["forced"] = True
        df["compactness"] = 1.0
        df["psf_bmaj"] = df["bmaj"]
        df["psf_bmin"] = df["bmin"]
        df["psf_pa"] = df["pa"]
        df["flag_c4"] = False
        df["spectral_index_from_TT"] = False
        df["has_siblings"] = False
        df["flux_int_isl_ratio"] = 1.0
        df["flux_peak_isl_ratio"] = 1.0

        return df

    forced_df = _update_forced_measurements(forced_df)
    remaining = list(set(forced_df.columns) - set(columns))
    forced_df = forced_df[columns + remaining]

    if do_upload:
        copy_upload_measurements(forced_df)

    forced_df = forced_df.rename(columns={"source_tmp_id": "source"})

    write_forced_parquet(forced_df, run_path=p_run_path, add_mode=add_mode)

    # Required to rename this column for the image add mode.
    forced_df = forced_df.rename(columns={"time": "datetime"})

    # Add the ["NULL"] related column
    forced_df["related"] = "NULL"
    forced_df["related"] = forced_df["related"].apply(lambda x: [x,])

    return forced_df[output_columns]


def write_forced_parquet(
        df: pd.DataFrame, run_path: str, add_mode: bool = False) -> None:
    """
    Write a single parquet file per image for forced measurements.

    Args:
        df:
            Dataframe containing the extracted measurements for a single image.
        run_path:
            The run path of the pipeline run.
        add_mode:
            True when the pipeline is running in add image mode.

    Returns:
        None
    """
    image = df["image"].unique().tolist()
    # Ensure our dataframe only has one image
    assert len(image) == 1
    image = image[0]

    fname = os.path.join(
        run_path, "forced_measurements_" + image.replace(".", "_") + ".parquet"
    )
    out_df = df.drop(["d2d", "dr", "source", "image"], axis=1)
    if os.path.isfile(fname) and add_mode:
        exist_df = pd.read_parquet(fname)
        out_df = pd.concat([exist_df, out_df])
    out_df.to_parquet(fname, index=False)


def forced_extraction(
    sources_df: dd.DataFrame,
    cfg_err_ra: float,
    cfg_err_dec: float,
    p_run: Run,
    extr_df: dd.DataFrame,
    min_sigma: float,
    edge_buffer: float,
    cluster_threshold: float,
    allow_nan: bool,
    add_mode: bool,
    done_images_df: pd.DataFrame,
    done_source_ids: List[int],
    io_workers: List[str],
) -> Tuple[pd.DataFrame, int]:
    """
    Check and extract expected measurements, and associated them with the
    related source(s).

    Args:
        sources_df:
            Dataframe containing all the extracted measurements and
            associations (product from association step).
        cfg_err_ra:
            The minimum RA error from the config file (in degrees).
        cfg_err_dec:
            The minimum declination error from the config file (in degrees).
        p_run:
            The pipeline run object.
        extr_df:
            The dataframe containing the information on what sources are
            missing from which images (output from
            get_src_skyregion_merged_df in main.py).
        min_sigma:
            Minimum sigma value to drop forced extracted measurements.
        edge_buffer:
            Flag to pass to ForcedPhot.measure method.
        cluster_threshold:
            Flag to pass to ForcedPhot.measure method.
        allow_nan:
            Flag to pass to ForcedPhot.measure method.
        add_mode:
            True when the pipeline is running in add image mode.
        done_images_df:
            Dataframe containing the images that thave already been processed
            in a previous run (used in add image mode).
        done_source_ids:
            List of the source ids that were already present in the previous
            run (used in add image mode).
        io_workers:
            List of dask worker addresses to use for `extract_from_image`
            This is likely the output of `DaskManager.get_n_random_workers()`

    Returns:
        The `sources_df` with the extracted sources added.
        The total number of forced measurements present in the run.
    """
    logger.info("Starting forced extraction step.")

    timer = StopWatch()

    # get all the skyregions and related images
    cols = [
        "id",
        "name",
        "measurements_path",
        "path",
        "noise_path",
        "beam_bmaj",
        "beam_bmin",
        "beam_bpa",
        "background_path",
        "rms_min",
        "datetime",
        "skyreg__centre_ra",
        "skyreg__centre_dec",
        "skyreg__xtr_radius",
    ]

    images_df = pd.DataFrame(
        list(
            Image.objects.filter(run=p_run)
            .select_related("skyreg")
            .order_by("datetime")
            .values(*tuple(cols))
        )
    ).set_index("name")
    
    logger.debug("Made images_df")

    # | name                          |   id     | measurements_path   | path         | noise_path   |
    # |:------------------------------|---------:|:--------------------|:-------------|:-------------|
    # | VAST_2118-06A.EPOCH01.I.fits  | iTsHMUy3 | path/to/file        | path/to/file | path/to/file |
    # | VAST_2118-06A.EPOCH03x.I.fits | nBufF23E | path/to/file        | path/to/file | path/to/file |
    # | VAST_2118-06A.EPOCH02.I.fits  | vxYozMVA | path/to/file        | path/to/file | path/to/file |

    # | name                          |   beam_bmaj |   beam_bmin |   beam_bpa | background_path   |
    # |:------------------------------|------------:|------------:|-----------:|:------------------|
    # | VAST_2118-06A.EPOCH01.I.fits  |  0.00589921 |  0.00326088 |   -70.4032 | path/to/file      |
    # | VAST_2118-06A.EPOCH03x.I.fits |  0.00470991 |  0.00300502 |   -83.1128 | path/to/file      |
    # | VAST_2118-06A.EPOCH02.I.fits  |  0.00351331 |  0.00308565 |    77.2395 | path/to/file      |

    # | name                          |   rms_min | datetime                         |   skyreg__centre_ra |   skyreg__centre_dec |   skyreg__xtr_radius |
    # |:------------------------------|----------:|:---------------------------------|--------------------:|---------------------:|---------------------:|
    # | VAST_2118-06A.EPOCH01.I.fits  |  0.173946 | 2019-08-27 18:12:16.700000+00:00 |             319.652 |              -6.2989 |               6.7401 |
    # | VAST_2118-06A.EPOCH03x.I.fits |  0.165395 | 2019-10-29 10:01:20.500000+00:00 |             319.652 |              -6.2989 |               6.7401 |
    # | VAST_2118-06A.EPOCH02.I.fits  |  0.16323  | 2019-10-30 08:31:20.200000+00:00 |             319.652 |              -6.2989 |               6.7401 |

    # Explode out the img_diff column.
    extr_df = extr_df.explode("img_diff").reset_index()
    total_to_extract = extr_df.shape[0]
    
    logger.debug("Exploded out img_diff column")
    logger.info(f"Total to extract: {total_to_extract}")

    if add_mode:
        logger.info("Running in add mode...")
        # If we are adding images to the run we assume that monitoring was
        # also performed before (enforced by the pre-run checks) so now we
        # only want to force extract in three situations:
        # 1. Any force extraction in a new image.
        # 2. The forced extraction is attached to a new source from the new
        # images.
        # 3. A new relation has been created and they need the forced
        # measuremnts filled in (actually covered by 2.)
        total_to_extract = extr_df.shape[0].compute()
        extr_df = dd.concat(
            [
                extr_df[~extr_df["img_diff"].isin(done_images_df["name"])],
                extr_df[
                    (~extr_df["source"].isin(done_source_ids))
                    & (extr_df["img_diff"].isin(done_images_df.name))
                ],
            ]
        )

        logger.info(
            f"{extr_df.shape[0].compute()} new measurements to force extract"
            f" (from {total_to_extract} total)"
        )

    timer.reset()
    logger.info("Starting parallel extraction...")
    extr_df = parallel_extraction(
        extr_df, images_df, sources_df[['source', 'image', 'flux_peak']],
        min_sigma, edge_buffer, cluster_threshold, allow_nan, add_mode,
        p_run.path, io_workers
    )
    logger.info("Completed parallel extraction step.")

    # Dask needs type metadata for map_partitions
    sources_meta = dd.utils.make_meta(sources_df).drop(['epoch', 'interim_ns', 'interim_ew'], axis=1)
    # Get expected database measurements schema
    columns = read_schema(images_df.iloc[0]["measurements_path"]).names

    logger.info("Building save and upload...")
    extr_df = extr_df.map_partitions(save_and_upload_forced_df,
                                     p_run_path=p_run.path,
                                     p_run_id=p_run.id,
                                     add_mode=add_mode,
                                     cfg_err_ra=cfg_err_ra,
                                     cfg_err_dec=cfg_err_dec,
                                     columns=columns,
                                     output_columns=sources_meta.columns,
                                     do_upload=(not __TESTING__),
                                     enforce_metadata=False,
                                     meta=sources_meta)

    # Calculate epoch column for extr_df
    if sources_df['epoch'].dtype == 'object':
        extr_df["epoch"] = "FORCED"
    elif sources_df['epoch'].dtype == 'int':
        extr_df["epoch"] = -1
    elif sources_df['epoch'].dtype == 'float':
        extr_df["epoch"] = -1.0
    else:
        extr_df["epoch"] = sources_df['epoch'].compute().iloc[0]

    extr_df = extr_df.persist()
    logger.info("Persisting extr_df...")
    wait(extr_df)
    logger.info("Persisted extr_df...")

    sources_df = dd.concat(
        [sources_df, extr_df]
    )

    # Wait for the forced extraction step to complete
    # NOTE: Ideally we would have some optimised way of sorting sources_df
    # by source id at this point to avoid needing to `set_index` on it
    # during the finalise step.
    sources_df = sources_df.persist()
    logger.info("Persisting sources_df...")
    wait(sources_df)
    logger.info("Persisted sources_df")

    del extr_df
    gc.collect()

    # get the number of forced extractions for the run
    forced_parquets = glob(os.path.join(p_run.path, "forced_measurements*.parquet"))
    if forced_parquets:
        n_forced = (
            dd.read_parquet(forced_parquets, columns=["id"]).count().compute().values[0]
        )
    else:
        n_forced = 0

    logger.info("Total forced extraction time: %.2f seconds", timer.reset_init())

    return sources_df, n_forced
