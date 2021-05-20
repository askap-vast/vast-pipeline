import os
import logging
import numpy as np
import pandas as pd

from typing import List, Optional, Dict, Tuple, Generator, Iterable
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
    Association, Measurement, Source, RelatedSource,
    MeasurementPair, Run, Image
)
from vast_pipeline.pipeline.config import PipelineConfig
from vast_pipeline.pipeline.utils import (
    get_create_img, get_create_img_band, add_run_to_img, write_parquets
)
from vast_pipeline.utils.utils import StopWatch


logger = logging.getLogger(__name__)


@transaction.atomic
def bulk_upload_model(
    djmodel: models.Model,
    generator: Iterable[Generator[models.Model, None, None]],
    batch_size: int=10_000, return_ids: bool=False
) -> List[int]:
    '''
    Bulk upload a list of generator objects of django models to db.

    Args:
        djmodel:
            The Django pipeline model to be uploaded.
        generator:
            The generator objects of the model to upload.
        batch_size:
            How many records to upload at once.
        return_ids:
            When set to True, the database IDs of the uploaded objects are
            returned.

    Returns:
        None or a list of the database IDs of the uploaded objects.

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


def make_upload_images(
    paths: Dict[str, Dict[str, str]], config: PipelineConfig, pipeline_run: Run=None
) -> Tuple[List[Image], pd.DataFrame]:
    '''
    Carry the first part of the pipeline, by uploading all the images
    to the image table and populated band and skyregion objects.

    Args:
        paths:
            Dictionary containing the image, noise and background paths of all
            the images in the pipeline run. The primary keys are `selavy`,
            'noise' and 'background' with the secondary key being the image
            name.
        config (config):
            The config object of the pipeline run.
        pipeline_run:
            The pipeline run object.

    Returns:
        A list of image objects that have been uploaded along with a DataFrame
        containing the information of the sky regions associated with the run.
    '''
    timer = StopWatch()
    images = []
    skyregions = []
    bands = []

    image_config = config.image_config()

    for path in paths['selavy']:
        # STEP #1: Load image and measurements
        image = SelavyImage(
            path,
            paths,
            image_config
        )
        logger.info('Reading image %s ...', image.name)

        # 1.1 get/create the frequency band
        with transaction.atomic():
            band = get_create_img_band(image)
        if band not in bands:
            bands.append(band)

        # 1.2 create image and skyregion entry in DB
        with transaction.atomic():
            img, exists_f = get_create_img(band.id, image)
            skyreg = img.skyreg
            if pipeline_run:
                add_run_to_img(pipeline_run, img)

        # add image and skyregion to respective lists
        images.append(img)
        if skyreg not in skyregions:
            skyregions.append(skyreg)

        if exists_f:
            logger.info('Image %s already processed', img.name)
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

    if pipeline_run:
        skyregs_df = write_parquets(images, skyregions, bands, config["run"]["path"])
    else:
        skyregs_df = None

    logger.info(
        'Total images upload/loading time: %.2f seconds',
        timer.reset_init()
    )

    return images, skyregs_df


def make_upload_sources(
    sources_df: pd.DataFrame, pipeline_run: Run, add_mode: bool = False
) -> pd.DataFrame:
    '''
    Delete previous sources for given pipeline run and bulk upload
    new found sources as well as related sources.

    Args:
        sources_df:
            Holds the measurements associated into sources. The output of of
            thE association step.
        pipeline_run:
            The pipeline Run object.
        add_mode:
            Whether the pipeline is running in add image mode.

    Returns:
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


def make_upload_related_sources(related_df: pd.DataFrame) -> None:
    """
    Uploads the related sources from the supplied related sources DataFrame.

    Args:
        related_df:
            DataFrame containing the related sources information from the
            pipeline.

    Returns:
        None.
    """
    logger.info('Populate "related" field of sources...')
    bulk_upload_model(RelatedSource, related_models_generator(related_df))


def make_upload_associations(associations_df: pd.DataFrame) -> None:
    """
    Uploads the associations from the supplied associations DataFrame.

    Args:
        associations_df:
            DataFrame containing the associations information from the
            pipeline.

    Returns:
        None.
    """
    logger.info('Upload associations...')
    bulk_upload_model(
        Association, association_models_generator(associations_df)
    )


def make_upload_measurements(measurements_df: pd.DataFrame) -> pd.DataFrame:
    """
    Uploads the measurements from the supplied measurements DataFrame.

    Args:
        measurements_df:
            DataFrame containing the measurements information from the
            pipeline.

    Returns:
        Original DataFrame with the database ID attached to each row.
    """
    meas_dj_ids = bulk_upload_model(
        Measurement,
        measurement_models_generator(measurements_df),
        return_ids=True
    )

    measurements_df['id'] = meas_dj_ids

    return measurements_df


def make_upload_measurement_pairs(
    measurement_pairs_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Uploads the measurement pairs from the supplied measurement pairs
    DataFrame.

    Args:
        measurement_pairs_df:
            DataFrame containing the measurement pairs information from the
            pipeline.

    Returns:
        Original DataFrame with the database ID attached to each row.
    """
    meas_pair_dj_ids = bulk_upload_model(
        MeasurementPair,
        measurement_pair_models_generator(measurement_pairs_df),
        return_ids=True
    )
    measurement_pairs_df["id"] = meas_pair_dj_ids

    return measurement_pairs_df


def update_sources(
    sources_df: pd.DataFrame, batch_size: int = 10_000
) -> pd.DataFrame:
    '''
    Update database using SQL code. This function opens one connection to the
    database, and closes it after the update is done.

    Args:
        sources_df:
            DataFrame containing the new data to be uploaded to the database.
            The columns to be updated need to have the same headers between
            the df and the table in the database.
        batch_size:
            The df rows are broken into chunks, each chunk is executed in a
            separate SQL command, batch_size determines the maximum size of the
            chunk.

    Returns:
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
    Generate the SQL code required to update the database.

    Args:
        df:
            DataFrame containing the new data to be uploaded to the database.
            The columns to be updated need to have the same headers between
            the df and the table in the database.
        model:
            The model that is being updated.
        index:
            Header of the column to join on, determines which rows in the
            different tables match. If None, then use the primary key column.
        columns:
            The column headers of the columns to be updated. If None, updates
            all columns except the index column.

    Returns:
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
