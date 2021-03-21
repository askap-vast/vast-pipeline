import os
import logging
import numpy as np
import pandas as pd

from typing import List, Optional
from itertools import islice
from django.db import transaction, connection, models

from vast_pipeline.image.main import SelavyImage
from vast_pipeline.pipeline.model_generator import (
    measurement_models_generator,
    source_models_generator,
    related_models_generator,
    association_models_generator,
    measurement_pair_models_generator,
)
from vast_pipeline.models import (
    Association, Measurement, Source, RelatedSource, MeasurementPair, Run
)
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


def make_upload_sources(sources_df: pd.DataFrame, pipeline_run: Run,
    add_mode: bool = False) -> pd.DataFrame:
    '''
    Delete previous sources for given pipeline run and bulk upload
    new found sources as well as related sources

    Parameters
    ----------
    sources_df : pd.DataFrame
        Holds the measurements associated into sources. The output of of the
        association step.
    pipeline_run : Run
        The pipeline Run object.
    add_mode : bool
        Whether the pipeline is running in add image mode.

    Returns
    -------
    sources_df : pd.DataFrame
        The input dataframe with the 'id' column added.
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


def update_sources(
    sources_df: pd.DataFrame, batch_size: int = 10_000) -> pd.DataFrame:
    '''
    Update database using SQL code. This function opens one connection to the
    database, and closes it after the update is done.

    Parameters
    ----------
    sources_df : pd.DataFrame
        DataFrame containing the new data to be uploaded to the database. The
        columns to be updated need to have the same headers between the df and
        the table in the database.
    batch_size : int
        The df rows are broken into chunks, each chunk is executed in a
        separate SQL command, batch_size determines the maximum size of the
        chunk.

    Returns
    -------
    sources_df : pd.DataFrame
        DataFrame containing the new data to be uploaded to the database.
    '''
    # Get all possible columns from the model
    all_source_table_cols = [
        fld.attname for fld in Source._meta.get_fields()
        if getattr(fld, 'attname', None) is not None
    ]

    # Filter to those present in sources_df
    columns = [
        col for col in all_source_table_cols if col in sources_df.columns
    ]

    sources_df['id'] = sources_df.index.values

    batches = np.ceil(len(sources_df)/batch_size)
    dfs = np.array_split(sources_df, batches)
    with connection.cursor() as cursor:
        for df_batch in dfs:
            SQL_comm = SQL_update(
                df_batch, Source, index='id', columns=columns
            )
            cursor.execute(SQL_comm)

    return sources_df


def SQL_update(
    df: pd.DataFrame, model: models.Model, index: Optional[str] = None,
    columns: Optional[List[str]] = None
) -> str:
    '''
    Generate SQL code required to update database.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing the new data to be uploaded to the database. The
        columns to be updated need to have the same headers between the df and
        the table in the database.
    model : Model
        The model that is being updated.
    index : str or None
        Header of the column to join on, determines which rows in the different
        tables match. If None, then use the primary key column.
    columns : List[str] or None
        The column headers of the columns to be updated. If None, updates all
        columns except the index column.

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
    data_arr = df[column_headers].to_numpy()
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
