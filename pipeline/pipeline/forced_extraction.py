import logging
import pandas as pd

from .utils import cartesian_product
from pipeline.models import Image


logger = logging.getLogger(__name__)


def forced_extraction(srcs_df, sources_df):
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
    # get all the skyregions and related images
    cols = list(
        'name', 'skyreg__centre_ra','skyreg__centre_dec',
        'skyreg__xtr_radius'
    )
    skyreg_df = pd.DataFrame(list(
        Image.objects.select_related('skyreg').values(*tuple(cols))
    ))
    skyreg_df = (
        skyreg_df.groupby(skyreg_df.columns.drop('name').values.tolist())
        .agg(lambda group: group.values.ravel().tolist())
        .reset_index()
    )


    # create dataframe with all skyregions and sources combinations
    combos = cross_join(srcs_df.reset_index(), skyreg_df)
    combos['sep'] = on_sky_sep(
        combos['wavg_ra'].values,
        combos['centre_ra'].values,
        combos['wavg_dec'].values,
        combos['centre_dec'].values,
    )
    import ipdb; ipdb.set_trace()  # breakpoint cfd8cd8a //

    pass
