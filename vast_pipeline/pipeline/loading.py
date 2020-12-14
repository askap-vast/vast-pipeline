import os
import logging
import numpy as np
import pandas as pd

from django.db import connection
from django.db import transaction
from itertools import islice

from vast_pipeline.image.main import SelavyImage
from vast_pipeline.pipeline.model_generator import (
    measurement_models_generator,
    source_models_generator,
    related_models_generator,
    association_models_generator,
    measurement_pair_models_generator,
)
from vast_pipeline.models import Association, Measurement, Source, RelatedSource, MeasurementPair
from vast_pipeline.pipeline.utils import (
    get_create_img, get_create_img_band
)
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


@transaction.atomic
def bulk_upload_model(djmodel, generator, batch_size=10_000, return_ids=False):
    '''
    bulk upload a pandas series of django models to db
    djmodel: django.model
    generator: generator
    batch_size: int
    return_ids: bool
    '''
    bulk_ids = []
    while True:
        items = list(islice(generator, batch_size))
        if not items:
            break
        out_bulk = djmodel.objects.bulk_create(items)
        logger.info('Bulk created #%i %s', len(out_bulk), djmodel.__name__)
        # save the DB ids to return
        if return_ids:
            bulk_ids.extend(list(map(lambda i: i.id, out_bulk)))

    if return_ids:
        return bulk_ids


@transaction.atomic
def bulk_upload_model(djmodel, generator, batch_size=10_000, return_ids=False):
    '''
    bulk upload a pandas series of django models to db
    djmodel: django.model
    generator: generator
    batch_size: int
    return_ids: bool
    '''
    bulk_ids = []
    while True:
        items = list(islice(generator, batch_size))
        if not items:
            break
        out_bulk = djmodel.objects.bulk_create(items)
        logger.info('Bulk created #%i %s', len(out_bulk), djmodel.__name__)
        # save the DB ids to return
        if return_ids:
            bulk_ids.extend(list(map(lambda i: i.id, out_bulk)))

    if return_ids:
        return bulk_ids


def make_upload_images(paths, config, pipeline_run):
    '''
    carry the first part of the pipeline, by uploading all the images
    to the image table and populated band and skyregion objects
    '''
    timer = StopWatch()
    images = []
    skyregions = []
    bands = []

    for path in paths['selavy']:
        # STEP #1: Load image and measurements
        image = SelavyImage(
            path,
            paths,
            config=config
        )
        logger.info('Reading image %s ...', image.name)

        # 1.1 get/create the frequency band
        with transaction.atomic():
            band = get_create_img_band(image)
        if band not in bands:
            bands.append(band)

        # 1.2 create image and skyregion entry in DB
        with transaction.atomic():
            img, skyreg, exists_f = get_create_img(
                pipeline_run, band.id, image
            )

        # add image and skyregion to respective lists
        images.append(img)
        if skyreg not in skyregions:
            skyregions.append(skyreg)
        if exists_f:
            logger.info(
                'Image %s already processed, grab measurements',
                img.name
            )
            # grab the measurements and skip to process next image
            measurements = (
                pd.Series(
                    Measurement.objects.filter(forced=False, image__id=img.id),
                    name='meas_dj'
                )
                .to_frame()
            )
            measurements['id'] = measurements['meas_dj'].apply(lambda x: x.id)
            continue

        # 1.3 get the image measurements and save them in DB
        measurements = image.read_selavy(img)
        logger.info(
            'Processed measurements dataframe of shape: (%i, %i)',
            measurements.shape[0], measurements.shape[1]
        )

        # upload measurements, a column with the db is added to the df
        measurements = make_upload_measurements(measurements)

        # save measurements to parquet file in pipeline run folder
        base_folder = os.path.dirname(img.measurements_path)
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)

        measurements.to_parquet(
            img.measurements_path,
            index=False
        )
        del measurements, image, band, img

    # write images parquet file under pipeline run folder
    images_df = pd.DataFrame(map(lambda x: x.__dict__, images))
    images_df = images_df.drop('_state', axis=1)
    images_df.to_parquet(
        os.path.join(config.PIPE_RUN_PATH, 'images.parquet'),
        index=False
    )
    # write skyregions parquet file under pipeline run folder
    skyregs_df = pd.DataFrame(map(lambda x: x.__dict__, skyregions))
    skyregs_df = skyregs_df.drop('_state', axis=1)
    skyregs_df.to_parquet(
        os.path.join(config.PIPE_RUN_PATH, 'skyregions.parquet'),
        index=False
    )
    # write skyregions parquet file under pipeline run folder
    bands_df = pd.DataFrame(map(lambda x: x.__dict__, bands))
    bands_df = bands_df.drop('_state', axis=1)
    bands_df.to_parquet(
        os.path.join(config.PIPE_RUN_PATH, 'bands.parquet'),
        index=False
    )

    logger.info(
        'Total images upload/loading time: %.2f seconds',
        timer.reset_init()
    )

    return images, skyregs_df


def make_upload_sources(sources_df, pipeline_run, add_mode=False):
    '''
    delete previous sources for given pipeline run and bulk upload
    new found sources as well as related sources
    '''
    # create sources in DB
    with transaction.atomic():
        if (add_mode is False and
                Source.objects.filter(run=pipeline_run).exists()):
            logger.info('Removing objects from previous pipeline run')
            n_del, detail_del = (
                Source.objects.filter(run=pipeline_run).delete()
            )
            logger.info(
                ('Deleting all sources and related objects for this run. '
                 'Total objects deleted: %i'),
                n_del,
            )
            logger.debug('(type, #deleted): %s', detail_del)

    src_dj_ids = bulk_upload_model(
        Source,
        source_models_generator(sources_df, pipeline_run=pipeline_run),
        return_ids=True
    )

    sources_df['id'] = src_dj_ids

    return sources_df


def update_sources(sources_df, pipeline_run, batch_size=10_000):
    Sources = Source.objects.filter(id__in=sources_df.index.values).only(
        'new', 'wavg_ra', 'wavg_dec', 'wavg_uncertainty_ew',
        'wavg_uncertainty_ns', 'avg_flux_int', 'avg_flux_peak',
        'max_flux_peak', 'min_flux_peak', 'max_flux_int', 'min_flux_int',
        'min_flux_int_isl_ratio', 'min_flux_peak_isl_ratio', 'avg_compactness',
        'min_snr', 'max_snr', 'v_int', 'v_peak', 'eta_int', 'eta_peak',
        'new_high_sigma', 'n_neighbour_dist', 'vs_abs_significant_max_int',
        'm_abs_significant_max_int', 'vs_abs_significant_max_peak',
        'm_abs_significant_max_peak', 'n_meas', 'n_meas_sel', 'n_meas_forced',
        'n_rel', 'n_sibl'
    )
    chunk = []
    fields = [
        'new', 'wavg_ra', 'wavg_dec', 'wavg_uncertainty_ew',
        'wavg_uncertainty_ns', 'avg_flux_int', 'avg_flux_peak',
        'max_flux_peak', 'min_flux_peak', 'max_flux_int', 'min_flux_int',
        'min_flux_int_isl_ratio', 'min_flux_peak_isl_ratio', 'avg_compactness',
        'min_snr', 'max_snr', 'v_int', 'v_peak', 'eta_int', 'eta_peak',
        'new_high_sigma', 'n_neighbour_dist', 'vs_abs_significant_max_int',
        'm_abs_significant_max_int', 'vs_abs_significant_max_peak',
        'm_abs_significant_max_peak', 'n_meas', 'n_meas_sel', 'n_meas_forced',
        'n_rel', 'n_sibl'
    ]
    # Use iterator to save memory
    for i, src in enumerate(Sources.iterator(chunk_size=batch_size)):
        src_series = sources_df.loc[src.id]
        for fld in fields:
            setattr(src, fld, src_series[fld])
        chunk.append(src)
        # Every 10000 events run bulk_update
        if i != 0 and i % batch_size == 0 and chunk:
            with transaction.atomic():
                Source.objects.bulk_update(chunk, fields)
                logger.info(f'Bulk updated #{batch_size} sources')
            chunk = []
    if chunk:
        with transaction.atomic():
            Source.objects.bulk_update(chunk, fields)
            logger.info('Bulk updated #%i sources', len(chunk))

    del chunk

    sources_df['id'] = sources_df.index.values

    return sources_df


def make_upload_related_sources(related_df):
    logger.info('Populate "related" field of sources...')
    bulk_upload_model(RelatedSource, related_models_generator(related_df))


def make_upload_associations(associations_df):
    logger.info('Upload associations...')
    bulk_upload_model(
        Association, association_models_generator(associations_df)
    )


def make_upload_measurements(measurements_df):
    meas_dj_ids = bulk_upload_model(
        Measurement,
        measurement_models_generator(measurements_df),
        return_ids=True
    )

    measurements_df['id'] = meas_dj_ids
    return measurements_df


def make_upload_measurement_pairs(measurement_pairs_df):
    meas_pair_dj_ids = bulk_upload_model(
        MeasurementPair,
        measurement_pair_models_generator(measurement_pairs_df),
        return_ids=True
    )
    measurement_pairs_df["id"] = meas_pair_dj_ids
    return measurement_pairs_df


def SQL_update(df, model, index=None, columns=None, batch_size=10_000):
    '''
    Update database using SQL code. This function opens one connection to the
    database, and closes it after the update is done. 

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing the new data to be uploaded to the database. The
        columns to be updated need to have the same headers between the df and
        the table in the database.
    model : Model
        The model that is being updated. 
    index : str
        Header of the column to join on, determines which rows in the different
        tables match. If None, then use the primary key column. 
    columns : List[str] or None
        The column headers of the columns to be updated. If None, updates all 
        columns except the index column.
    batch_size : int
        The df rows are broken into chunks, each chunk is executed in a 
        separate SQL command, chunk determines the maximum size of the chunk.

    Returns
    -------
    None
    '''
    chunks = np.ceil(len(df)/batch_size)
    dfs = np.array_split(df, chunks)
    with connection.cursor() as cursor:
        for df_chunk in dfs:
            SQL_comm = SQL_update_comm(df_chunk, model, index, columns=columns)
            cursor.execute(SQL_comm)


def SQL_update_comm(df, model, index=None, columns=None):
    '''
    Update database using SQL code. For more details on the input parameters, 
    see SQL_update. 

    Returns
    -------
    SQL_comm : str
        The SQL command to update the database. 
    '''
    # set index and columns if None
    if index is None:
        index = model._meta.pk.name
    if columns is None:
        columns = df.columns.tolist()
        columns.remove(index)

    # get names 
    table = model._meta.db_table
    new_columns = ', '.join('new_'+c for c in columns)
    set_columns = ', '.join(c+'=new_'+c for c in columns)

    # get index values and new values
    column_headers = [index]
    column_headers.extend(columns)
    data_arr = df.loc[:, column_headers].to_numpy()
    values = []
    for row in data_arr:
        val_row = '(' + ', '.join(f'{val}' for val in row) + ')'
        values.append(val_row)
    values = ', '.join(values)

    # update database
    SQL_comm = f"""
        UPDATE {table}
        SET {set_columns}
        FROM (VALUES {values})
        AS new_values (index_col, {new_columns})
        WHERE {index}=index_col;
    """
    
    return SQL_comm
