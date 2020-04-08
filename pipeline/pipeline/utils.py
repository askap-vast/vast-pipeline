import os
import logging
import numpy as np
import pandas as pd

from ..utils.utils import eq_to_cart
from ..models import Band, Image, Run, SkyRegion, Measurement


logger = logging.getLogger(__name__)


def get_measurement_models(row):
    one_m = Measurement()
    for fld in one_m._meta.get_fields():
        if getattr(fld, 'attname', None) and fld.attname in row.index:
            setattr(one_m, fld.attname, row[fld.attname])
    return one_m


def get_create_skyreg(p_run, image):
    skyr = SkyRegion.objects.filter(
        centre_ra=image.ra,
        centre_dec=image.dec,
        xtr_radius=image.radius_pixels
    )
    if skyr:
        skyr = skyr.get()
        logger.info('Found sky region %s', skyr)
        if p_run not in skyr.run.all():
            logger.info('Adding %s to sky region %s', p_run, skyr)
            skyr.run.add(p_run)
        return skyr

    x, y, z = eq_to_cart(image.ra, image.dec)
    skyr = SkyRegion(
        centre_ra=image.ra,
        centre_dec=image.dec,
        xtr_radius=image.radius_pixels,
        x=x,
        y=y,
        z=z,
    )
    skyr.save()
    logger.info('Created sky region %s', skyr)
    skyr.run.add(p_run)
    logger.info('Adding %s to sky region %s', p_run, skyr)
    return skyr


def get_create_img_band(image):
    '''
    Return the existing Band row for the given FitsImage.
    An image is considered to belong to a band if its frequency is within some
    tolerance of the band's frequency.
    Returns a Band row or None if no matching band.
    '''
    # For now we match bands using the central frequency.
    # This assumes that every band has a unique frequency,
    # which is true for the data we've used so far.
    freq = int(image.freq_eff * 1.e-6)
    freq_band = int(image.freq_bw * 1.e-6)
    # TODO: refine the band query
    for band in Band.objects.all():
        diff = abs(freq - band.frequency) / float(band.frequency)
        if diff < 0.02:
            return band.id

    # no band has been found so create it
    band = Band(name=str(freq), frequency=freq, bandwidth=freq_band)
    logger.info('Adding new frequency band: %s', band)
    band.save()

    return band.id


def get_create_img(p_run, band_id, image):
    img = Image.objects.filter(name__exact=image.name)
    if img.exists():
        img = img.get()
        skyreg = get_create_skyreg(p_run, img)
        # check and add the many to many if not existent
        if not Image.objects.filter(
            id=img.id, run__id=p_run.id
        ).exists():
            img.run.add(p_run)

        return (img, True)

    # at this stage measurement parquet file not created but assume location
    img_folder_name = '_'.join([
        image.name.split('.i.', 1)[-1].split('.', 1)[0],
        image.datetime.isoformat()
    ])
    measurements_path = os.path.join(
        p_run.path,
        img_folder_name,
        'measurements.parquet'
        )
    img = Image(
        band_id=band_id,
        measurements_path=measurements_path
    )
    # set the attributes and save the image,
    # by selecting only valid (not hidden) attributes
    # FYI attributs and/or method starting with _ are hidden
    # and with __ can't be modified/called
    for fld in img._meta.get_fields():
        if getattr(fld, 'attname', None) and getattr(image, fld.attname, None):
            setattr(img, fld.attname, getattr(image, fld.attname))

    # get create the sky region and associate with image
    skyreg = get_create_skyreg(p_run, img)
    img.skyreg = skyreg

    img.save()
    img.run.add(p_run)

    return (img, False)


def get_create_p_run(name, path):
    p_run = Run.objects.filter(name__exact=name)
    if p_run:
        return p_run.get()

    p_run = Run(name=name, path=path)
    p_run.save()

    return p_run


def prep_skysrc_df(image, perc_error, ini_df=False):
    '''
    initiliase the source dataframe to use in association logic by
    reading the measurement parquet file and creating columns
    inputs
    image: django image model
    ini_df: flag to initialise source id depending if inital df or not
    '''
    cols = [
    'id',
    'ra',
    'uncertainty_ew',
    'weight_ew',
    'dec',
    'uncertainty_ns',
    'weight_ns',
    'flux_int',
    'flux_int_err',
    'flux_peak',
    'flux_peak_err'
    ]

    df = pd.read_parquet(image.measurements_path, columns=cols)
    df['img'] = image.name
    # these are the first 'sources'
    df['source'] = df.index + 1 if ini_df else -1
    df['ra_source'] = df['ra']
    df['uncertainty_ew_source'] = df['uncertainty_ew']
    df['dec_source'] = df['dec']
    df['uncertainty_ns_source'] = df['uncertainty_ns']
    df['d2d'] = 0.
    df['dr'] = 0.
    df['related'] = None
    logger.info('Correcting flux errors with config error setting...')
    for col in ['flux_int', 'flux_peak']:
        df[f'{col}_err'] = np.hypot(
            df[f'{col}_err'].values, perc_error * df[col].values
        )

    return df


def get_or_append_list(obj_in, elem):
    '''
    return a list with elem in it, if obj_in is list append to it
    '''
    if isinstance(obj_in, list):
        out = obj_in
        out.append(elem)
        return out

    return [elem]
