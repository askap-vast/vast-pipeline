import math
from django.db import models
from django.core.validators import RegexValidator


# Create your models here.
class Survey(models.Model):
    """An external survey eg NVSS, SUMSS"""
    name = models.CharField(max_length=32, unique=True)
    comment = models.TextField(max_length=1000, blank=True)
    frequency = models.IntegerField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SurveySource(models.Model):
    """A source from a survey catalogue eg NVSS, SUMSS"""
    # An index on the survey_id field causes queries to perform much worse
    # because there are so few unique surveys, it's a poor field to index.
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)

    name = models.CharField(max_length=100, unique=True)

    ra = models.FloatField()  # degrees
    err_ra = models.FloatField()  # degrees
    dec = models.FloatField()  # degrees
    err_dec = models.FloatField()  # degrees

    bmaj = models.FloatField()  # major axis (arcsecs)
    bmin = models.FloatField()  # minor axis (arcsecs)
    pa = models.FloatField()  # position angle (degrees east of north)

    peak_flux = models.FloatField()  # mJy/beam
    err_peak_flux = models.FloatField()  # mJy/beam
    total_flux = models.FloatField()  # total flux mJy
    err_total_flux = models.FloatField()  # mJy

    alpha = models.FloatField(default=0)  # Spectral index of source
    image_name = models.CharField(max_length=100, blank=True)  # image file

    def __str__(self):
        return self.name


class Dataset(models.Model):
    """A dataset is group of cubes (thus images), typically used to group images that can be compared"""
    name = models.CharField(
        max_length=32,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'[\[@!#$%^&*()<>?/\|}{~:\] ]',
                message='Name contains not allowed characters!',
                inverse_match=True
            ),
        ]
    )
    path = models.FilePathField(max_length=200)# the path to the dataset
    comment = models.TextField(max_length=1000, default='', blank=True)  # A description of this dataset

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # enforce the full model validation on save
        self.full_clean()
        super(Dataset, self).save(*args, **kwargs)


class Band(models.Model):
    """A band on the frequency spectrum used for imaging. Each image is associated with one band."""
    name = models.CharField(max_length=12, unique=True)
    frequency = models.IntegerField()  # central frequency of band (integer MHz)
    bandwidth = models.IntegerField()  # bandwidth (MHz)

    class Meta:
        ordering = ['frequency']

    def __str__(self):
        return self.name


class Catalog(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.SET_NULL, null=True,)
    name = models.CharField(max_length=100)

    ave_ra = models.FloatField()
    ave_dec = models.FloatField()

    def __str__(self):
        return self.name


class Image(models.Model):
    """An image is a 2D radio image from a cube"""
    band = models.ForeignKey(Band, on_delete=models.CASCADE)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.SET_NULL, blank=True, null=True
    )

    polarisation = models.CharField(max_length=2)  # eg XX,YY,I,Q,U,V
    name = models.CharField(max_length=200)
    path = models.FilePathField(max_length=200)# the path to the file containing this image
    sources_path = models.FilePathField(max_length=200)# the path to the sources parquet that belongs to this image

    time = models.DateTimeField()  # date/time of observation, aka epoch
    jd = models.FloatField()  # date/time of observation in Julian Date format

    flux_gain = models.FloatField(default=1)  # flux gain factor
    err_flux_gain = models.FloatField(default=0)  # std in flux gain factor

    ra = models.FloatField()  # RA of image centre (degrees)
    dec = models.FloatField()  # Dec of image centre (degrees)
    fov_bmaj = models.FloatField()  # Major (Dec) radius of image (degrees)
    fov_bmin = models.FloatField()  # Minor (RA) radius of image (degrees)
    radius_pixels = models.FloatField()  # Radius of the useable region of the image (pixels)

    beam_bmaj = models.FloatField()  # Beam major axis (degrees)
    beam_bmin = models.FloatField()  # Beam minor axis (degrees)
    beam_bpa = models.FloatField()  # Beam position angle (degrees)
    rms = models.FloatField(default=0)  # Background RMS (mJy)

    flux_percentile = models.FloatField(default=0)  # Pixel flux at 95th percentile

    class Meta:
        ordering = ['time']

    def __str__(self):
        return self.name


class Source(models.Model):
    """
    A Source is an object in the sky that has been detected at least once.
    The Source table starts empty and is built up as images are processed.
    """
    image = models.ForeignKey(Image, null=True, on_delete=models.CASCADE)  # first image seen in
    cross_match_sources = models.ManyToManyField(SurveySource, through='CrossMatch')
    catalog = models.ManyToManyField(
        Catalog,
        through='Association',
        through_fields=('source', 'catalog')
    )

    name = models.CharField(max_length=32, unique=True)
    time = models.DateTimeField()  # date/time of observation, aka epoch

    ra = models.FloatField()  # degrees
    err_ra = models.FloatField()
    dec = models.FloatField()  # degrees
    err_dec = models.FloatField()

    bmaj = models.FloatField()  # Major axis (degrees)
    err_bmaj = models.FloatField()  # Major axis (degrees)
    bmin = models.FloatField()  # Minor axis (degrees)
    err_bmin = models.FloatField()  # Minor axis (degrees)
    pa = models.FloatField()  # Position angle (degrees)
    err_pa = models.FloatField()  # Position angle (degrees)

    total_flux = models.FloatField()  # mJy/beam
    err_total_flux = models.FloatField()  # mJy/beam
    peak_flux = models.FloatField()  # mJy/beam
    err_peak_flux = models.FloatField()  # mJy/beam

    monitor = models.BooleanField(default=False)  # Are we monitoring this location?
    persistent = models.BooleanField(default=False)  # Keep this source between pipeline runs
    quality = models.NullBooleanField(default=False)  # Is this a "quality" source for analysis purposes?

    class Meta:
        ordering = ['ra']

    def __str__(self):
        return self.name


class CrossMatch(models.Model):
    """
    An association between a pipeline source and a survey catalogue source.
    Each pipeline source may be associated with many sources from each survey catalogue
    as multiple survey sources may fit inside the beam of the pipeline telescope esp. MWA.
    The source and survey source rows are referenced by name instead of ID so these
    records can be retained between pipeline reprocessing runs that produce different IDs.
    """
    # Foreign keys have on_delete as 'CASCADE' so that we can directly delete things from
    # the source/survey_source tables without having to think about this crossmatch table
    source = models.ForeignKey(
        Source, to_field='name', on_delete=models.CASCADE
    )
    survey_source = models.ForeignKey(
        SurveySource, to_field='name', on_delete=models.CASCADE
    )

    manual = models.BooleanField()  # a manual cross-match (vs automatic)
    distance = models.FloatField()  # distance between source and survey source (degrees)
    probability = models.FloatField()  # probability of association
    comment = models.CharField(max_length=100)


class Association(models.Model):
    """
    model association between sources and catalogs based on some parameters
    """
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE)

    probability = models.FloatField(default=1.)  # probability of association
    comment = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'assoc prob: {self.probability:.2%}'
