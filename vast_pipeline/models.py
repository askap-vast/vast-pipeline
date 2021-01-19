import logging
import math
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.templatetags.static import static
from social_django.models import UserSocialAuth
from tagulous.models import TagField


class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now_add=True)
    comment = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def get_avatar_url(self) -> str:
        """Get the URL for the user's avatar from GitHub. If the user has no associated
        GitHub account (e.g. a Django superuser), return the URL to the default user
        avatar.

        Returns
        -------
        str
            The avatar URL.
        """
        social = UserSocialAuth.get_social_auth_for_user(self.author).first()
        if social and "avatar_url" in social.extra_data:
            return social.extra_data["avatar_url"]
        else:
            return static("img/user-32.png")


class CommentableModel(models.Model):
    comment = GenericRelation(
        Comment,
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="%(class)s",
    )

    class Meta:
        abstract = True


class Survey(models.Model):
    """An external survey eg NVSS, SUMSS"""
    name = models.CharField(
        max_length=32,
        unique=True,
        help_text='Name of the Survey e.g. NVSS.'
    )
    comment = models.TextField(max_length=1000, default='', blank=True)
    frequency = models.IntegerField(
        help_text='Frequency of the survey.'
    )

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
        help_text='Name of the survey source.'
    )

    ra = models.FloatField(
        help_text='RA of the survey source (Deg).'
    )# degrees
    ra_err = models.FloatField(
        help_text='RA error of the survey source (Deg).'
        )# degrees
    dec = models.FloatField(
        help_text='DEC of the survey source (Deg).'
    )# degrees
    dec_err = models.FloatField(
        help_text='DEC error of the survey source (Deg).'
    )# degrees

    bmaj = models.FloatField(
        help_text=(
            'The major axis of the Gaussian fit to the survey source '
            '(arcsecs).'
        )
    )
    bmin = models.FloatField(
        help_text=(
            'The minor axis of the Gaussian fit to the survey source '
            '(arcsecs).'
        )
    )
    pa = models.FloatField(
        help_text=(
            'Position angle of Gaussian fit east of north to bmaj '
            '(Deg).'
        )
    )

    flux_peak = models.FloatField(
        help_text='Peak flux of the Guassian fit (Jy).'
    )# Jy/beam
    flux_peak_err = models.FloatField(
        help_text='Peak flux error of the Gaussian fit (Jy).'
    )# Jy/beam
    flux_int = models.FloatField(
        help_text='Integrated flux of the Guassian fit (Jy).'
    )# total flux Jy
    flux_int_err = models.FloatField(
        help_text='Integrated flux of the Guassian fit (Jy).'
    )# Jy

    alpha = models.FloatField(default=0,
        help_text='Spectral index of the survey source.'
    )
    image_name = models.CharField(max_length=100,
        blank=True,
        help_text='Name of survey image where measurement was made.'
    )

    objects = SurveySourceQuerySet.as_manager()

    def __str__(self):
        return f"{self.id} {self.name}"


class RunQuerySet(models.QuerySet):

    def check_max_runs(self, max_runs=5):
        """
        Check if number of running pipeline runs is above threshold
        """
        return self.filter(status='RUN').count() >= max_runs


class Run(CommentableModel):
    """
    A Run is essentially a pipeline run/processing istance over a set of
    images
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'[\[@!#$%^&*()<>?/\|}{~:\] ]',
                message='Name contains not allowed characters!',
                inverse_match=True
            ),
        ],
        help_text='name of the pipeline run'
    )
    description = models.CharField(
        max_length=240,
        blank=True,
        help_text="A short description of the pipeline run."
    )
    time = models.DateTimeField(
        auto_now=True,
        help_text='Datetime of a pipeline run.'
    )
    path = models.FilePathField(
        max_length=200,
        help_text='path to the pipeline run'
    )
    STATUS_CHOICES = [
        ('INI', 'Initialised'),
        ('QUE', 'Queued'),
        ('RUN', 'Running'),
        ('END', 'Completed'),
        ('ERR', 'Error'),
        ('RES', 'Restoring'),
    ]
    status = models.CharField(
        max_length=3,
        choices=STATUS_CHOICES,
        default='INI',
        help_text='Status of the pipeline run.'
    )
    n_images = models.IntegerField(
        default=0,
        help_text='number of images processed in this run'
    )
    n_sources = models.IntegerField(
        default=0,
        help_text='number of sources extracted in this run'
    )
    n_selavy_measurements = models.IntegerField(
        default=0,
        help_text='number of selavy measurements in this run'
    )
    n_forced_measurements = models.IntegerField(
        default=0,
        help_text='number of forced measurements in this run'
    )
    epoch_based = models.BooleanField(
        default=False,
        help_text=(
            'Whether the run was processed using epoch based association'
            ', i.e. the user passed in groups of images defining epochs'
            ' rather than every image being treated individually.'
        )
    )

    objects = RunQuerySet.as_manager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # enforce the full model validation on save
        self.full_clean()
        super(Run, self).save(*args, **kwargs)


class Band(models.Model):
    """
    A band on the frequency spectrum used for imaging. Each image is
    associated with one band.
    """
    name = models.CharField(max_length=12, unique=True)
    frequency = models.FloatField(
        help_text='central frequency of band (integer MHz)'
    )
    bandwidth = models.FloatField(
        help_text='bandwidth (MHz)'
    )

    class Meta:
        ordering = ['frequency']

    def __str__(self):
        return self.name


class SkyRegion(models.Model):
    run = models.ManyToManyField(Run)

    centre_ra = models.FloatField()
    centre_dec = models.FloatField()
    width_ra = models.FloatField()
    width_dec = models.FloatField()
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


class Source(CommentableModel):
    run = models.ForeignKey(Run, on_delete=models.CASCADE, null=True,)
    cross_match_sources = models.ManyToManyField(
        SurveySource,
        through='CrossMatch',
        through_fields=('source', 'survey_source')
    )
    related = models.ManyToManyField(
        'self',
        through='RelatedSource',
        symmetrical=False,
        through_fields=('from_source', 'to_source')
    )

    name = models.CharField(max_length=100)
    new = models.BooleanField(default=False, help_text='New Source.')
    tags = TagField(
        space_delimiter=False,
        autocomplete_view="vast_pipeline:source_tags_autocomplete",
        autocomplete_settings={"width": "100%"},
    )

    # average fields calculated from the source measurements
    wavg_ra = models.FloatField(
        help_text='The weighted average right ascension (Deg).'
    )
    wavg_dec = models.FloatField(
        help_text='The weighted average declination (Deg).'
    )
    wavg_uncertainty_ew = models.FloatField(
        help_text=(
            'The weighted average uncertainty in the east-'
            'west (RA) direction (Deg).'
        )
    )
    wavg_uncertainty_ns = models.FloatField(
        help_text=(
            'The weighted average uncertainty in the north-'
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
    min_flux_peak = models.FloatField(
        help_text='The minimum peak flux value.'
    )
    max_flux_int = models.FloatField(
        help_text='The maximum integrated flux value.'
    )
    min_flux_int = models.FloatField(
        help_text='The minimum integrated flux value.'
    )
    min_flux_int_isl_ratio = models.FloatField(
        help_text='The minimum integrated island flux ratio value.'
    )
    min_flux_peak_isl_ratio = models.FloatField(
        help_text='The minimum peak island flux ratio value.'
    )
    avg_compactness = models.FloatField(
        help_text='The average compactness.'
    )
    min_snr = models.FloatField(
        help_text='The minimum signal-to-noise ratio value of the detections.'
    )
    max_snr = models.FloatField(
        help_text='The maximum signal-to-noise ratio value of the detections.'
    )

    # metrics
    v_int = models.FloatField(
        help_text='V metric for int flux.'
    )
    v_peak = models.FloatField(
        help_text='V metric for peak flux.'
    )
    eta_int = models.FloatField(
        help_text='Eta metric for int flux.'
    )
    eta_peak = models.FloatField(
        help_text='Eta metric for peak flux.'
    )
    new_high_sigma = models.FloatField(
        help_text=(
            'The largest sigma value for the new source'
            ' if it was placed in previous image.'
        )
    )
    n_neighbour_dist = models.FloatField(
        help_text='Distance to the nearest neighbour (deg)'
    )
    vs_abs_significant_max_int = models.FloatField(
        default=0.0,
        help_text=(
            'Maximum value of all measurement pair variability t-statistics for int '
            'flux that exceed SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS in the pipeline run '
            'configuration.'
        )
    )
    m_abs_significant_max_int = models.FloatField(
        default=0.0,
        help_text=(
            'Maximum absolute value of all measurement pair modulation indices for int '
            'flux that exceed SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS in the pipeline run '
            'configuration.'
        )
    )
    vs_abs_significant_max_peak = models.FloatField(
        default=0.0,
        help_text=(
            'Maximum absolute value of all measurement pair variability t-statistics for '
            'peak flux that exceed SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS in the pipeline '
            'run configuration.'
        )
    )
    m_abs_significant_max_peak = models.FloatField(
        default=0.0,
        help_text=(
            'Maximum absolute value of all measurement pair modulation indices for '
            'peak flux that exceed SOURCE_AGGREGATE_PAIR_METRICS_MIN_ABS_VS in the '
            'pipeline run configuration.'
        )
    )


    # total metrics to report in UI
    n_meas = models.IntegerField(
        help_text='total measurements of the source'
    )
    n_meas_sel = models.IntegerField(
        help_text='total selavy extracted measurements of the source'
    )
    n_meas_forced = models.IntegerField(
        help_text='total force extracted measurements of the source'
    )
    n_rel = models.IntegerField(
        help_text='total relations of the source with other sources'
    )
    n_sibl = models.IntegerField(
        help_text='total siblings of the source'
    )

    objects = SourceQuerySet.as_manager()

    def __str__(self):
        return self.name


class RelatedSource(models.Model):
    '''
    Association table for the many to many Source relationship with itself
    Django doc https://docs.djangoproject.com/en/3.1/ref/models/fields/#django.db.models.ManyToManyField.through
    '''
    from_source = models.ForeignKey(Source, on_delete=models.CASCADE)
    to_source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name='related_sources'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='%(app_label)s_%(class)s_unique_pair',
                fields=['from_source', 'to_source']
            )
        ]


class Image(CommentableModel):
    """An image is a 2D radio image from a cube"""
    band = models.ForeignKey(Band, on_delete=models.CASCADE)
    run = models.ManyToManyField(Run)
    skyreg = models.ForeignKey(SkyRegion, on_delete=models.CASCADE)

    measurements_path = models.FilePathField(
        max_length=200,
        db_column='meas_path',
        help_text=(
            'the path to the measurements parquet that belongs to this image'
        )
    )
    POLARISATION_CHOICES = [
        ('I', 'I'),
        ('XX', 'XX'),
        ('YY', 'YY'),
        ('Q', 'Q'),
        ('U', 'U'),
        ('V', 'V'),
    ]
    polarisation = models.CharField(
        max_length=2,
        choices=POLARISATION_CHOICES,
        help_text='Polarisation of the image one of I,XX,YY,Q,U,V.'
    )
    name = models.CharField(
        unique=True,
        max_length=200,
        help_text='Name of the image.'
    )
    path = models.FilePathField(
        max_length=500,
        help_text='Path to the file containing the image.'
    )
    noise_path = models.FilePathField(
        max_length=300,
        blank=True,
        default='',
        help_text='Path to the file containing the RMS image.'
    )
    background_path = models.FilePathField(
        max_length=300,
        blank=True,
        default='',
        help_text='Path to the file containing the background image.'
    )

    datetime = models.DateTimeField(
        help_text='Date/time of observation or epoch.'
    )
    jd = models.FloatField(
        help_text='Julian date of the observation (days).'
    )
    duration =  models.FloatField(
        default=0.,
        help_text='Duration of the observation.'
    )

    ra = models.FloatField(
        help_text='RA of the image centre (Deg).'
    )
    dec = models.FloatField(
        help_text='DEC of the image centre (Deg).'
    )
    fov_bmaj = models.FloatField(
        help_text='Field of view major axis (Deg).'
    )# Major (Dec) radius of image (degrees)
    fov_bmin = models.FloatField(
        help_text='Field of view minor axis (Deg).'
    )# Minor (RA) radius of image (degrees)
    physical_bmaj = models.FloatField(
        help_text='The actual size of the image major axis (Deg).'
    )# Major (Dec) radius of image (degrees)
    physical_bmin = models.FloatField(
        help_text='The actual size of the image minor axis (Deg).'
    )# Minor (RA) radius of image (degrees)
    radius_pixels = models.FloatField(
        help_text='Radius of the useable region of the image (pixels).'
    )

    beam_bmaj = models.FloatField(
        help_text='Major axis of image restoring beam (Deg).'
    )
    beam_bmin = models.FloatField(
        help_text='Minor axis of image restoring beam (Deg).'
    )
    beam_bpa = models.FloatField(
        help_text='Beam position angle (Deg).'
    )
    rms_median = models.FloatField(
        help_text='Background average RMS from the provided RMS map (mJy).'
    )
    rms_min = models.FloatField(
        help_text='Background minimum RMS from the provided RMS map (mJy).'
    )
    rms_max = models.FloatField(
        help_text='Background maximum RMS from the provided RMS map (mJy).'
    )

    class Meta:
        ordering = ['datetime']

    def __str__(self):
        return self.name


class MeasurementQuerySet(models.QuerySet):

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


class Measurement(CommentableModel):
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

    ra = models.FloatField(help_text='RA of the source (Deg).')# degrees
    ra_err = models.FloatField(
        help_text='RA error of the source (Deg).'
    )
    dec = models.FloatField(help_text='DEC of the source (Deg).')# degrees
    dec_err = models.FloatField(
        help_text='DEC error of the source (Deg).'
    )

    bmaj = models.FloatField(
        help_text=(
            'The major axis of the Gaussian fit to the source (Deg).'
        )
    )
    err_bmaj = models.FloatField(help_text='Error major axis (Deg).')
    bmin = models.FloatField(
        help_text=(
            'The minor axis of the Gaussian fit to the source (Deg).'
        )
    )
    err_bmin = models.FloatField(help_text='Error minor axis (Deg).')
    pa = models.FloatField(
        help_text=(
            'Position angle of Gaussian fit east of north to bmaj '
            '(Deg).'
        )
    )
    err_pa = models.FloatField(help_text='Error position angle (Deg).')

    # supplied by user via config
    ew_sys_err = models.FloatField(
        help_text='Systematic error in east-west (RA) direction (Deg).'
    )
    # supplied by user via config
    ns_sys_err = models.FloatField(
        help_text='Systematic error in north-south (dec) direction (Deg).'
    )

    # estimate of maximum error radius (from ra_err and dec_err)
    # Used in advanced association.
    error_radius = models.FloatField(
        help_text=(
            'Estimate of maximum error radius using ra_err'
            ' and dec_err (Deg).'
        )
    )

    # quadratic sum of error_radius and ew_sys_err
    uncertainty_ew = models.FloatField(
        help_text=(
            'Total east-west (RA) uncertainty, quadratic sum of'
            ' error_radius and ew_sys_err (Deg).'
        )
    )
     # quadratic sum of error_radius and ns_sys_err
    uncertainty_ns = models.FloatField(
        help_text=(
            'Total north-south (Dec) uncertainty, quadratic sum of '
            'error_radius and ns_sys_err (Deg).'
        )
    )

    flux_int = models.FloatField()# mJy/beam
    flux_int_err = models.FloatField()# mJy/beam
    flux_int_isl_ratio = models.FloatField(
        help_text=(
            'Ratio of the component integrated flux to the total'
            ' island integrated flux.'
        )
    )
    flux_peak = models.FloatField()# mJy/beam
    flux_peak_err = models.FloatField()# mJy/beam
    flux_peak_isl_ratio = models.FloatField(
        help_text=(
            'Ratio of the component peak flux to the total'
            ' island peak flux.'
        )
    )
    chi_squared_fit = models.FloatField(
        db_column='chi2_fit',
        help_text='Chi-squared of the Guassian fit to the source.'
    )
    spectral_index = models.FloatField(
        db_column='spectr_idx',
        help_text='In-band Selavy spectral index.'
    )
    spectral_index_from_TT = models.BooleanField(
        default=False,
        db_column='spectr_idx_tt',
        help_text=(
            'True/False if the spectral index came from the taylor '
            'term.'
        )
    )

    local_rms = models.FloatField(
        help_text='Local rms in mJy from Selavy.'
    )# mJy/beam

    snr = models.FloatField(
        help_text='Signal-to-noise ratio of the measurement.'
    )

    flag_c4 = models.BooleanField(
        default=False,
        help_text='Fit flag from Selavy.'
    )

    compactness = models.FloatField(
        help_text='Int flux over peak flux.'
    )

    has_siblings = models.BooleanField(
        default=False,
        help_text='True if the fit comes from an island that has more than 1 component.'
    )
    component_id = models.CharField(
        max_length=64,
        help_text=(
            'The ID of the component from which the source comes from.'
        )
    )
    island_id = models.CharField(
        max_length=64,
        help_text=(
            'The ID of the island from which the source comes from.'
        )
    )

    forced = models.BooleanField(
        default=False,
        help_text='True: the measurement is forced extracted.'
    )

    objects = MeasurementQuerySet.as_manager()

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
    model association between sources and measurements based on
    some parameters
    """
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    meas = models.ForeignKey(Measurement, on_delete=models.CASCADE)

    d2d = models.FloatField(
        default=0.,
        help_text='astronomical distance calculated by Astropy, arcsec.'
    )
    dr = models.FloatField(
        default=0.,
        help_text='De Ruiter radius calculated in advanced association.'
    )

    def __str__(self):
        return (
            f'distance: {self.d2d:.2f}' if self.dr == 0 else
            f'distance: {self.dr:.2f}'
        )


class SourceFav(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    comment = models.TextField(
        max_length=500,
        default='',
        blank=True,
        help_text='Why did you include this as favourite'
    )


class MeasurementPair(models.Model):
    """Links two Measurement objects from the same Source and stores two variability metrics
    for peak and integrated fluxes:
        - `vs_peak` and `vs_int` is the variability t-statistic. e.g. if Vs is 4.3, then
            the source is considered variable to a 95% CI.
        - `m_peak` and `m_int` is the modulation index, related to fractional variability.
    See Section 5 of Mooley et al. (2016) for details, DOI: 10.3847/0004-637X/818/2/105.
    """
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    measurement_a = models.ForeignKey(
        Measurement, related_name="measurement_pairs_a", on_delete=models.CASCADE
    )
    measurement_b = models.ForeignKey(
        Measurement, related_name="measurement_pairs_b", on_delete=models.CASCADE
    )
    vs_peak = models.FloatField(help_text="Variability metric: t-statistic for peak fluxes.")
    m_peak = models.FloatField(help_text="Variability metric: modulation index for peak fluxes.")
    vs_int = models.FloatField(help_text="Variability metric: t-statistic for integrated fluxes.")
    m_int = models.FloatField(help_text="Variability metric: modulation index for integrated fluxes.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "measurement_a", "measurement_b"],
                name="%(app_label)s_%(class)s_unique_pair"
            )
        ]

    def __str__(self):
        return f"({self.measurement_a}, {self.measurement_b})"
