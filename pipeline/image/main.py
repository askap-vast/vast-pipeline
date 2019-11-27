import os
import logging
import pandas as pd
from astropy.io import fits


logger = logging.getLogger(__name__)


class Image(object):
    """generic abstract class for an image"""
    def __init__(self, path):
        self.name = os.path.basename(path)
        self.path = path

    def __repr__(self):
        return self.name


class FitsImage(Image):
    """FitsImage class"""

    def __init__(self, path, hdu_index=0):
        # inherit from parent
        super().__init__(path)

        self.header = self.__get_header(hdu_index)
        self.polarisation = self.header.get('STOKES', 'I')

        # set the rest of the attributes
        self.__set_data_for_telescope()

        # get the frequency
        self.__get_frequency()

    def __get_header(self, hdu_index):
        with fits.open(self.path) as hdulist:
            hdu = hdulist[hdu_index]
        return hdu.header.copy()

    def __set_data_for_telescope(self):
        self.datetime = pd.Timestamp('1900-01-01T00:00:00')
        self.beam_bmaj = None
        self.beam_bmin = None
        self.beam_bpa = None

        if self.header.get('TELESCOP', None) == 'ASKAP':
            self.datetime = pd.Timestamp(self.header['DATE'])
            self.beam_bmaj = self.header['BMAJ']
            self.beam_bmin = self.header['BMIN']
            self.beam_bpa = self.header['BPA']

    def __get_frequency(self):
        """
        Set some 'shortcut' variables for access to the frequency parameters
        in the FITS file header.

        @param hdulist: hdulist to parse
        @type hdulist: hdulist
        """
        self.freq_eff = None
        self.freq_bw = None
        try:
            header = self.header
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

    def __init__(self, path, hdu_index=0):
        # inherit from parent
        super().__init__(path, hdu_index)

    def read_selavy(self):
        """
        read the sources from the selavy catalogue, select wanted columns
        and remap them to correct names
        """
        cols_map = {
            "island_id":"island",
            "component_id":"source",
            "rms_image":"local_rms",
            "ra_deg_cont":"ra",
            "ra_err":"err_ra",
            "dec_deg_cont":"dec",
            "dec_err":"err_dec",
            "flux_peak":"peak_flux",
            "flux_peak_err":"err_peak_flux",
            "flux_int":"int_flux",
            "flux_int_err":"err_int_flux",
            "maj_axis":"a",
            "maj_axis_err":"err_a",
            "min_axis":"b",
            "min_axis_err":"err_b",
            "pos_ang":"pa",
            "pos_ang_err":"err_pa",
            "maj_axis_deconv":"psf_a",
            "min_axis_deconv":"psf_b",
            "pos_ang_deconv":"psf_pa",
            "flag_c4":"flag"
        }

        df = pd.read_fwf(self.path)
        # drop first line, select only wanted columns and rename them
        df = (
            df.drop(0)
            .loc[:, cols_map.keys()]
            .rename(columns=cols_map)
        )
        return df
