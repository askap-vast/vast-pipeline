import logging
import math
from django.db import models
from django.core.validators import RegexValidator


# Create your models here.
class Survey(models.Model):
    """An external survey eg NVSS, SUMSS"""
    name = models.CharField(
        max_length=32,
        unique=True,
        help_text='Name of the Survey e.g. NVSS'
    )
    comment = models.TextField(max_length=1000, default='', blank=True)
    frequency = models.IntegerField(help_text='Frequency of the survey')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SurveySourceQuerySet(models.QuerySet):

    def cone_search(self, ra, dec, radius_deg):
        """
        Return all the survey sources withing radius_deg of (ra,dec).
        Returns a QuerySet of survey sources, ordered by distance from
        (ra,dec) ascending
        """
        return (
            self.extra(
                select={
                    "distance": "q3c_dist(ra, dec, %s, %s) * 3600"
                },
                select_params=[ra, dec],
                where=["q3c_radial_query(ra, dec, %s, %s, %s)"],
                params=[ra, dec, radius_deg],
            )
            .order_by("distance")
        )


class SurveySource(models.Model):
    """A source from a survey catalogue eg NVSS, SUMSS"""
    # An index on the survey_id field causes queries to perform much worse
    # because there are so few unique surveys, it's a poor field to index.
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)

    name = models.CharField(
        max_length=100,
        help_text='Name of the survey source'
    )

    ra = models.FloatField(help_text='RA of the survey source (Deg)')# degrees
    ra_err = models.FloatField('RA error of the survey source (Deg)')# degrees
    dec = models.FloatField('DEC of the survey source (Deg)')# degrees
    dec_err = models.FloatField('DEC error of the survey source (Deg)')# degrees

    bmaj = models.FloatField(
        help_text=(
            'The major axis of the Gaussian fit to the survey source (arcsecs)'
        )
    )# major axis (arcsecs)
    bmin = models.FloatField(
        help_text=(
            'The minor axis of the Gaussian fit to the survey source (arcsecs)'
        )
    )# minor axis (arcsecs)
    pa = models.FloatField(
        help_text='Position angle of Gaussian fit east of north to bmaj (Deg)'
    )# position angle (degrees east of north)

    flux_peak = models.FloatField(
        help_text='Peak flux of the Guassian fit (Jy)'
    )# Jy/beam
    flux_peak_err = models.FloatField(
        help_text='Peak flux error of the Gaussian fit (Jy)'
    )# Jy/beam
    flux_int = models.FloatField(
        help_text='Integrated flux of the Guassian fit (Jy)'
    )# total flux Jy
    flux_int_err = models.FloatField(
        help_text='Integrated flux of the Guassian fit (Jy)'
    )# Jy

    alpha = models.FloatField(default=0,
        help_text='Spectral index of the survey source'
    )# Spectral index of source
    image_name = models.CharField(max_length=100,
        blank=True,
        help_text='Name of survey image where measurement was made'
    )# image file

    objects = SurveySourceQuerySet.as_manager()

    def __str__(self):
        return f"{self.id} {self.name}"


class Run(models.Model):
    """
    A Run is essentially a pipeline run/processing istance over a set of
    images
    """
    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'[\[@!#$%^&*()<>?/\|}{~:\] ]',
                message='Name contains not allowed characters!',
                inverse_match=True
            ),
        ]
    )
    time = models.DateTimeField(
        auto_now=True,
        help_text='Datetime of run'
    )# run date/time of the pipeline run
    path = models.FilePathField(max_length=200)# the path to the pipeline run
    comment = models.TextField(
        max_length=1000,
        default='',
        blank=True
    )# A description of this pipeline run

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # enforce the full model validation on save
        self.full_clean()
        super(Run, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Override default delete method to also delete related image
        objects only if no other pipeline runs are related to the image.
        """
        logger = logging.getLogger(__name__)
        for image in self.image_set.all():
            if image.run.count() == 1:
                logger.info("Deleting image: %s", image.name)
                deleted_num, deleted_detail = image.delete()
                for instance_type, count in deleted_detail.items():
                    logger.info(
                        "Deleted %d instances of %s", count, instance_type
                    )
        super(Run, self).delete(*args, **kwargs)


class Band(models.Model):
    """
    A band on the frequency spectrum used for imaging. Each image is
    associated with one band.
    """
    name = models.CharField(max_length=12, unique=True)
    frequency = models.IntegerField()# central frequency of band (integer MHz)
    bandwidth = models.IntegerField()# bandwidth (MHz)

    class Meta:
        ordering = ['frequency']

    def __str__(self):
        return self.name


class SkyRegion(models.Model):
    run = models.ManyToManyField(Run)

    centre_ra = models.FloatField()
    centre_dec = models.FloatField()
    xtr_radius = models.FloatField()
    x = models.FloatField()
    y = models.FloatField()
    z = models.FloatField()

    def __str__(self):
        return f'{round(self.centre_ra, 3)}, {round(self.centre_dec, 3)}'


class SourceQuerySet(models.QuerySet):

    def cone_search(self, ra, dec, radius_deg):
        """
        Return all the Sources withing radius_deg of (ra,dec).
        Returns a QuerySet of Sources, ordered by distance from
        (ra,dec) ascending
        """
        return (
            self.extra(
                select={
                    "distance": "q3c_dist(wavg_ra, wavg_dec, %s, %s) * 3600"
                },
                select_params=[ra, dec],
                where=["q3c_radial_query(wavg_ra, wavg_dec, %s, %s, %s)"],
                params=[ra, dec, radius_deg],
            )
            .order_by("distance")
        )


class Source(models.Model):
    run = models.ForeignKey(Run, on_delete=models.CASCADE, null=True,)
    cross_match_sources = models.ManyToManyField(
        SurveySource,
        through='CrossMatch',
        through_fields=('source', 'survey_source')
    )
    related = models.ManyToManyField('self')

    name = models.CharField(max_length=100)
    comment = models.TextField(max_length=1000, default='', blank=True)
    new = models.BooleanField(default=False, help_text='New Source')

    # average fields calculated from the source measurements
    wavg_ra = models.FloatField(
        help_text='The weighted average right ascension (Deg).'
    )
    wavg_dec = models.FloatField(
        help_text='The weighted average declination (Deg).'
    )
    wavg_uncertainty_ew = models.FloatField(
        help_text=(
            'The weighted average uncertainty in the east-.'
            'west (RA) direction (Deg).'
        )
    )
    wavg_uncertainty_ns = models.FloatField(
        help_text=(
            'The weighted average uncertainty in the north-.'
            'south (Dec) direction (Deg).'
        )
    )
    avg_flux_int = models.FloatField(
        help_text='The average integrated flux value.'
    )
    avg_flux_peak = models.FloatField(
        help_text='The average peak flux value.'
    )
    max_flux_peak = models.FloatField(
        help_text='The maximum peak flux value.'
    )

    # metrics
    v_int = models.FloatField(
        help_text='V metric for int flux'
    )
    v_peak = models.FloatField(
        help_text='V metric for peak flux'
    )
    eta_int = models.FloatField(
        help_text='Eta metric for int flux'
    )
    eta_peak = models.FloatField(
        help_text='Eta metric for peak flux'
    )

    objects = SourceQuerySet.as_manager()

    def __str__(self):
        return self.name


class Image(models.Model):
    """An image is a 2D radio image from a cube"""
    band = models.ForeignKey(Band, on_delete=models.CASCADE)
    run = models.ManyToManyField(Run)
    skyreg = models.ForeignKey(SkyRegion, on_delete=models.CASCADE)

    measurements_path = models.FilePathField(
        max_length=200,
        db_column='meas_path'
    )# the path to the measurements parquet that belongs to this image
    polarisation = models.CharField(
        max_length=2,
        help_text='Polarisation of the image e.g. I,XX,YY,Q,U,V'
        )# eg XX,YY,I,Q,U,V
    name = models.CharField(
        max_length=200,
            help_text='Name of the image'
            )
    path = models.FilePathField(
        max_length=500,
        help_text='Path to the file containing the image'
        )# the path to the file containing this image
    noise_path = models.CharField(
        max_length=300,
            blank=True,
        default='',
        help_text='Path to the file containing the RMS image'
        )# includes filename
    background_path = models.CharField(
        max_length=300,
            blank=True,
        default='',
        help_text='Path to the file containing the background image'
        )# includes filename
    valid = models.BooleanField(
        default=True,
        help_text='Is the image valid'
        )# Is the image valid?

    datetime = models.DateTimeField(
        help_text='Date of observation'
    )# date/time of observation, aka epoch
    jd = models.FloatField(
        help_text='Julian date of the observation (days)'
    )# date/time of observation in Julian Date format
    duration =  models.FloatField(
        default=0.,
        help_text='Duration of the observation'
    )# Duration of the observation

    flux_gain = models.FloatField(
        default=1,
        help_text=(
            'Gain of the image, multiplicative factor to change the'
            ' relative flux scale'
        )
    )# flux gain factor
    flux_gain_err = models.FloatField(
        default=0,
        help_text='Error on the image gain'
    )# std in flux gain factor

    ra = models.FloatField(
        help_text='RA of the image centre (Deg)'
    )# RA of image centre (degrees)
    dec = models.FloatField(
        help_text='DEC of the image centre (Deg)'
    )# Dec of image centre (degrees)
    fov_bmaj = models.FloatField(
        help_text='Field of view major axis (Deg)'
    )# Major (Dec) radius of image (degrees)
    fov_bmin = models.FloatField(
        help_text='Field of view minor axis '
    )# Minor (RA) radius of image (degrees)
    radius_pixels = models.FloatField(
        help_text='Radius of the useable region of the image (pixels)'
    )# Radius of the useable region of the image (pixels)

    beam_bmaj = models.FloatField(
        help_text='Major axis of image restoring beam (Deg)'
    )# Beam major axis (degrees)
    beam_bmin = models.FloatField(
        help_text='Minor axis of image restoring beam (Deg)'
    )# Beam minor axis (degrees)
    beam_bpa = models.FloatField(
    )# Beam position angle (degrees)
    rms = models.FloatField(
        default=0,
        help_text='Background RMS based on sigma clipping of image data (mJy)'
    )# Background RMS (mJy)

    flux_percentile = models.FloatField(default=0)# Pixel flux at 95th percentile

    class Meta:
        ordering = ['datetime']

    def __str__(self):
        return self.name


class SourceQuerySet(models.QuerySet):

    def cone_search(self, ra, dec, radius_deg):
        """
        Return all the Sources withing radius_deg of (ra,dec).
        Returns a QuerySet of Sources, ordered by distance from
        (ra,dec) ascending
        """
        return (
            self.extra(
                select={
                    "distance": "q3c_dist(ra, dec, %s, %s) * 3600"
                },
                select_params=[ra, dec],
                where=["q3c_radial_query(ra, dec, %s, %s, %s)"],
                params=[ra, dec, radius_deg],
            )
            .order_by("distance")
        )


class Measurement(models.Model):
    """
    A Measurement is an object in the sky that has been detected at least once.
    Essentially a source single measurement in time.
    """
    image = models.ForeignKey(
        Image,
        null=True,
        on_delete=models.CASCADE
    )# first image seen in
    source = models.ManyToManyField(
        Source,
        through='Association',
        through_fields=('meas', 'source')
    )

    name = models.CharField(max_length=64, unique=True)

    ra = models.FloatField(help_text='RA of the source (Deg)')# degrees
    ra_err = models.FloatField(help_text='RA error of the source (Deg)')
    dec = models.FloatField(help_text='DEC of the source (Deg)')# degrees
    dec_err = models.FloatField(help_text='DEC error of the source (Deg)')

    bmaj = models.FloatField(
        help_text='The major axis of the Gaussian fit to the source (Deg)'
    )# Major axis (degrees)
    err_bmaj = models.FloatField()# Error major axis (degrees)
    bmin = models.FloatField(
        help_text='The minor axis of the Gaussian fit to the source (Deg)'
    )# Minor axis (degrees)
    err_bmin = models.FloatField()# Error minor axis (degrees)
    pa = models.FloatField(
        help_text='Position angle of Gaussian fit east of north to bmaj (Deg)'
    )# Position angle (degrees)
    err_pa = models.FloatField()# Error position angle (degrees)

    # supplied by user via config
    ew_sys_err = models.FloatField(
        help_text='Systematic error in east-west (RA) direction (Deg).'
    )# Systematic error in RA (degrees).
    # supplied by user via config
    ns_sys_err = models.FloatField(
        help_text='Systematic error in north-south (dec) direction (Deg).'
    )# Systematic error in Dec (degrees).

    # estimate of maximum error radius (from ra_err and dec_err)
    error_radius = models.FloatField(
        help_text=(
            'Estimate of maximum error radius using ra_err'
            ' and dec_err (Deg).'
        )
    )# Used in advanced association.

    # quadratic sum of error_radius and ew_sys_err
    uncertainty_ew = models.FloatField(
        help_text=(
            'Total east-west (RA) uncertainty, quadratic sum of error_radius'
            ' and ew_sys_err (Deg).'
        )
    )# Uncertainty in RA (degrees).
     # quadratic sum of error_radius and ns_sys_err
    uncertainty_ns = models.FloatField(
        help_text=(
            'Total north-south (Dec) uncertainty, quadratic sum of error_radius'
            ' and ns_sys_err (Deg).'
        )
    )# Uncertainty in Dec (degrees).

    flux_int = models.FloatField()# Jy/beam
    flux_int_err = models.FloatField()# Jy/beam
    flux_peak = models.FloatField()# Jy/beam
    flux_peak_err = models.FloatField()# Jy/beam
    chi_squared_fit = models.FloatField(
        db_column='chi2_fit',
        help_text='Chi-squared of the Guassian fit to the source'
    )# chi-squared of Gaussian fit
    spectral_index = models.FloatField(
        db_column='spectr_idx',
        help_text='In-band Selavy spectral index'
        )# In band spectral index from Selavy
    spectral_index_from_TT = models.BooleanField(
        default=False,
        db_column='spectr_idx_tt',
        help_text=(
            'True/False if the spectral index came from the taylor'
            ' term came'
        )
        )# Did the spectral index come from the taylor term
    flag_c4 = models.BooleanField(
        default=False,
        help_text='Fit flag from selavy'
    )# Fit flag from selavy file

    has_siblings = models.BooleanField(
        default=False,
        help_text='Does the fit come from an island'
    )# Does the fit come from an island?
    component_id = models.CharField(
        max_length=64,
        help_text='The ID of the component from which the source comes from'
    )# The ID of the component from which the source comes from
    island_id    = models.CharField(
        max_length=64,
        help_text='The ID of the island from which the source comes from'
    )# The ID of the island from which the source comes from

    monitor = models.BooleanField(
        default=False,
        help_text='Are we monitoring this location'
    )# Are we monitoring this location?
    persistent = models.BooleanField(
        default=False,
        help_text='Keep this source between pipeline runs'
    )
    quality = models.NullBooleanField(
        default=False,
        help_text='Is this a quality source for analysis purposes'
    )# Is this a "quality" source for analysis purposes?

    objects = SourceQuerySet.as_manager()

    class Meta:
        ordering = ['ra']

    def __str__(self):
        return self.name


class CrossMatch(models.Model):
    """
    An association between a pipeline source and a survey catalogue source.
    Each pipeline source may be associated with many sources from each
    survey catalogue as multiple survey sources may fit inside the beam of
    the pipeline telescope esp. MWA. The source and survey source rows are
    referenced by name instead of ID so these records can be retained
    between pipeline reprocessing runs that produce different IDs.
    """
    # Foreign keys have on_delete as 'CASCADE' so that we can directly
    # delete things from the source/survey_source tables without having
    # to think about this crossmatch table
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE
    )
    survey_source = models.ForeignKey(
        SurveySource, on_delete=models.CASCADE
    )

    manual = models.BooleanField()# a manual cross-match (vs automatic)
    distance = models.FloatField()# distance source to survey source (degrees)
    probability = models.FloatField()# probability of association
    comment = models.TextField(max_length=1000, default='', blank=True)


class Association(models.Model):
    """
    model association between sources and measurements based on some parameters
    """
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    meas = models.ForeignKey(Measurement, on_delete=models.CASCADE)

    d2d = models.FloatField(
        default=0.,
        help_text='astronomical distance calculated by Astropy, arcsec.'
    )
    dr = models.FloatField(
        default=0.,
        help_text='De Roiter radius calculated in advanced association'
    )

    def __str__(self):
        return f'assoc prob: {self.probability:.2%}'
