import os
import logging

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS

from ..survey.translators import tr_selavy

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
    """FitsImage class"""

    entire_image = True

    def __init__(self, path, hdu_index=0):
        # inherit from parent
        super().__init__(path)

        # set other attributes
        header = self.__get_header(hdu_index)
        self.polarisation = header.get('STOKES', 'I')

        # set the rest of the attributes
        self.__set_data_for_telescope(header)

        # get the frequency
        self.__get_frequency(header)

    def __get_header(self, hdu_index):
        with fits.open(self.path) as hdulist:
            hdu = hdulist[hdu_index]
        return hdu.header.copy()

    def __set_data_for_telescope(self, header):
        '''
        set the image attributes depending on the telescope type
        '''
        self.datetime = pd.Timestamp('1900-01-01T00:00:00')
        self.beam_bmaj = 0.
        self.beam_bmin = 0.
        self.beam_bpa = 0.
        self.ra = None
        self.dec = None
        self.fov_bmaj = None
        self.fov_bmin = None

        if header.get('TELESCOP', None) == 'ASKAP':
            self.time = pd.Timestamp(header['DATE'], tz=header['TIMESYS'])
            self.beam_bmaj = header['BMAJ']
            self.beam_bmin = header['BMIN']
            self.beam_bpa = header['BPA']

            params = {
                'header': header,
                'fits_naxis1': 'NAXIS1',
                'fits_naxis2': 'NAXIS2',
                'fits_cdelt1': 'CDELT1',
                'fits_cdelt2': 'CDELT2'
            }

            # set the coordinate attributes
            self.__get_coordinates(**params)

        # get the time as Julian Datetime using Pandas function
        self.jd = self.time.to_julian_date()


    def __get_coordinates(self, header, fits_naxis1, fits_naxis2, fits_cdelt1, fits_cdelt2):
        wcs = WCS(header, naxis=2)
        x = header[fits_naxis1]
        y = header[fits_naxis2]
        pix_centre = [[x / 2., y / 2.], [x / 2., y / 2.]]
        # sky_centre = wcs.wcs_pix2sky(pix_centre, 1)
        sky_centre = wcs.wcs_pix2world(pix_centre, 1)
        self.ra = float(sky_centre[0][0])
        self.dec = float(sky_centre[0][1])

        # The field-of-view (in pixels) is assumed to be a circle in the centre
         # of the image. This may be an ellipse on the sky, eg MOST images.
        # We leave a pixel margin at the edge that we don't use.
        # TODO: move unused pixel as argument
        unusedpix = 0.
        usable_radius_pix = self.__get_radius_pixels(header, fits_naxis1, fits_naxis2) - unusedpix
        self.fov_bmin = usable_radius_pix * abs(header[fits_cdelt1])
        self.fov_bmaj = usable_radius_pix * abs(header[fits_cdelt2])

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
            if header['TELESCOP'] in ('LOFAR', 'AARTFAAC'):
                self.freq_eff = header['RESTFRQ']
                if 'RESTBW' in header:
                    self.freq_bw = header['RESTBW']

                else:
                    logger.warning("bandwidth header missing in image {},"
                                   " setting to 1 MHz".format(self.url))
                    self.freq_bw = 1e6
            else:
                if ('ctype3' in header) and (header['ctype3'] in ('FREQ', 'VOPT')):
                    self.freq_eff = header['crval3']
                    self.freq_bw = header['cdelt3']
                elif ('ctype4' in header) and (header['ctype4'] in ('FREQ', 'VOPT')):
                    self.freq_eff = header['crval4']
                    self.freq_bw = header['cdelt4']
                else:
                    self.freq_eff = header['restfreq']
                    self.freq_bw = 0.0
        except Exception:
            msg = f"Frequency not specified in headers for {self.name}"
            logger.error(msg)
            raise TypeError(msg)


class SelavyImage(FitsImage):
    """Fits images that have a selavy catalogue"""

    def __init__(self, path, selavy_path, hdu_index=0):
        # inherit from parent
        self.selavy_path = selavy_path
        super().__init__(path, hdu_index)

    def read_selavy(self):
        """
        read the sources from the selavy catalogue, select wanted columns
        and remap them to correct names
        """
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
        return df
