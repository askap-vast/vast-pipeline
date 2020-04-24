import os
import logging

import numpy as np
import pandas as pd
from django.conf import settings
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

from .utils import calc_error_radius
from .utils import calc_condon_flux_errors

from pipeline.survey.translators import tr_selavy


logger = logging.getLogger(__name__)


# TODO: improve using Py abstract class ABC
class Image(object):
    """generic abstract class for an image"""
    def __init__(self, path):
        self.name = os.path.basename(path)
        self.path = path

    def __repr__(self):
        return self.name


class FitsImage(Image):
    """FitsImage class to model FITS files"""

    entire_image = True

    def __init__(self, path, hdu_index=0):
        # inherit from parent
        super().__init__(path)

        # set other attributes
        header = self.__get_header(hdu_index)

        # set the rest of the attributes
        self.__set_img_attr_for_telescope(header)

        # get the frequency
        self.__get_frequency(header)

    def __get_header(self, hdu_index):
        try:
            with fits.open(self.path) as hdulist:
                hdu = hdulist[hdu_index]
        except Exception as e:
            raise e
        return hdu.header.copy()

    def __set_img_attr_for_telescope(self, header):
        '''
        set the image attributes depending on the telescope type
        '''
        self.polarisation = header.get('STOKES', 'I')
        self.duration = float(header.get('DURATION', 0.))
        self.beam_bmaj = 0.
        self.beam_bmin = 0.
        self.beam_bpa = 0.
        self.ra = None
        self.dec = None
        self.fov_bmaj = None
        self.fov_bmin = None

        if header.get('TELESCOP', None) == 'ASKAP':
            try:
                self.datetime = pd.Timestamp(header['DATE-OBS'], tz=header['TIMESYS'])
                self.beam_bmaj = header['BMAJ']
                self.beam_bmin = header['BMIN']
                self.beam_bpa = header['BPA']
            except KeyError as e:
                logger.exception(
                    "Image %s does not contain expected FITS header keywords.",
                    self.name,
                )
                raise e

            params = {
                'header': header,
                'fits_naxis1': 'NAXIS1',
                'fits_naxis2': 'NAXIS2',
            }

            # set the coordinate attributes
            self.__get_img_coordinates(**params)

        # get the time as Julian Datetime using Pandas function
        self.jd = self.datetime.to_julian_date()

    def __get_img_coordinates(self, header, fits_naxis1, fits_naxis2):
        """
        set the image attributes ra, dec, fov_bmin and fov_bmaj, radius
        from the image file header
        """
        wcs = WCS(header, naxis=2)
        pix_centre = [[header[fits_naxis1] / 2., header[fits_naxis2] / 2.]]
        self.ra, self.dec = wcs.wcs_pix2world(pix_centre, 1)[0]

        # The field-of-view (in pixels) is assumed to be a circle in the centre
         # of the image. This may be an ellipse on the sky, eg MOST images.
        # We leave a pixel margin at the edge that we don't use.
        # TODO: move unused pixel as argument
        unusedpix = 0.
        usable_radius_pix = self.__get_radius_pixels(header, fits_naxis1, fits_naxis2) - unusedpix
        cdelt1, cdelt2 = proj_plane_pixel_scales(WCS(header).celestial)
        self.fov_bmin = usable_radius_pix * abs(cdelt1)
        self.fov_bmaj = usable_radius_pix * abs(cdelt2)

        # set the pixels radius
        # TODO: check calcs
        self.radius_pixels = usable_radius_pix

    def __get_radius_pixels(self, header, fits_naxis1, fits_naxis2):
        """
        Return the radius (pixels) of the full image.
        If the image is not a square/circle then the shortest radius will be returned.
        """
        if self.entire_image:
            #a large circle that *should* include the whole image (and then some)
            diameter = np.hypot(header[fits_naxis1], header[fits_naxis2])
        else:
            # We simply place the largest circle we can in the centre.
            diameter = min(header[fits_naxis1], header[fits_naxis2])
        return diameter / 2.

    def __get_frequency(self, header):
        """
        Set some 'shortcut' variables for access to the frequency parameters
        in the FITS file header.

        @param hdulist: hdulist to parse
        @type hdulist: hdulist
        """
        self.freq_eff = None
        self.freq_bw = None
        try:
            if ('ctype3' in header) and (header['ctype3'] in ('FREQ', 'VOPT')):
                self.freq_eff = header['crval3']
                self.freq_bw = header['cdelt3'] if 'cdelt3' in header else 0.0
            elif ('ctype4' in header) and (header['ctype4'] in ('FREQ', 'VOPT')):
                self.freq_eff = header['crval4']
                self.freq_bw = header['cdelt4'] if 'cdelt4' in header else 0.0
            else:
                self.freq_eff = header['restfreq']
                self.freq_bw = header['restbw'] if 'restbw' in header else 0.0
        except Exception:
            msg = f"Frequency not specified in headers for {self.name}"
            logger.error(msg)
            raise TypeError(msg)


class SelavyImage(FitsImage):
    """Fits images that have a selavy catalogue"""

    def __init__(self, path, selavy_path, hdu_index=0, config=None):
        # inherit from parent
        self.selavy_path = selavy_path
        self.config = config
        super().__init__(path, hdu_index)

    def read_selavy(self, dj_image):
        """
        read the sources from the selavy catalogue, select wanted columns
        and remap them to correct names
        """
        # TODO: improve with loading only the cols we need and set datatype
        df = pd.read_fwf(self.selavy_path)
        # drop first line with unit of measure, select only wanted
        # columns and rename them
        df = (
            df.drop(0)
            .loc[:, tr_selavy.keys()]
            .rename(columns={x : tr_selavy[x]['name'] for x in tr_selavy})
        )

        # fix dtype of columns
        for ky in tr_selavy:
            key = tr_selavy[ky]
            if df[key['name']].dtype != key['dtype']:
                df[key['name']] = df[key['name']].astype(key['dtype'])

        # do checks and fill in missing field for uploading sources
        # in DB (see fields in models.py -> Source model)
        if df['component_id'].duplicated().any():
            raise Exception('Found duplicated names in sources')

        # add fields from image and fix name column
        df['image_id'] = dj_image.id
        df['time'] = dj_image.datetime

        # append img prefix to source name
        img_prefix = dj_image.name.split('.i.', 1)[-1].split('.', 1)[0] + '_'
        df['name'] = img_prefix + df['component_id']

        # # fix error fluxes
        for col in ['flux_int_err', 'flux_peak_err']:
            sel = df[col] < settings.FLUX_DEFAULT_MIN_ERROR
            if sel.any():
                df.loc[sel, col] = settings.FLUX_DEFAULT_MIN_ERROR

        # # fix error ra dec
        for col in ['ra_err', 'dec_err']:
            sel = df[col] < settings.POS_DEFAULT_MIN_ERROR
            if sel.any():
                df.loc[sel, col] = settings.POS_DEFAULT_MIN_ERROR
            df[col] = df[col] / 3600.

        logger.debug("Calculating errors...")
        # TODO: avoid extra column given that it is a single value
        df['ew_sys_err'] = self.config.ASTROMETRIC_UNCERTAINTY_RA / 3600.
        df['ns_sys_err'] = self.config.ASTROMETRIC_UNCERTAINTY_DEC / 3600.

        df['error_radius'] = calc_error_radius(
            df['ra'].values,
            df['ra_err'].values,
            df['dec'].values,
            df['dec_err'].values,
        )

        df['uncertainty_ew'] = np.hypot(
            df['ew_sys_err'].values, df['error_radius'].values
        )

        df['uncertainty_ns'] = np.hypot(
            df['ns_sys_err'].values, df['error_radius'].values
        )

        # weight calculations to use later
        df['weight_ew'] = 1. / df['uncertainty_ew'].values**2
        df['weight_ns'] = 1. / df['uncertainty_ns'].values**2

        df['snr'] = df['flux_peak'] / df['rms_image']

        if self.config.USE_CONDON_ERRORS:
            theta_n = np.hypot(dj_image.beam_bmaj, dj_image.beam_bmin)

            df[['condon_flux_peak_err', 'condon_flux_int_err']] = df.apply(
                calc_condon_flux_errors,
                args=(theta_n,),
                axis=1,
                result_type='expand'
            )

        df['condon_flux_peak_err'] = df['condon_flux_peak_err'] * 1.e3
        df['condon_flux_int_err'] = df['condon_flux_int_err'] * 1.e3

        df.to_csv("selavy_fluxes_condon.csv", index=False)

        import ipdb; ipdb.set_trace() # BREAKPOINT

        logger.debug('Errors calculation done.')

        return df
