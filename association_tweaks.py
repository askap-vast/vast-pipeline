import pandas as pd
import logging
from vast_pipeline.utils.utils import StopWatch

import numpy as np

def calculate_wavg_coords(sources_df):
    iter_timer = StopWatch()
    ra = sources_df.ra.values
    dec = sources_df.dec.values
    ra_wrap_mask = ra <= 0.1 # Why is this 0.1 and not 0.0? Is this the cause of issue 711?
    ra[ra_wrap_mask] = ra[ra_wrap_mask] + 360.

    sources_df['interim_ew'] = (
        ra * sources_df['weight_ew'].values
    )
    sources_df['interim_ns'] = (
        dec * sources_df['weight_ns'].values
    )

    tmp_srcs_df = (
        sources_df.loc[
            (sources_df['source'] != -1) & (sources_df['forced'] == False),
            [
                'ra', 'dec', 'uncertainty_ew', 'uncertainty_ns',
                'source', 'interim_ew', 'interim_ns', 'weight_ew',
                'weight_ns'
            ]
        ]
        .groupby('source', sort=False)
    )
    logger.debug(
        'Time to handle RA wrapping: %.2f',
        iter_timer.reset(),
    )

    weight_ew = tmp_srcs_df['weight_ew'].sum()
    weight_ns = tmp_srcs_df['weight_ns'].sum()

    wm_ra = tmp_srcs_df['interim_ew'].sum() / weight_ew
    wm_uncertainty_ew = 1. / np.sqrt(weight_ew)

    wm_dec = tmp_srcs_df['interim_ns'].sum() / weight_ns
    wm_uncertainty_ns = 1. / np.sqrt(weight_ns)

    weighted_df = (
        pd.concat(
            [wm_ra, wm_uncertainty_ew, wm_dec, wm_uncertainty_ns],
            axis=1,
            sort=False,
        )
        .reset_index()
        .rename(
            columns={
                0: "ra",
                "weight_ew": "uncertainty_ew",
                1: "dec",
                "weight_ns": "uncertainty_ns",
            }
        )
    )

    # correct the RA wrapping
    weighted_ra = weighted_df.ra.values
    ra_wrap_mask = weighted_ra >= 360.
    weighted_df.loc[
        ra_wrap_mask, 'ra'
    ] = weighted_ra[ra_wrap_mask] - 360.

    logger.debug(
        'Time to recalculate wavg coordinates: %.2f',
        iter_timer.reset()
    )
    
    return weighted_df



logger = logging.getLogger()
associated_df = pd.read_parquet('results_new_new.parquet')

associated_df = associated_df[associated_df.skyreg_group == 1]

grouped = associated_df.groupby('skyreg_id')

test_key = list(grouped.groups.keys())[0]
print(test_key)

skyreg_df = grouped.get_group(test_key)

print(skyreg_df)

weighted_df = calculate_wavg_coords(skyreg_df)

print(weighted_df)


exit()



for it, epoch in enumerate(epochs):
    logger.info(
        'Starting association iteration: %i/%i%s',
        it + 1,
        num_iterations,
        skyreg_tag
    )
    logger.debug('len(skyc1): %i%s', len(skyc1_srcs), skyreg_tag)
    # load skyc2 source measurements and create SkyCoord
    images_df_rows = images_df.loc[images_df['epoch'] == epoch]
    images = (
        images_df_rows['image_dj'].to_list()
    )
    image_names = (
        images_df_rows['image_name'].to_list()
    )
    
    image_name_str = ",".join(image_names)
    logger.info('Loaded %s%s', image_name_str, skyreg_tag)

    max_beam_maj = (
        images_df.loc[images_df["epoch"] == epoch, "image_dj"]
        .apply(lambda x: x.beam_bmaj)
        .max()
    )
    skyc2_srcs = prep_skysrc_df(
        images, config["measurements"]["flux_fractional_error"], duplicate_limit
    )
    logger.debug('len(skyc2_srcs): %i%s', len(skyc2_srcs), skyreg_tag)

    skyc2_srcs["epoch"] = epoch
    skyc2 = SkyCoord(
        skyc2_srcs["ra"].values, skyc2_srcs["dec"].values, unit=(u.deg, u.deg)
    )

    
    iter_timer.reset()
    if method == 'basic':
        sources_df, skyc1_srcs = basic_association(
            sources_df,
            skyc1_srcs,
            skyc1,
            skyc2_srcs,
            skyc2,
            limit,
        )

    elif method in ["advanced", "deruiter"]:
        if method == "deruiter":
            bw_max = Angle(bw_limit * (max_beam_maj * 3600.0 / 2.0) * u.arcsec)
        else:
            bw_max = limit
        sources_df, skyc1_srcs = advanced_association(
            method,
            sources_df,
            skyc1_srcs,
            skyc1,
            skyc2_srcs,
            skyc2,
            dr_limit,
            bw_max,
        )
    else:
        raise Exception('association method not implemented!')
    logger.debug(
        'Time to carry out association: %.2f%s',
        iter_timer.reset(),
        skyreg_tag
    )

    logger.info(
        "Calculating weighted average RA and Dec for sources%s...", skyreg_tag
    )

    # account for RA wrapping
    iter_timer.reset()
    ra = sources_df.ra.values
    dec = sources_df.dec.values
    ra_wrap_mask = ra <= 0.1 # Why is this 0.1 and not 0.0? Is this the cause of issue 711?
    ra[ra_wrap_mask] = ra[ra_wrap_mask] + 360.

    sources_df['interim_ew'] = (
        ra * sources_df['weight_ew'].values
    )
    sources_df['interim_ns'] = (
        dec * sources_df['weight_ns'].values
    )

    tmp_srcs_df = (
        sources_df.loc[
            (sources_df['source'] != -1) & (sources_df['forced'] == False),
            [
                'ra', 'dec', 'uncertainty_ew', 'uncertainty_ns',
                'source', 'interim_ew', 'interim_ns', 'weight_ew',
                'weight_ns'
            ]
        ]
        .groupby('source', sort=False)
    )
    logger.debug(
        'Time to handle RA wrapping: %.2f%s',
        iter_timer.reset(),
        skyreg_tag
    )

    weight_ew = tmp_srcs_df['weight_ew'].sum()
    weight_ns = tmp_srcs_df['weight_ns'].sum()

    wm_ra = tmp_srcs_df['interim_ew'].sum() / weight_ew
    wm_uncertainty_ew = 1. / np.sqrt(weight_ew)

    wm_dec = tmp_srcs_df['interim_ns'].sum() / weight_ns
    wm_uncertainty_ns = 1. / np.sqrt(weight_ns)

    weighted_df = (
        pd.concat(
            [wm_ra, wm_uncertainty_ew, wm_dec, wm_uncertainty_ns],
            axis=1,
            sort=False,
        )
        .reset_index()
        .rename(
            columns={
                0: "ra",
                "weight_ew": "uncertainty_ew",
                1: "dec",
                "weight_ns": "uncertainty_ns",
            }
        )
    )

    # correct the RA wrapping
    weighted_ra = weighted_df.ra.values
    ra_wrap_mask = weighted_ra >= 360.
    weighted_df.loc[
        ra_wrap_mask, 'ra'
    ] = weighted_ra[ra_wrap_mask] - 360.

    logger.debug(
        'Time to recalculate wavg coordinates: %.2f%s',
        iter_timer.reset(),
        skyreg_tag
    )

    logger.info(
        "Finalising base sources catalogue ready for next iteration%s...",
        skyreg_tag,
    )

    # merge the weighted ra and dec and replace the values
    skyc1_srcs = skyc1_srcs.merge(
        weighted_df, on="source", how="left", suffixes=("", "_skyc2")
    )
    del tmp_srcs_df, weighted_df

    skyc1_srcs['ra'] = skyc1_srcs['ra_skyc2']
    skyc1_srcs['dec'] = skyc1_srcs['dec_skyc2']
    skyc1_srcs['uncertainty_ew'] = skyc1_srcs['uncertainty_ew_skyc2']
    skyc1_srcs['uncertainty_ns'] = skyc1_srcs['uncertainty_ns_skyc2']
    skyc1_srcs = skyc1_srcs.drop(
        ["ra_skyc2", "dec_skyc2", "uncertainty_ew_skyc2", "uncertainty_ns_skyc2"],
        axis=1,
    )

    # generate new sky coord ready for next iteration
    skyc1 = SkyCoord(
        skyc1_srcs["ra"].values, skyc1_srcs["dec"].values, unit=(u.deg, u.deg)
    )

    # and update relations in skyc1
    skyc1_srcs = skyc1_srcs.drop("related", axis=1)
    relations_unique = pd.DataFrame(
        sources_df[sources_df["related"].notna()]
        .explode("related")
        .groupby("source")["related"]
        .apply(lambda x: x.unique().tolist())
    )

    skyc1_srcs = skyc1_srcs.merge(
        relations_unique, how="left", left_on="source", right_index=True
    )
    
    logger.debug(
        'Time to finalise sources: %.2f%s',
        iter_timer.reset(),
        skyreg_tag
    )
    
    logger.debug(
        'Time to finalise sources: %.2f%s',
        iter_timer.reset(),
        skyreg_tag
    )

    logger.info(
        'Completed association iteration: %i/%i%s',
        it + 1,
        num_iterations,
        skyreg_tag
    )

# End of iteration over images, ra and dec columns are actually the
# average over each iteration so remove ave ra and ave dec used for
# calculation and use ra_source and dec_source columns
sources_df = sources_df.drop(["ra", "dec"], axis=1).rename(
    columns={"ra_source": "ra", "dec_source": "dec"}
)

del skyc1_srcs, skyc2_srcs

# sort by the datetime of the image as this makes sure that we do things
# correctly when computing missing_sources_df
sources_df = sources_df.sort_values(by='datetime')

# Finally the related column Null entries are filled with a list containing "NULL"
# to avoid dask schema issues later on.
related_null_mask = sources_df["related"].isnull()
sources_df.loc[related_null_mask, "related"] = "NULL"
sources_df.loc[related_null_mask, "related"] = sources_df.loc[related_null_mask, "related"].apply(
    lambda x: [x,]
)
#sources_df.reset_index(inplace=True)
sources_df['skyreg_id'] = skyreg
sources_df['skyreg_group'] = skyreg_group


logger.info(
    "Total association time: %.2f seconds%s.", timer.reset_init(), skyreg_tag
)
