"""
This module contains the relevant classes for the image ingestion.
"""

import os
import logging
import numpy as np
import pandas as pd

from django.conf import settings
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from typing import Dict

from .utils import calc_error_radius
from .utils import calc_condon_flux_errors

from vast_pipeline import models
from vast_pipeline.survey.translators import tr_selavy
from vast_pipeline.image.utils import open_fits


logger = logging.getLogger(__name__)


# TODO: improve using Py abstract class ABC
class Image(object):
    """Generic abstract class for an image.

    Attributes:
        name (str): The image name taken from the file name.
        path (str): The system path to the image.

    """

    def __init__(self, path: str) -> None:
        """
        Initiliase an image object.

        Args:
            path:
                The system path to the FITS image. The name of the image is
                taken from the filename in the given path.

        Returns:
            None.
        """
        self.name = os.path.basename(path)
        self.path = path

    def __repr__(self) -> str:
        """
        Defines the printable representation.

        Returns:
            Printable representation which is the pipeline run name.
        """
        return self.name


class FitsImage(Image):
    """
    FitsImage class to model FITS files

    Attributes:
        beam_bmaj (float): Major axis size of the restoring beam (degrees).
        beam_bmin (float): Minor axis size of the restoring beam (degrees).
        beam_bpa (float): Position angle of the restoring beam (degrees).
        datetime (pd.Timestamp): Date of the observation.
        duration (float): Duration of the observation in seconds. Is set to
            0 if duration is not in header.
        fov_bmaj (float): Estimate of the field of view in the north-south
            direction (degrees).
        fov_bmin (float): Estimate of the field of view in the east-west
            direction (degrees).
        ra (float): Right ascension coordinate of the image centre (degrees).
        dec (float): Declination coordinate of the image centre (degrees).
        polarisation (str): The polarisation of the image.
    """

    entire_image = True

    def __init__(self, path: str, hdu_index: int = 0) -> None:
        """
        Initialise a FitsImage object.

        Args:
            path:
                The system path of the FITS image.
            hdu_index:
                The index to use on the hdu to fetch the FITS header.

        Returns:
            None.
        """
        # inherit from parent
        super().__init__(path)

        # set other attributes
        header = self.__get_header(hdu_index)

        # set the rest of the attributes
        self.__set_img_attr_for_telescope(header)

        # get the frequency
        self.__get_frequency(header)

    def __get_header(self, hdu_index: int) -> fits.Header:
        """
        Retrieves the header from the FITS image.

        Args:
            hdu_index:
                The index to use on the hdu to fetch the FITS header.

        Returns:
            The FITS header as an astropy.io.fits.Header object.
        """

        try:
            with open_fits(self.path) as hdulist:
                hdu = hdulist[hdu_index]
        except Exception:
            raise IOError((
                'Could not read FITS file: '
                f'{self.path}'
            ))

        return hdu.header.copy()

    def __set_img_attr_for_telescope(self, header):
        '''
        Set the image attributes depending on the telescope type
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
                self.datetime = pd.Timestamp(
                    header['DATE-OBS'], tz=header['TIMESYS']
                )
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

    def __get_img_coordinates(
        self, header: fits.Header, fits_naxis1: str, fits_naxis2: str
    ) -> None:
        """
        Set the image attributes ra, dec, fov_bmin and fov_bmaj, radius
        from the image file header.

        Args:
            header: The FITS header object.
            fits_naxis1: The header keyword of the NAXIS1 to use.
            fits_naxis2: The header keyword of the NAXIS2 to use.

        Returns:
            None
        """
        wcs = WCS(header, naxis=2)
        pix_centre = [[header[fits_naxis1] / 2., header[fits_naxis2] / 2.]]
        self.ra, self.dec = wcs.wcs_pix2world(pix_centre, 1)[0]

        # The field-of-view (in pixels) is assumed to be a circle in the centre
        # of the image. This may be an ellipse on the sky, eg MOST images.
        # We leave a pixel margin at the edge that we don't use.
        # TODO: move unused pixel as argument
        unusedpix = 0.
        usable_radius_pix = self.__get_radius_pixels(
            header, fits_naxis1, fits_naxis2
        ) - unusedpix
        cdelt1, cdelt2 = proj_plane_pixel_scales(WCS(header).celestial)
        self.fov_bmin = usable_radius_pix * abs(cdelt1)
        self.fov_bmaj = usable_radius_pix * abs(cdelt2)
        self.physical_bmin = header[fits_naxis1] * abs(cdelt1)
        self.physical_bmaj = header[fits_naxis2] * abs(cdelt2)

        # set the pixels radius
        # TODO: check calcs
        self.radius_pixels = usable_radius_pix

    def __get_radius_pixels(
        self, header: fits.Header, fits_naxis1: str, fits_naxis2: str
    ) -> float:
        """
        Return the radius (pixels) of the full image.

        If the image is not a square/circle then the shortest radius will be
        returned.

        Args:
            header: The FITS header object.
            fits_naxis1: The header keyword of the NAXIS1 to use.
            fits_naxis2: The header keyword of the NAXIS2 to use.

        Returns:
            The radius of the image in pixels.
        """
        if self.entire_image:
            # a large circle that *should* include the whole image
            # (and then some)
            diameter = np.hypot(header[fits_naxis1], header[fits_naxis2])
        else:
            # We simply place the largest circle we can in the centre.
            diameter = min(header[fits_naxis1], header[fits_naxis2])
        return diameter / 2.

    def __get_frequency(self, header: fits.Header) -> None:
        """
        Set some 'shortcut' variables for access to the frequency parameters
        in the FITS file header.

        Args:
            header: The FITS header object.

        Returns:
            None
        """
        self.freq_eff = None
        self.freq_bw = None
        try:
            freq_keys = ('FREQ', 'VOPT')
            if ('ctype3' in header) and (header['ctype3'] in freq_keys):
                self.freq_eff = header['crval3']
                self.freq_bw = header['cdelt3'] if 'cdelt3' in header else 0.0
            elif ('ctype4' in header) and (header['ctype4'] in freq_keys):
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
    """
    Fits images that have a selavy catalogue.

    Attributes:
        selavy_path (str): The system path to the Selavy file.
        noise_path (str): The system path to the noise image associated
            with the image.
        background_path (str): The system path to the background image
            associated with the image.
        config (Dict): The image configuration settings.
    """

    def __init__(
        self,
        path: str,
        paths: Dict[str, Dict[str, str]],
        config: Dict,
        hdu_index: int = 0,
    ) -> None:
        """
        Initialise the SelavyImage.

        Args:
            path: The system path to the FITS image.
            paths: Dictionary containing the system paths to the associated
                image products and selavy catalogue. The keys are 'selavy',
                'noise', 'background'.
            config: Configuration settings for the image ingestion.
            hdu_index: The index number to use to access the header from the
                hdu object.

        Returns:
            None.
        """
        # inherit from parent
        self.selavy_path = paths['selavy'][path]
        self.noise_path = paths['noise'].get(path, '')
        self.background_path = paths['background'].get(path, '')
        self.config: Dict = config
        super().__init__(path, hdu_index)

    def read_selavy(self, dj_image: models.Image) -> pd.DataFrame:
        """
        Read the sources from the selavy catalogue, select wanted columns
        and remap them to correct names, followed by filtering and Condon
        error calculations.

        Args:
            dj_image: The image model object.

        Returns:
            Dataframe containing the cleaned and processed Selavy components.
        """
        # TODO: improve with loading only the cols we need and set datatype
        if self.selavy_path.endswith(
                ".xml") or self.selavy_path.endswith(".vot"):
            df = Table.read(
                self.selavy_path, format="votable", use_names_over_ids=True
            ).to_pandas()
        elif self.selavy_path.endswith(".csv"):
            # CSVs from CASDA have all lowercase column names
            df = pd.read_csv(self.selavy_path).rename(
                columns={"spectral_index_from_tt": "spectral_index_from_TT"}
            )
        else:
            df = pd.read_fwf(self.selavy_path, skiprows=[1])
        # drop first line with unit of measure, select only wanted
        # columns and rename them
        df = df.loc[:, tr_selavy.keys()].rename(
            columns={x: tr_selavy[x]["name"] for x in tr_selavy}
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

        # drop unrealistic sources
        cols_to_check = [
            'bmaj',
            'bmin',
            'flux_peak',
            'flux_int',
        ]

        bad_sources = df[(df[cols_to_check] == 0).any(axis=1)]
        if bad_sources.shape[0] > 0:
            logger.debug("Dropping %i bad sources.", bad_sources.shape[0])
            df = df.drop(bad_sources.index)

        # dropping tiny sources
        nr_sources_old = df.shape[0]
        df = df.loc[
            (df['bmaj'] > dj_image.beam_bmaj * 500) &
            (df['bmin'] > dj_image.beam_bmin * 500)
        ]
        if df.shape[0] != nr_sources_old:
            logger.info(
                'Dropped %i tiny sources.', nr_sources_old - df.shape[0]
            )

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

        # replace 0 local_rms values using user config value
        df.loc[
            df['local_rms'] == 0., 'local_rms'
        ] = self.config["selavy_local_rms_fill_value"]

        df['snr'] = df['flux_peak'].values / df['local_rms'].values
        df['compactness'] = df['flux_int'].values / df['flux_peak'].values

        if self.config["condon_errors"]:
            logger.debug("Calculating Condon '97 errors...")
            theta_B = dj_image.beam_bmaj
            theta_b = dj_image.beam_bmin

            df[[
                'flux_peak_err',
                'flux_int_err',
                'err_bmaj',
                'err_bmin',
                'err_pa',
                'ra_err',
                'dec_err',
            ]] = df[[
                'flux_peak',
                'flux_int',
                'bmaj',
                'bmin',
                'pa',
                'snr',
                'local_rms',
            ]].apply(
                calc_condon_flux_errors,
                args=(theta_B, theta_b),
                axis=1,
                result_type='expand'
            )

            logger.debug("Condon errors done.")

        # TODO: avoid extra column given that it is a single value
        df['ew_sys_err'] = self.config["ra_uncertainty"] / 3600.
        df['ns_sys_err'] = self.config["dec_uncertainty"] / 3600.

        
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
        
        # Initialise the forced column as False
        df['forced'] = False

        # Calculate island flux fractions
        island_flux_totals = (
            df[['island_id', 'flux_int', 'flux_peak']]
            .groupby('island_id')
            .agg('sum')
        )

        df['flux_int_isl_ratio'] = (
            df['flux_int'].values
            / island_flux_totals.loc[df['island_id']]['flux_int'].values
        )

        df['flux_peak_isl_ratio'] = (
            df['flux_peak'].values
            / island_flux_totals.loc[df['island_id']]['flux_peak'].values
        )

        return df
