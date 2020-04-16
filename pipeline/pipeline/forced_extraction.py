import logging
import numpy as np
import pandas as pd

from astropy import units as u
from astropy.coordinates import SkyCoord

from pipeline.models import Image
from pipeline.image.utils import on_sky_sep
from .forced_phot import ForcedPhot
from .utils import cross_join


logger = logging.getLogger(__name__)


def get_image_list_diff(row):
    out = []
    for image in row['skyrg_img_list']:
        if image not in row['img_list']:
            out.append(image)

    # set empty list to -1
    if not out:
        out = -1

    return out


def extract_from_image(df, images_df):
    P_islands = SkyCoord(
        df['wavg_ra'].values * u.deg,
        df['wavg_dec'].values * u.deg
    )

    image, noise, background = images_df.loc[
        df['image'].iloc[0],
        ['path', 'noise_path', 'background_path']
    ]
    FP = ForcedPhot(image, background, noise)
    flux, flux_err, chisq, DOF = FP.measure(
        P_islands,
        cluster_threshold=3
    )
    import ipdb; ipdb.set_trace()  # breakpoint 99f075aa //
    df['flux'] = flux
    df['flux_err'] = flux_err
    df['chisq'] = chisq
    df['DOF'] = DOF


def forced_extraction(srcs_df, sources_df):
    """
    check and extract expected measurements, and associated them with the
    related source(s)
    """
    # get all the skyregions and related images
    cols = [
        'name', 'measurements_path', 'path', 'noise_path',
        'background_path', 'skyreg__centre_ra', 'skyreg__centre_dec',
        'skyreg__xtr_radius'
    ]
    skyreg_df = pd.DataFrame(list(
        Image.objects.select_related('skyreg').values(*tuple(cols))
    ))
    # grab images df to use later
    images = (
        skyreg_df.copy()
        .drop([x for x in skyreg_df.columns if 'skyreg' in x], axis=1)
        # not necessary now but here for future when many images might
        # belong to same sky region
        .drop_duplicates()
        # assume each image name is unique
        .set_index('name')
    )
    skyreg_df = (
        skyreg_df.groupby(skyreg_df.columns.drop('name').values.tolist())
        .agg(lambda group: group.values.ravel().tolist())
        .reset_index()
        .rename(columns={'name':'skyrg_img_list'})
    )
    skyreg_df.columns = [
        x.replace('skyreg__', '') for x in skyreg_df.columns.values
    ]


    # create dataframe with all skyregions and sources combinations
    cols = [
        'wavg_uncertainty_ew', 'wavg_uncertainty_ns', 'avg_flux_int',
        'avg_flux_peak', 'max_flux_peak', 'v_int', 'v_peak', 'eta_int',
        'eta_peak', 'new', 'related_list', 'src_dj'
    ]
    src_skyrg_df = cross_join(
        (
            srcs_df.drop(cols, axis=1)
            .reset_index()
        ),
        skyreg_df
    )
    src_skyrg_df['sep'] = np.rad2deg(
        on_sky_sep(
            np.deg2rad(src_skyrg_df['wavg_ra'].values),
            np.deg2rad(src_skyrg_df['centre_ra'].values),
            np.deg2rad(src_skyrg_df['wavg_dec'].values),
            np.deg2rad(src_skyrg_df['centre_dec'].values),
        )
    )

    # select rows where separation is less than sky region radius
    # drop not more useful columns and groupby source id
    # compute list of images
    src_skyrg_df = (
        src_skyrg_df.loc[
            src_skyrg_df['sep'] < src_skyrg_df['xtr_radius'],
            ['source', 'skyrg_img_list']
        ]
        .groupby('source')
        .agg(lambda group: list(
            set(sum(group.values.ravel().tolist(), []))
        ))
    )

    # merge into main df and compare the images
    srcs_df = srcs_df.merge(
        src_skyrg_df, left_index=True, right_index=True
    )
    del src_skyrg_df

    srcs_df['img_diff'] = srcs_df[['img_list', 'skyrg_img_list']].apply(
        get_image_list_diff, axis=1
    )

    # prepare df to groupby image and apply force extraction function
    extr_df = srcs_df.loc[
        srcs_df['img_diff'] != -1,
        ['wavg_ra', 'wavg_dec', 'img_diff']
    ].copy()
    extr_df = (
        extr_df.explode('img_diff')
        .rename(columns={'img_diff':'image'})
        .reset_index()
        .groupby('image')
    )
    extr_df = extr_df.apply(extract_from_image, images_df=images)

    import ipdb; ipdb.set_trace()  # breakpoint f3fd8927 //

    pass
