import os
import logging
import datetime
import gc
import shutil
import uuid

import numpy as np
import pandas as pd
import dask.dataframe as dd
from glob import glob

from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from pyarrow.parquet import read_schema
from typing import List, Tuple, Dict, Optional
from dask.distributed import get_client, wait

from vast_pipeline.models import Image, Run
from vast_pipeline.pipeline.loading import copy_upload_measurements
from vast_pipeline.daskmanager.manager import get_io_semaphore

from forced_phot import ForcedPhot
from ..utils.utils import StopWatch
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
    with get_io_semaphore():
        image_hdul = open_fits(image, memmap=memmap)
        background_hdul = open_fits(background, memmap=memmap)
        noise_hdul = open_fits(noise, memmap=memmap)

    return image_hdul, background_hdul, noise_hdul


def extract_from_image(
    df: pd.DataFrame,
    df_images: pd.DataFrame,
    p_run_path: str,
    add_mode: bool,
    edge_buffer: float,
    cluster_threshold: float,
    allow_nan: bool,
    **kwargs,
) -> pd.DataFrame:
    """
    Extract the flux, its errors and chi squared data from the image
    files (image FIT, background and noise files) and return the dataframe
    with the extracted data added.

    Args:
        df:
            input dataframe with columns [source_tmp_id, wavg_ra, wavg_dec,
            image_name, flux_peak]
        df_images:
            dataframe indexed by image name with columns 'id',
            'measurements_path', 'path', 'noise_path', 'beam_bmaj',
            'beam_bmin', 'beam_bpa', 'background_path' and 'datetime'.
        p_run_path:
            the system path of the pipeline run output.
        add_mode:
            True when the pipeline is running in add image mode.
        edge_buffer:
            flag to pass to ForcedPhot.measure method
        cluster_threshold:
            flag to pass to ForcedPhot.measure method
        allow_nan:
            flag to pass to ForcedPhot.measure method

    Returns:
        Input dataframe with added columns (flux_int, flux_int_err,
            chi_squared_fit and those added by finalise_forced_dfs).
    """
    timer = StopWatch()

    # Each partition must contain the rows for exactly one image.
    assert df['image_name'].nunique() == 1, (
        "extract_from_image expects a single image per partition"
    )
    image_name = df['image_name'].iloc[0]
    parquet_meta = get_data_from_parquet(
        (df_images.at[image_name, "measurements_path"], df_images.at[image_name, "id"]),
        p_run_path,
        add_mode,
    )
    _img_cols = ["id", "path", "background_path", "noise_path",
                 "beam_bmaj", "beam_bmin", "beam_bpa", "datetime"]
    data = {**parquet_meta, **{col: df_images.at[image_name, col] for col in _img_cols}}

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

    # df can be empty if every measurement for the image was filtered out
    image = df['image_name'].iloc[0] if len(df) > 0 else ""
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


def _make_extract_meta(input_meta: pd.DataFrame, df_images: pd.DataFrame) -> pd.DataFrame:
    """
    Build the output metadata of extract_from_image for Dask by running
    the real column-adding code (finalise_forced_dfs) on a single dummy row.

    Args:
        input_meta:
            Metadata of the per-image parquet dataframe, with columns
            [source_tmp_id, wavg_ra, wavg_dec, flux_peak, image_name].
        df_images:
            dataframe indexed by image name, used to get the dtypes of the
            beam, id and datetime values.

    Returns:
        Empty dataframe with the columns and dtypes returned by
            extract_from_image.
    """
    dummy = dd.utils.meta_nonempty(input_meta).iloc[:1].copy()
    dummy["flux_int"] = np.float64(1.0)
    dummy["flux_int_err"] = np.float64(1.0)
    dummy["chi_squared_fit"] = np.float64(1.0)
    row = df_images.iloc[0]
    return finalise_forced_dfs(
        dummy,
        prefix="island_",
        max_id=1,
        beam_bmaj=row["beam_bmaj"],
        beam_bmin=row["beam_bmin"],
        beam_bpa=row["beam_bpa"],
        id=row["id"],
        datetime=row["datetime"],
    ).iloc[:0]


def parallel_extraction(
    df: pd.DataFrame,
    df_images: pd.DataFrame,
    min_sigma: float,
    edge_buffer: float,
    cluster_threshold: float,
    allow_nan: bool,
    add_mode: bool,
    p_run_path: str,
) -> pd.DataFrame:
    """
    Parallelize forced extraction with Dask

    Args:
        df:
            dataframe with columns 'wavg_ra', 'wavg_dec', 'img_diff',
            'detection', 'flux_peak'
        df_images:
            dataframe with the images data and columns 'id',
            'measurements_path', 'path', 'noise_path', 'beam_bmaj',
            'beam_bmin', 'beam_bpa', 'background_path', 'rms_min', 'datetime',
            'skyreg__centre_ra', 'skyreg__centre_dec', 'skyreg__xtr_radius'
            and 'name' as the index.
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

    Returns:
        Dataframe with forced extracted measurements data, columns are
            'source_tmp_id', 'ra', 'dec', 'image', 'flux_peak', 'island_id',
            'component_id', 'name', 'flux_int', 'flux_int_err'
    """

    # Look up the int32 image index and rms_min for each img_diff in df.
    image_names_index = df_images.index
    image_rms_min = df_images["rms_min"].to_numpy()

    def _add_image_idx(part: pd.DataFrame) -> pd.DataFrame:
        idx = image_names_index.get_indexer(part["img_diff"])
        if (idx < 0).any():
            raise ValueError("img_diff contains image names not found in df_images")
        return part.assign(
            image_idx=idx.astype(np.int32),
            rms_min=image_rms_min[idx],
        )

    out = df.rename(columns={"source": "source_tmp_id"})
    out_meta = out._meta.assign(
        image_idx=np.empty(0, dtype=np.int32),
        rms_min=np.empty(0, dtype=image_rms_min.dtype),
    )
    out = out.map_partitions(_add_image_idx, meta=out_meta)

    # drop the source for which we would have no hope of detecting
    out = (
        out[out["flux_peak"] / out["rms_min"] > min_sigma]
        .drop(columns=["rms_min", "img_diff"])
    )

    # out after this point looks like:
    # |   | source_tmp_id | wavg_ra | wavg_dec | image_idx | flux_peak |
    # |--:|--------------:|--------:|---------:|----------:|----------:|
    # | 0 |  223b8Lp4Sdp3 | 317.607 | -8.66952 | 1042      |    11.555 |
    # | 1 |  22LyLU54pBPm | 323.803 | -2.6899  | 1043      |     2.178 |
    # | 2 |  23Vif6cLMQ5C | 316.147 | -3.11408 | 1044      |     6.815 |
    # | 3 |  zzyc7GFJreMg | 322.094 | -4.44977 | 1045      |     1.879 |
    # | 4 |  225RNzDTJ3MR | 321.734 | -6.82934 | 1046      |     1.61  |

    out = out.persist()
    logger.info("Persisting out df...")
    wait(out)
    logger.info("Persisted out df")

    # Shuffle by image_idx so all rows for a given image land in exactly one
    # partition (deterministic hash), then write one parquet per image via
    # map_partitions to a temporary location.
    _tmp_dir = os.path.join(p_run_path, "_forced_extract_tmp")
    os.makedirs(_tmp_dir, exist_ok=True)

    def _write_image_files(df, tmp_dir, images_index):
        for image_idx_val, group in df.groupby("image_idx"):
            image_name = images_index[image_idx_val]
            path = os.path.join(tmp_dir, image_name.replace(".", "_") + ".parquet")
            out_group = group.drop(columns=["image_idx"]).copy()
            out_group["image_name"] = image_name
            out_group.to_parquet(path, index=False)
        return pd.DataFrame()

    out = out.shuffle("image_idx", npartitions=len(df_images), shuffle_method="p2p")
    out.map_partitions(_write_image_files, _tmp_dir, df_images.index,
                       meta=pd.DataFrame()).compute()

    del out

    # Scatter df_images to the cluster once, broadcasting a single copy to
    # every worker. Without this, passing df_images directly to
    # map_partitions copies the whole DataFrame in every one of the
    # ~len(df_images) extraction tasks graph nodes, which are all
    # held for the full duration of the extraction run.
    df_images_future = get_client().scatter(df_images, broadcast=True)

    per_image_ddf = dd.read_parquet(_tmp_dir, split_row_groups=False, blocksize=None)
    extract_meta = _make_extract_meta(per_image_ddf._meta, df_images)

    out = per_image_ddf.map_partitions(
        extract_from_image,
        df_images_future,
        p_run_path,
        add_mode,
        edge_buffer=edge_buffer,
        cluster_threshold=cluster_threshold,
        allow_nan=allow_nan,
        meta=extract_meta,
    ).persist()

    logger.info("Running extraction and persisting...")
    wait(out)
    logger.info("Finished persisting out")
    logger.info("Cleaning up temporary files...")
    shutil.rmtree(_tmp_dir, ignore_errors=True)

    return out


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
        df["id"] = df.apply(lambda _: str(uuid.uuid4()), axis=1)
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

    Returns:
        The `sources_df` with the extracted sources added.
        The total number of forced measurements present in the run.
    """
    logger.info("Starting force extraction step.")

    timer = StopWatch()

    # get all the skyregions and related images
    cols = {
        "id": "object",
        "name": "object",
        "measurements_path": "object",
        "path": "object",
        "noise_path": "object",
        "beam_bmaj": "float32",
        "beam_bmin": "float32",
        "beam_bpa": "float32",
        "background_path": "object",
        "rms_min": "float32",
        "datetime": "datetime64[ns, UTC]",
        "skyreg__centre_ra": "float32",
        "skyreg__centre_dec": "float32",
        "skyreg__xtr_radius": "float32",
    }

    images_df = (
        pd.DataFrame(
            list(
                Image.objects.filter(run=p_run)
                .select_related("skyreg")
                .order_by("datetime")
                .values(*tuple(cols.keys()))
            )
        )
        .set_index("name")
        .astype({k: v for k, v in cols.items() if k != "name"})
    )

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

    extr_df = extr_df.reset_index()
    total_to_extract = extr_df.shape[0].compute()
    logger.info("%d forced measurements to extract", total_to_extract)

    if add_mode:
        # If we are adding images to the run we assume that monitoring was
        # also performed before (enforced by the pre-run checks) so now we
        # only want to force extract in three situations:
        # 1. Any force extraction in a new image.
        # 2. The forced extraction is attached to a new source from the new
        # images.
        # 3. A new relation has been created and they need the forced
        # measuremnts filled in (actually covered by 2.)
        logger.info("Running extraction in add mode...")
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
    extr_df = parallel_extraction(
        extr_df,
        images_df,
        min_sigma,
        edge_buffer,
        cluster_threshold,
        allow_nan,
        add_mode,
        p_run.path,
    )
    logger.info("Completed parallel extraction step.")

    # Dask needs type metadata for map_partitions
    sources_meta = dd.utils.make_meta(sources_df).drop(['epoch', 'interim_ns', 'interim_ew'], axis=1)
    # Get expected database measurements schema
    columns = read_schema(images_df.iloc[0]["measurements_path"]).names

    logger.debug("Building save and upload...")
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

    logger.info("Persisting extr_df...")
    extr_df = extr_df.persist()
    wait(extr_df)
    logger.info("Persisted extr_df.")

    sources_df = dd.concat(
        [sources_df, extr_df],
        interleave_partitions=True
    )

    # Wait for the forced extraction step to complete
    # NOTE: Ideally we would have some optimised way of sorting sources_df
    # by source id at this point to avoid needing to `set_index` on it
    # during the finalise step.
    logger.info("Persisting sources_df...")
    sources_df = sources_df.persist()
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
