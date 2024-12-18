import os
import logging
import datetime
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
from typing import Any, List, Tuple, Dict, Optional

from vast_pipeline.models import Image, Measurement, Run
from vast_pipeline.pipeline.loading import make_upload_measurements

from forced_phot import ForcedPhot
from ..utils.utils import StopWatch, calculate_workers_and_partitions
from vast_pipeline.image.utils import open_fits
from vast_pipeline.pipeline.utils import log_total_memory_usage

logger = logging.getLogger(__name__)


def remove_forced_meas(run_path: str) -> None:
    '''
    Remove forced measurements from the database if forced parquet files
    are found.

    Args:
        run_path:
            The run path of the pipeline run.

    Returns:
        None
    '''
    path_glob = glob(
        os.path.join(run_path, 'forced_measurements_*.parquet')
    )
    if path_glob:
        ids = (
            dd.read_parquet(path_glob, columns='id')
            .values
            .compute()
            .tolist()
        )
        obj_to_delete = Measurement.objects.filter(id__in=ids)
        del ids
        if obj_to_delete.exists():
            with transaction.atomic():
                n_del, detail_del = obj_to_delete.delete()
                logger.info(
                    ('Deleting all previous forced measurement and association'
                     ' objects for this run. Total objects deleted: %i'),
                    n_del,
                )
                logger.debug('(type, #deleted): %s', detail_del)


def get_data_from_parquet(
    file_and_image_id: Tuple[str, int], p_run_path: str, add_mode: bool = False
) -> Dict:
    '''
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
    '''
    file, image_id = file_and_image_id
    if add_mode:
        image_name = file.split("/")[-2]
        forced_parquet = os.path.join(
            p_run_path,
            f"forced_measurements_{image_name}.parquet"
        )
        if os.path.isfile(forced_parquet):
            file = forced_parquet
    # get max component id from parquet file
    df = pd.read_parquet(file, columns=['island_id', 'image_id'])
    if len(df) > 0:
        prefix = df['island_id'].iloc[0].rsplit('_', maxsplit=1)[0] + '_'
        max_id = (
            df['island_id'].str.rsplit('_', n=1)
            .str.get(-1)
            .astype(int)
            .values.max() + 1
        )
    else:
        prefix = "island_"
        max_id = 1
    return {'prefix': prefix, 'max_id': max_id, 'id': image_id}


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
    image: str,
    background: str,
    noise: str,
    edge_buffer: float,
    cluster_threshold: float,
    allow_nan: bool,
    **kwargs,
) -> Dict:
    """
    Extract the flux, its erros and chi squared data from the image
    files (image FIT, background and noise files) and return a dictionary
    with the dataframe and image name

    Args:
        df:
            input dataframe with columns [source_tmp_id, wavg_ra, wavg_dec,
            image_name, flux_peak]
        image:
            a string with the path of the image FIT file
        background:
            a string with the path of the image background file
        noise:
            a string with the path of the image noise file
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

    # create the skycoord obj to pass to the forced extraction
    # see usage https://github.com/dlakaplan/forced_phot
    P_islands = SkyCoord(
        df['wavg_ra'].values,
        df['wavg_dec'].values,
        unit=(u.deg, u.deg)
    )
    
    num_sources = len(df)
    logger.debug(f"Will fit {num_sources} sources for {image}...")

    # load the image, background and noisemaps into memory
    # a dedicated function may seem unneccesary, but will be useful if we
    # split the load to a separate thread.
    forcedphot_input = _forcedphot_preload(image,
                                           background,
                                           noise,
                                           memmap=False
                                           )
    FP_timer = StopWatch()
    FP = ForcedPhot(*forcedphot_input, use_numba=True)
    logger.debug(f"{image} - Time to init FP: {FP_timer.reset()} s")

    # This should ultimately be removed in v2, but for now I am keeping the
    # option to use clustering in order to keep things backward-compatible.
    use_clusters=True
    if cluster_threshold == 0:
        use_clusters=False

    flux, flux_err, chisq, DOF, cluster_id = FP.measure(
        P_islands,
        cluster_threshold=cluster_threshold,
        allow_nan=allow_nan,
        edge_buffer=edge_buffer,
        use_clusters=use_clusters
    )
    logger.debug(f"{image} - Time to measure FP: {FP_timer.reset()}s")
    
    num_fits = np.sum(flux>0.0)

    logger.debug(f"{image}: Obtained {num_fits} measurements "
                 f"({num_sources-num_fits} sources outside of image range)."
                 )

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

    logger.debug(f"{image} - Total extraction time: {timer.reset()}s")

    return {'df': df, 'image': df['image_name'].iloc[0]}


def finalise_forced_dfs(
    df: pd.DataFrame, prefix: str, max_id: int, beam_bmaj: float,
    beam_bmin: float, beam_bpa: float, id: int, datetime: datetime.datetime,
    image: str
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
        image:
            string with the image name

    Returns:
        Input dataframe with added columns island_id, component_id,
            name, bmaj, bmin, pa, image_id, time.
    """
    # make up the measurements name from the image island_id and component_id
    df['island_id'] = np.char.add(
        prefix,
        np.arange(max_id, max_id + df.shape[0]).astype(str)
    )
    df['component_id'] = df['island_id'].str.replace(
        'island', 'component'
    ) + 'a'
    df['name'] = df['component_id']
    # assign all the other columns
    # convert fluxes to mJy
    # store source bmaj and bmin in arcsec
    df['bmaj'] = beam_bmaj * 3600.
    df['bmin'] = beam_bmin * 3600.
    df['pa'] = beam_bpa
    # add image id and time
    df['image_id'] = id
    df['time'] = datetime

    return df


def parallel_extraction(
    df: pd.DataFrame, df_images: pd.DataFrame, df_sources: pd.DataFrame,
    min_sigma: float, edge_buffer: float, cluster_threshold: float,
    allow_nan: bool, add_mode: bool, p_run_path: str, n_workers: int = 5
) -> pd.DataFrame:
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
        n_workers:
            The desired number of workers for Dask

    Returns:
        Dataframe with forced extracted measurements data, columns are
            'source_tmp_id', 'ra', 'dec', 'image', 'flux_peak', 'island_id',
            'component_id', 'name', 'flux_int', 'flux_int_err'
    """
    # explode the lists in 'img_diff' column (this will make a copy of the df)
    out = (
        df.rename(columns={'img_diff': 'image', 'source': 'source_tmp_id'})
        # merge the rms_min column from df_images
        .merge(
            df_images[['rms_min']],
            left_on='image',
            right_on='name',
            how='left'
        )
        .rename(columns={'rms_min': 'image_rms_min'})
        # merge the measurements columns 'source', 'image', 'flux_peak'
        .merge(
            df_sources,
            left_on=['source_tmp_id', 'detection'],
            right_on=['source', 'image'],
            how='left'
        )
        .drop(columns=['image_y', 'source'])
        .rename(columns={'image_x': 'image'})
    )

    # drop the source for which we would have no hope of detecting
    predrop_shape = out.shape[0]
    out['max_snr'] = out['flux_peak'].values / out['image_rms_min'].values
    out = out[out['max_snr'] > min_sigma].reset_index(drop=True)
    logger.debug("Min forced sigma dropped %i sources",
                 predrop_shape - out.shape[0]
                 )

    # drop some columns that are no longer needed and the df should look like
    # out
    # |   | source_tmp_id | wavg_ra | wavg_dec | image_name       | flux_peak |
    # |--:|--------------:|--------:|---------:|:-----------------|----------:|
    # | 0 |            81 | 317.607 | -8.66952 | VAST_2118-06A... |    11.555 |
    # | 1 |           894 | 323.803 | -2.6899  | VAST_2118-06A... |     2.178 |
    # | 2 |          1076 | 316.147 | -3.11408 | VAST_2118-06A... |     6.815 |
    # | 3 |          1353 | 322.094 | -4.44977 | VAST_2118-06A... |     1.879 |
    # | 4 |          1387 | 321.734 | -6.82934 | VAST_2118-06A... |     1.61  |

    out = (
        out.drop(['max_snr', 'image_rms_min', 'detection'], axis=1)
        .rename(columns={'image': 'image_name'})
    )

    # get the unique images to extract from
    unique_images_to_extract = out['image_name'].unique().tolist()

    # create a list of dictionaries with image file paths and dataframes
    # with data related to each images
    def image_data_func(image_name: str) -> Dict[str, Any]:
        # `out` refers to the `out` declared in nearest enclosing scope
        nonlocal out
        return {
            'image_id': df_images.at[image_name, 'id'],
            'image': df_images.at[image_name, 'path'],
            'background': df_images.at[image_name, 'background_path'],
            'noise': df_images.at[image_name, 'noise_path'],
            'df': out[out['image_name'] == image_name]
        }
    list_to_map = list(map(image_data_func, unique_images_to_extract))
    # create a list of all the measurements parquet files to extract data from,
    # such as prefix and max_id
    list_meas_parquets = list(map(
        lambda image_name: (
            df_images.at[image_name, 'measurements_path'],
            df_images.at[image_name, 'id'],
        ),
        unique_images_to_extract
    ))
    del out, unique_images_to_extract, image_data_func

    # get a map of the columns that have a fixed value
    mapping = (
        db.from_sequence(
            list_meas_parquets,
            npartitions=len(list_meas_parquets)
        )
        .map(get_data_from_parquet, p_run_path, add_mode)
        .compute(num_workers=n_workers, scheduler="processes")
    )
    mapping = pd.DataFrame(mapping)
    # remove not used columns from images_df and merge into mapping
    col_to_drop = list(filter(
        lambda x: ('path' in x) or ('skyreg' in x),
        df_images.columns.values.tolist()
    ))
    mapping = (
        mapping.merge(
            df_images.drop(col_to_drop, axis=1).reset_index(),
            on='id',
            how='left'
        )
        .drop('rms_min', axis=1)
        .set_index('name')
    )
    del col_to_drop

    logger.debug("Starting image extraction....")
    extract_timer = StopWatch()
    bags = db.from_sequence(list_to_map, npartitions=len(list_to_map))
    forced_dfs = (
        bags.map(lambda x: extract_from_image(
            edge_buffer=edge_buffer,
            cluster_threshold=cluster_threshold,
            allow_nan=allow_nan,
            **x
        ))
        .compute(num_workers=n_workers, scheduler='processes')
    )
    logger.debug(f"Completed image extraction in {extract_timer.reset()} s")

    del bags
    log_total_memory_usage()

    # create intermediates dfs combining the mapping data and the forced
    # extracted data from the images
    intermediate_df = list(map(
        lambda x: {**(mapping.loc[x['image'], :].to_dict()), **x},
        forced_dfs
    ))
    logger.debug(f"Created {len(intermediate_df)} intermediate dfs")
    log_total_memory_usage()

    # compute the rest of the columns
    # NOTE: Avoid using dask bags to parallelise the mapping
    # over DataFrames, since these tend to get very large in memory and
    # dask bags make a copy of the output before collecting the results.
    # There is also a minimal speed penalty for doing this step without
    # parallelism.
    extract_timer.reset()
    intermediate_df = list(map(
        lambda x: finalise_forced_dfs(**x),
        intermediate_df
        ))
    logger.debug(f"Populated intermediate df in {extract_timer.reset()} s")
    log_total_memory_usage()

    df_out = (
        pd.concat(intermediate_df, axis=0, sort=False)
        .rename(
            columns={
                'wavg_ra': 'ra', 'wavg_dec': 'dec', 'image_name': 'image'
            }
        )
    )
    logger.debug(f"Successfully concatenated intermediate dfs")
    log_total_memory_usage()

    return df_out


def write_group_to_parquet(
        df: pd.DataFrame, fname: str, add_mode: bool) -> None:
    '''
    Write a dataframe correpondent to a single group/image
    to a parquet file.

    Args:
        df:
            Dataframe containing all the extracted measurements.
        fname:
            The file name of the output parquet.
        add_mode:
            True when the pipeline is running in add image mode.

    Returns:
        None
    '''
    out_df = df.drop(['d2d', 'dr', 'source', 'image'], axis=1)
    if os.path.isfile(fname) and add_mode:
        exist_df = pd.read_parquet(fname)
        out_df = pd.concat([exist_df, out_df])

    out_df.to_parquet(fname, index=False)

    pass


def write_forced_parquet(
        df: pd.DataFrame, run_path: str, add_mode: bool = False) -> None:
    '''
    Write parquet files for forced measurements.

    Args:
        df:
            Dataframe containing all the extracted measurements.
        run_path:
            The run path of the pipeline run.
        add_mode:
            True when the pipeline is running in add image mode.

    Returns:
        None
    '''
    images = df['image'].unique().tolist()

    def get_fname(n): return os.path.join(
        run_path,
        'forced_measurements_' + n.replace('.', '_') + '.parquet'
    )
    # Avoid saving the maping to a list since this copies the the entire
    # DataFrame which can already be very large in memory at this point.
    dfs = map(lambda x: (df[df['image'] == x], get_fname(x)), images)

    # Write parquets
    for this_df, fname in dfs:
        write_group_to_parquet(this_df, fname, add_mode)
    pass


def forced_extraction(
    sources_df: pd.DataFrame, cfg_err_ra: float, cfg_err_dec: float,
    p_run: Run, extr_df: pd.DataFrame, min_sigma: float, edge_buffer: float,
    cluster_threshold: float, allow_nan: bool, add_mode: bool,
    done_images_df: pd.DataFrame, done_source_ids: List[int],
    n_cpu: int = 5
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
        n_cpu:
            The desired number of workers for Dask.

    Returns:
        The `sources_df` with the extracted sources added.
        The total number of forced measurements present in the run.
    """
    logger.info(
        'Starting force extraction step.'
    )

    timer = StopWatch()

    # get all the skyregions and related images
    cols = [
        'id', 'name', 'measurements_path', 'path', 'noise_path',
        'beam_bmaj', 'beam_bmin', 'beam_bpa', 'background_path',
        'rms_min', 'datetime', 'skyreg__centre_ra',
        'skyreg__centre_dec', 'skyreg__xtr_radius'
    ]

    images_df = pd.DataFrame(list(
        Image.objects.filter(
            run=p_run
        ).select_related('skyreg').order_by('datetime').values(*tuple(cols))
    )).set_index('name')
# | name                          |   id | measurements_path   | path         | noise_path   |
# |:------------------------------|-----:|:--------------------|:-------------|:-------------|
# | VAST_2118-06A.EPOCH01.I.fits  |    1 | path/to/file        | path/to/file | path/to/file |
# | VAST_2118-06A.EPOCH03x.I.fits |    3 | path/to/file        | path/to/file | path/to/file |
# | VAST_2118-06A.EPOCH02.I.fits  |    2 | path/to/file        | path/to/file | path/to/file |

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
    extr_df = extr_df.explode('img_diff').reset_index()
    total_to_extract = extr_df.shape[0]

    if add_mode:
        # If we are adding images to the run we assume that monitoring was
        # also performed before (enforced by the pre-run checks) so now we
        # only want to force extract in three situations:
        # 1. Any force extraction in a new image.
        # 2. The forced extraction is attached to a new source from the new
        # images.
        # 3. A new relation has been created and they need the forced
        # measuremnts filled in (actually covered by 2.)

        extr_df = pd.concat(
            [
                extr_df[~extr_df['img_diff'].isin(done_images_df['name'])],
                extr_df[
                    (~extr_df['source'].isin(done_source_ids))
                    & (extr_df['img_diff'].isin(done_images_df.name))
                ]
            ]
        ).sort_index()

        logger.info(
            f"{extr_df.shape[0]} new measurements to force extract"
            f" (from {total_to_extract} total)"
        )

    # Don't care about n_partitions in this step
    n_workers, _ = calculate_workers_and_partitions(None, n_cpu)

    timer.reset()
    extr_df = parallel_extraction(
        extr_df, images_df, sources_df[['source', 'image', 'flux_peak']],
        min_sigma, edge_buffer, cluster_threshold, allow_nan, add_mode,
        p_run.path, n_workers=n_workers
    )
    logger.info(
        'Force extraction step time: %.2f seconds', timer.reset()
    )

    # make measurement names unique for db constraint
    extr_df['name'] = extr_df['name'] + f'_f_run{p_run.id:03d}'

    default_pos_err = settings.POS_DEFAULT_MIN_ERROR / 3600.
    extr_df['ra_err'] = default_pos_err
    extr_df['dec_err'] = default_pos_err
    extr_df['err_bmaj'] = 0.
    extr_df['err_bmin'] = 0.
    extr_df['err_pa'] = 0.
    extr_df['ew_sys_err'] = cfg_err_ra
    extr_df['ns_sys_err'] = cfg_err_dec
    extr_df['error_radius'] = 0.

    extr_df['uncertainty_ew'] = np.hypot(
        cfg_err_ra,
        default_pos_err
    )
    extr_df['weight_ew'] = 1. / extr_df['uncertainty_ew'].values**2
    extr_df['uncertainty_ns'] = np.hypot(
        cfg_err_dec,
        default_pos_err
    )
    extr_df['weight_ns'] = 1. / extr_df['uncertainty_ns'].values**2

    extr_df['flux_peak'] = extr_df['flux_int']
    extr_df['flux_peak_err'] = extr_df['flux_int_err']
    extr_df['local_rms'] = extr_df['flux_int_err']
    extr_df['snr'] = (
        extr_df['flux_peak'].values
        / extr_df['local_rms'].values
    )
    extr_df['spectral_index'] = 0.
    extr_df['dr'] = 0.
    extr_df['d2d'] = 0.
    extr_df['forced'] = True
    extr_df['compactness'] = 1.
    extr_df['psf_bmaj'] = extr_df['bmaj']
    extr_df['psf_bmin'] = extr_df['bmin']
    extr_df['psf_pa'] = extr_df['pa']
    extr_df['flag_c4'] = False
    extr_df['spectral_index_from_TT'] = False
    extr_df['has_siblings'] = False
    extr_df['flux_int_isl_ratio'] = 1.0
    extr_df['flux_peak_isl_ratio'] = 1.0

    col_order = read_schema(
        images_df.iloc[0]['measurements_path']
    ).names
    col_order.remove('id')

    remaining = list(set(extr_df.columns) - set(col_order))

    extr_df = extr_df[col_order + remaining]

    # upload the measurements, a column 'id' is returned with the DB id
    extr_df = make_upload_measurements(extr_df)

    extr_df = extr_df.rename(columns={'source_tmp_id': 'source'})

    # write forced measurements to specific parquet
    logger.info(
        'Saving forced measurements to specific parquet file...'
    )
    write_forced_parquet(extr_df, p_run.path, add_mode)

    # Required to rename this column for the image add mode.
    extr_df = extr_df.rename(columns={'time': 'datetime'})

    # append new meas into main df and proceed with source groupby etc
    sources_df = pd.concat(
        [
            sources_df,
            extr_df.loc[:, extr_df.columns.isin(sources_df.columns)]
        ],
        ignore_index=True
    )

    # get the number of forced extractions for the run
    forced_parquets = glob(
        os.path.join(p_run.path, "forced_measurements*.parquet"))
    if forced_parquets:
        n_forced = (
            dd.read_parquet(forced_parquets, columns=['id'])
            .count()
            .compute(num_workers=n_workers, scheduler='processes')
            .values[0]
        )
    else:
        n_forced = 0

    logger.info(
        'Total forced extraction time: %.2f seconds', timer.reset_init()
    )
    return sources_df, n_forced
