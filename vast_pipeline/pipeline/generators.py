# contains all the generators for bulk data uploading
# assumes these are used with apply on a dataframe
import logging

import pandas as pd

from typing import Iterable
from vast_pipeline.utils.utils import deg2hms, deg2dms
from vast_pipeline.models import (
    Association, Measurement, Source, RelatedSource, Run
)


logger = logging.getLogger(__name__)


def measurement_models_generator(
    meas_df: pd.DataFrame
) -> Iterable[Measurement]:
    """
    Creates a generator object containing yielded Measurement objects from
    an input pipeline measurement dataframe.

    Parameters
    ----------
    meas_df: pd.DataFrame
        The dataframe from the pipeline containing the measurements of an image.

    Returns
    -------
    one_m: Iterable[Measurement]
        An iterable generator object containing the yielded Measurement
        objects.
    """
    for i, row in meas_df.iterrows():
        one_m = Measurement()
        for fld in one_m._meta.get_fields():
            if getattr(fld, 'attname', None) and fld.attname in row.index:
                setattr(one_m, fld.attname, row[fld.attname])
        yield one_m


def source_models_generator(
    src_df: pd.DataFrame, pipeline_run: Run
) -> Iterable[Source]:
    """
    Creates a generator object containing yielded Source objects from
    an input pipeline sources dataframe.

    Parameters
    ----------
    src_df: pd.DataFrame
        The dataframe from the pipeline containing the measurements of an image.
    pipeline_run: Run
        The pipeline Run object of which the sources are associated with.

    Returns
    -------
    src: Iterable[Source]
        An iterable generator object containing the yielded Source objects.
    """
    for i, row in src_df.iterrows():
        name = (
            f"ASKAP_{deg2hms(row['wavg_ra'])}"
            f"{deg2dms(row['wavg_dec'])}".replace(":", "")
        )
        src = Source()
        src.run_id = pipeline_run.id
        src.name = name
        for fld in src._meta.get_fields():
            if getattr(fld, 'attname', None) and fld.attname in row.index:
                setattr(src, fld.attname, row[fld.attname])

        yield src


def association_models_generator(
    assoc_df: pd.DataFrame
) -> Iterable[Association]:
    """
    Creates a generator object containing yielded Association objects from
    an input pipeline association dataframe.

    Parameters
    ----------
    assoc_df: pd.DataFrame
        The dataframe from the pipeline containing the associations between
        measurements and sources.

    Returns
    -------
    Association: Iterable[Association]
        An iterable generator object containing the yielded Association objects.
    """
    for i, row in assoc_df.iterrows():
        yield Association(
            meas_id=row['id'],
            source_id=row['source_id'],
            d2d=row['d2d'],
            dr=row['dr'],
        )


def related_models_generator(
    related_df: pd.DataFrame
) -> Iterable[RelatedSource]:
    """
    Creates a generator object containing yielded Association objects from
    an input pipeline association dataframe.

    Parameters
    ----------
    related_df: pd.DataFrame
        The dataframe from the pipeline containing the relations between
        sources.

    Returns
    -------
    RelatedSource: Iterable[RelatedSource]
        An iterable generator object containing the yielded Association objects.
    """
    for i, row in related_df.iterrows():
        yield RelatedSource(**row.to_dict())
