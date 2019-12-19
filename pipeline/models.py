import math
from django.db import models
from django.core.validators import RegexValidator


# Create your models here.
class Survey(models.Model):
    """An external survey eg NVSS, SUMSS"""
    name = models.CharField(max_length=32, unique=True, help_text='Name of the Survey e.g. NVSS')
    comment = models.TextField(max_length=1000, blank=True)
    frequency = models.IntegerField(help_text='Frequency of the survey')

class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SurveySource(models.Model):
    """A source from a survey catalogue eg NVSS, SUMSS"""
    # An index on the survey_id field causes queries to perform much worse
    # because there are so few unique surveys, it's a poor field to index.
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)

    name = models.CharField(max_length=100, unique=True, help_text='Name of the survey source')

    ra = models.FloatField(help_text='RA of the survey source (Deg)')  # degrees
    ra_err = models.FloatField('RA error of the survey source (Deg)')  # degrees
    dec = models.FloatField('DEC of the survey source (Deg)')  # degrees
    dec_err = models.FloatField('DEC error of the survey source (Deg)')  # degrees

    bmaj = models.FloatField(help_text='The major axis of the Gaussian fit to the survey source (arcsecs)')  # major axis (arcsecs)
    bmin = models.FloatField(help_text='The minor axis of the Gaussian fit to the survey source (arcsecs)')  # minor axis (arcsecs)
    pa = models.FloatField(help_text='Position angle of Gaussian fit east of north to bmaj (Deg)')  # position angle (degrees east of north)

    flux_peak = models.FloatField(help_text='Peak flux of the Guassian fit (Jy)')  # Jy/beam
    flux_peak_err = models.FloatField(help_text='Peak flux error of the Gaussian fit (Jy)')  # Jy/beam
    flux_int = models.FloatField(help_text='Integrated flux of the Guassian fit (Jy)')  # total flux Jy
    flux_int_err = models.FloatField(help_text='Integrated flux of the Guassian fit (Jy)')  # Jy

    alpha = models.FloatField(default=0, help_text='Spectral index of the survey source')  # Spectral index of source
    image_name = models.CharField(max_length=100, blank=True, help_text='Name of survey image where measurement was made')  # image file
 

    def __str__(self):
        return f"{self.id} {self.name}"

    @classmethod
    def cone_search(cls, ra, dec, radius_deg):
        """
        Return all the SurveySources withing radius_deg of (ra,dec).
        Returns a QuerySet of SurveySources, ordered by distance from (ra,dec) ascending
        """
        qs = (
            SurveySource.objects
            .extra(
                select={"distance": "q3c_dist(ra, dec, %s, %s) * 3600"},
                select_params=[ra, dec],
                where=["q3c_radial_query(ra, dec, %s, %s, %s)"],
                params=[ra, dec, radius_deg],
            )
            .order_by("distance")
        )
        return qs


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


class Image(models.Model):
    """An image is a 2D radio image from a cube"""
    band = models.ForeignKey(Band, on_delete=models.CASCADE)
    dataset = models.ForeignKey(
        Dataset, on_delete=models.SET_NULL, blank=True, null=True
    )

    polarisation = models.CharField(max_length=2, help_text='Polarisation of the image e.g. I,XX,YY,Q,U,V')  # eg XX,YY,I,Q,U,V
    name = models.CharField(max_length=200, help_text='Name of the image')
    path = models.CharField(max_length=500, help_text='Path to the file containing the image')  # the path to the file containing this image
    noise_path = models.CharField(max_length=300, blank=True, default='', help_text='Path to the file containing the RMS image')  # includes filename
    background_path = models.CharField(max_length=300, blank=True, default='', help_text='Path to the file containing the background image')  # includes filename
    valid = models.BooleanField(default=True, help_text='Is the image valid')  # Is the image valid?

    time = models.DateTimeField(help_text='Date of observation')  # date/time of observation, aka epoch
    jd = models.FloatField(help_text='Julian date of the observation (days)')  # date/time of observation in Julian Date format
    duration =  models.FloatField(help_text='Duration of the observation') # Duration of the observation 

    flux_gain = models.FloatField(default=1, help_text='Gain of the image, multiplicative factor to change the relative flux scale')  # flux gain factor
    flux_gain_err = models.FloatField(default=0, help_text='Error on the image gain')  # std in flux gain factor

    ra = models.FloatField(help_text='RA of the image centre (Deg)')  # RA of image centre (degrees)
    dec = models.FloatField(help_text='DEC of the image centre (Deg)')  # Dec of image centre (degrees)
    fov_bmaj = models.FloatField(help_text='Field of view major axis (Deg)')  # Major (Dec) radius of image (degrees)
    fov_bmin = models.FloatField(help_text='Field of view minor axis ')  # Minor (RA) radius of image (degrees)
    radius_pixels = models.FloatField(help_text='Radius of the useable region of the image (pixels)')  # Radius of the useable region of the image (pixels)

    beam_bmaj = models.FloatField(help_text='Major axis of image restoring beam (Deg)')  # Beam major axis (degrees)
    beam_bmin = models.FloatField(help_text='Minor axis of image restoring beam (Deg)')  # Beam minor axis (degrees)
    beam_bpa = models.FloatField()  # Beam position angle (degrees)
    rms = models.FloatField(default=0, help_text='Background RMS based on sigma clipping of image data (mJy)')  # Background RMS (mJy)

    flux_percentile = models.FloatField(default=0)  # Pixel flux at 95th percentile

    # source_find_time = models.FloatField(null=True)  # blind source finding time (seconds)
    # validation_time = models.FloatField(null=True)  # detection validation time (seconds)
    # assoc_time = models.FloatField(null=True)  # source association time (seconds)
    
    # source_stats_time = models.FloatField(null=True)  # source stats recalculation time (seconds)
    # monitor_time = models.FloatField(null=True)  # non-detection monitoring time (seconds)
    # total_time = models.FloatField(null=True)  # total processing time (seconds)

    class Meta:
        ordering = ['time']

    def __str__(self):
        return "image:{0}".format(self.id)

    @classmethod
    def images_containing_position(cls, ra, dec):
        """Return all the images that contain the given ra/dec"""
        query = Image.objects.extra(
            where=["q3c_ellipse_query(ra, dec, %s, %s, fov_bmaj," +
            "(fov_bmin/fov_bmaj), 0)"],
            params=[ra, dec]
        )
        return query

    def overlapping_images(self):
        """Return a QuerySet for the images whose FoV overlaps this one"""
        return Image.objects.exclude(id=self.id).extra(
            where=["q3c_radial_query(ra, dec, %s, %s, " +
            "GREATEST(fov_bmaj,fov_bmin) + %s)"],
            params=[self.ra, self.dec, max(self.fov_bmaj, self.fov_bmin)]
        )

    def get_beam_area(self):
        """Returns the image beam area (square degrees)"""
        return self.beam_bmaj * self.beam_bmin * math.pi

    def blind_detection_count(self):
        """The number of blind detections in this image"""
        return self.flux_set.filter(blind_detection=True).count()

    def good_fit_count(self):
        return self.flux_set.filter(good_fit=True).count()

    @classmethod
    def get_extnames(cls):
        """Returns a list of the distinct extname values in the entire table"""
        return (
            Image.objects.values_list('extname', flat=True)
            .order_by('-extname').distinct()
        )

    @classmethod
    def get_polarisations(cls):
        """Return a list of distinct polarisations (strings)"""
        return (
            Image.objects.values_list('polarisation', flat=True)
            .order_by('polarisation').distinct()
        )


class Source(models.Model):
    """
    A Source is an object in the sky that has been detected at least once.
    The Source table starts empty and is built up as images are processed.
    """
    image = models.ForeignKey(Image, null=True, on_delete=models.CASCADE)  # first image seen in
    cross_match_sources = models.ManyToManyField(SurveySource, through='CrossMatch')

    name = models.CharField(max_length=32, unique=True)

    ra = models.FloatField(help_text='RA of the source (Deg)')  # degrees
    ra_err = models.FloatField(help_text='RA error of the source (Deg)')
    dec = models.FloatField(help_text='DEC of the source (Deg)')  # degrees
    dec_err = models.FloatField(help_text='DEC error of the source (Deg)')

    bmaj = models.FloatField(help_text='The major axis of the Gaussian fit to the source (Deg)')  # Major axis (degrees)
    err_bmaj = models.FloatField()  # Error major axis (degrees)
    bmin = models.FloatField(help_text='The minor axis of the Gaussian fit to the source (Deg)')  # Minor axis (degrees)
    err_bmin = models.FloatField()  # Error minor axis (degrees)
    pa = models.FloatField(help_text='Position angle of Gaussian fit east of north to bmaj (Deg)')  # Position angle (degrees)
    err_pa = models.FloatField()  # Error position angle (degrees)

    flux_int = models.FloatField()  # Jy/beam
    flux_int_err = models.FloatField()  # Jy/beam
    flux_peak = models.FloatField()  # Jy/beam
    flux_peak_err = models.FloatField()  # Jy/beam
    chi_squared_fit = models.FloatField(help_text='Chi-squared of the Guassian fit to the source') # chi-squared of Gaussian fit
    spectral_index = models.FloatField(help_text='In-band Selavy spectral index') # In band spectral index from Selavy
    spectral_index_from_TT = models.BooleanField(default=False, help_text='True/False if the spectral index came from the taylor term came') # Did the spectral index come from the taylor term
    flag_c4 = models.BooleanField(default=False, help_text='Fit flag from selavy') # Fit flag from selavy file

    has_siblings = models.BooleanField(default=False, help_text='Does the fit come from an island') # Does the fit come from an island? 
    component_id = models.IntegerField(help_text='The ID of the component from which the source comes from') # The ID of the component from which the source comes from 
    island_id    = models.IntegerField(help_text='The ID of the island from which the source comes from ') # The ID of the island from which the source comes from 

    monitor = models.BooleanField(default=False, help_text='Are we monitoring this location')  # Are we monitoring this location?
    persistent = models.BooleanField(default=False)  # Keep this source between pipeline runs
    quality = models.NullBooleanField(default=False, help_text='Is this a quality source for analysis purposes')  # Is this a "quality" source for analysis purposes?

    class Meta:
        ordering = ['ra']

    def __str__(self):
        return self.name

    # @classmethod
    # def cone_search(cls, ra, dec, radius_deg):
    #     """
    #     Return all the sources withing radius_deg of (ra,dec).
    #     Returns a QuerySet of Sources with "dist" field added, ordered by dist ascending
    #     """
    #     # Use Django's QuerySet.extra() feature to specify q3c functions in SQL.
    #     # I tried putting the q3c_dist() in the order_by clause but Django seems to have a bug
    #     # and it created invalid SQL. But putting it in the select works.
    #     return Source.objects.extra(
    #         select={"dist": f"q3c_dist(ra, dec, {ra}, {dec})"},
    #         where=["q3c_radial_query(ra, dec, %s, %s, %s)"],
    #         params=[ra, dec, radius_deg],
    #         order_by=["dist"]
    #     )

    # @classmethod
    # def nondetected_sources(cls, image):
    #     """
    #     Return all the sources that are within the image's field of view and have no
    #     flux measurement for the given image id. Ie all the sources that were not found in the given image.
    #     """
    #     return (
    #         Source.objects.extra(
    #             where=["q3c_ellipse_query(ra, dec, %s, %s, %s, %s, 0) " +
    #                 "AND id NOT IN (SELECT s.id FROM vast_source s, vast_flux" +
    #                 "WHERE s.id=source_id AND image_id=%s) "],
    #             params=[image.ra, image.dec, image.fov_bmaj,
    #                 (image.fov_bmin / image.fov_bmaj), image.id]
    #         )
    #     )


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
