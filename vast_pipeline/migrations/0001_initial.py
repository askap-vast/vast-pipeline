# Generated by Django 3.0.7 on 2020-11-02 18:41

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import tagulous.models.fields
import tagulous.models.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Association',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('d2d', models.FloatField(default=0.0, help_text='astronomical distance calculated by Astropy, arcsec.')),
                ('dr', models.FloatField(default=0.0, help_text='De Ruiter radius calculated in advanced association.')),
            ],
        ),
        migrations.CreateModel(
            name='Band',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=12, unique=True)),
                ('frequency', models.FloatField(help_text='central frequency of band (integer MHz)')),
                ('bandwidth', models.FloatField(help_text='bandwidth (MHz)')),
            ],
            options={
                'ordering': ['frequency'],
            },
        ),
        migrations.CreateModel(
            name='CrossMatch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('manual', models.BooleanField()),
                ('distance', models.FloatField()),
                ('probability', models.FloatField()),
                ('comment', models.TextField(blank=True, default='', max_length=1000)),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('measurements_path', models.FilePathField(db_column='meas_path', help_text='the path to the measurements parquet that belongs to this image', max_length=200)),
                ('polarisation', models.CharField(choices=[('I', 'I'), ('XX', 'XX'), ('YY', 'YY'), ('Q', 'Q'), ('U', 'U'), ('V', 'V')], help_text='Polarisation of the image one of I,XX,YY,Q,U,V.', max_length=2)),
                ('name', models.CharField(help_text='Name of the image.', max_length=200, unique=True)),
                ('path', models.FilePathField(help_text='Path to the file containing the image.', max_length=500)),
                ('noise_path', models.FilePathField(blank=True, default='', help_text='Path to the file containing the RMS image.', max_length=300)),
                ('background_path', models.FilePathField(blank=True, default='', help_text='Path to the file containing the background image.', max_length=300)),
                ('datetime', models.DateTimeField(help_text='Date/time of observation or epoch.')),
                ('jd', models.FloatField(help_text='Julian date of the observation (days).')),
                ('duration', models.FloatField(default=0.0, help_text='Duration of the observation.')),
                ('ra', models.FloatField(help_text='RA of the image centre (Deg).')),
                ('dec', models.FloatField(help_text='DEC of the image centre (Deg).')),
                ('fov_bmaj', models.FloatField(help_text='Field of view major axis (Deg).')),
                ('fov_bmin', models.FloatField(help_text='Field of view minor axis (Deg).')),
                ('physical_bmaj', models.FloatField(help_text='The actual size of the image major axis (Deg).')),
                ('physical_bmin', models.FloatField(help_text='The actual size of the image minor axis (Deg).')),
                ('radius_pixels', models.FloatField(help_text='Radius of the useable region of the image (pixels).')),
                ('beam_bmaj', models.FloatField(help_text='Major axis of image restoring beam (Deg).')),
                ('beam_bmin', models.FloatField(help_text='Minor axis of image restoring beam (Deg).')),
                ('beam_bpa', models.FloatField(help_text='Beam position angle (Deg).')),
                ('rms_median', models.FloatField(help_text='Background average RMS from the provided RMS map (mJy).')),
                ('rms_min', models.FloatField(help_text='Background minimum RMS from the provided RMS map (mJy).')),
                ('rms_max', models.FloatField(help_text='Background maximum RMS from the provided RMS map (mJy).')),
                ('band', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Band')),
            ],
            options={
                'ordering': ['datetime'],
            },
        ),
        migrations.CreateModel(
            name='Measurement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('ra', models.FloatField(help_text='RA of the source (Deg).')),
                ('ra_err', models.FloatField(help_text='RA error of the source (Deg).')),
                ('dec', models.FloatField(help_text='DEC of the source (Deg).')),
                ('dec_err', models.FloatField(help_text='DEC error of the source (Deg).')),
                ('bmaj', models.FloatField(help_text='The major axis of the Gaussian fit to the source (Deg).')),
                ('err_bmaj', models.FloatField(help_text='Error major axis (Deg).')),
                ('bmin', models.FloatField(help_text='The minor axis of the Gaussian fit to the source (Deg).')),
                ('err_bmin', models.FloatField(help_text='Error minor axis (Deg).')),
                ('pa', models.FloatField(help_text='Position angle of Gaussian fit east of north to bmaj (Deg).')),
                ('err_pa', models.FloatField(help_text='Error position angle (Deg).')),
                ('ew_sys_err', models.FloatField(help_text='Systematic error in east-west (RA) direction (Deg).')),
                ('ns_sys_err', models.FloatField(help_text='Systematic error in north-south (dec) direction (Deg).')),
                ('error_radius', models.FloatField(help_text='Estimate of maximum error radius using ra_err and dec_err (Deg).')),
                ('uncertainty_ew', models.FloatField(help_text='Total east-west (RA) uncertainty, quadratic sum of error_radius and ew_sys_err (Deg).')),
                ('uncertainty_ns', models.FloatField(help_text='Total north-south (Dec) uncertainty, quadratic sum of error_radius and ns_sys_err (Deg).')),
                ('flux_int', models.FloatField()),
                ('flux_int_err', models.FloatField()),
                ('flux_peak', models.FloatField()),
                ('flux_peak_err', models.FloatField()),
                ('chi_squared_fit', models.FloatField(db_column='chi2_fit', help_text='Chi-squared of the Guassian fit to the source.')),
                ('spectral_index', models.FloatField(db_column='spectr_idx', help_text='In-band Selavy spectral index.')),
                ('spectral_index_from_TT', models.BooleanField(db_column='spectr_idx_tt', default=False, help_text='True/False if the spectral index came from the taylor term.')),
                ('local_rms', models.FloatField(help_text='Local rms in mJy from Selavy.')),
                ('snr', models.FloatField(help_text='Signal-to-noise ratio of the measurement.')),
                ('flag_c4', models.BooleanField(default=False, help_text='Fit flag from Selavy.')),
                ('compactness', models.FloatField(help_text='Int flux over peak flux.')),
                ('has_siblings', models.BooleanField(default=False, help_text='True if the fit comes from an island that has more than 1 component.')),
                ('component_id', models.CharField(help_text='The ID of the component from which the source comes from.', max_length=64)),
                ('island_id', models.CharField(help_text='The ID of the island from which the source comes from.', max_length=64)),
                ('forced', models.BooleanField(default=False, help_text='True: the measurement is forced extracted.')),
                ('image', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Image')),
            ],
            options={
                'ordering': ['ra'],
            },
        ),
        migrations.CreateModel(
            name='RelatedSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='Run',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='name of the pipeline run', max_length=64, unique=True, validators=[django.core.validators.RegexValidator(inverse_match=True, message='Name contains not allowed characters!', regex='[\\[@!#$%^&*()<>?/\\|}{~:\\] ]')])),
                ('description', models.CharField(blank=True, help_text='A short description of the pipeline run.', max_length=240)),
                ('time', models.DateTimeField(auto_now=True, help_text='Datetime of a pipeline run.')),
                ('path', models.FilePathField(help_text='path to the pipeline run', max_length=200)),
                ('status', models.CharField(choices=[('INI', 'Initialised'), ('RUN', 'Running'), ('END', 'Completed'), ('ERR', 'Error')], default='INI', help_text='Status of the pipeline run.', max_length=3)),
                ('n_images', models.IntegerField(default=0, help_text='number of images processed in this run')),
                ('n_sources', models.IntegerField(default=0, help_text='number of sources extracted in this run')),
                ('n_selavy_measurements', models.IntegerField(default=0, help_text='number of selavy measurements in this run')),
                ('n_forced_measurements', models.IntegerField(default=0, help_text='number of forced measurements in this run')),
                ('epoch_based', models.BooleanField(default=False, help_text='Whether the run was processed using epoch based association, i.e. the user passed in groups of images defining epochs rather than every image being treated individually.')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('new', models.BooleanField(default=False, help_text='New Source.')),
                ('wavg_ra', models.FloatField(help_text='The weighted average right ascension (Deg).')),
                ('wavg_dec', models.FloatField(help_text='The weighted average declination (Deg).')),
                ('wavg_uncertainty_ew', models.FloatField(help_text='The weighted average uncertainty in the east-west (RA) direction (Deg).')),
                ('wavg_uncertainty_ns', models.FloatField(help_text='The weighted average uncertainty in the north-south (Dec) direction (Deg).')),
                ('avg_flux_int', models.FloatField(help_text='The average integrated flux value.')),
                ('avg_flux_peak', models.FloatField(help_text='The average peak flux value.')),
                ('max_flux_peak', models.FloatField(help_text='The maximum peak flux value.')),
                ('avg_compactness', models.FloatField(help_text='The average compactness.')),
                ('min_snr', models.FloatField(help_text='The minimum signal-to-noise ratio value of the detections.')),
                ('max_snr', models.FloatField(help_text='The maximum signal-to-noise ratio value of the detections.')),
                ('v_int', models.FloatField(help_text='V metric for int flux.')),
                ('v_peak', models.FloatField(help_text='V metric for peak flux.')),
                ('eta_int', models.FloatField(help_text='Eta metric for int flux.')),
                ('eta_peak', models.FloatField(help_text='Eta metric for peak flux.')),
                ('new_high_sigma', models.FloatField(help_text='The largest sigma value for the new source if it was placed in previous image.')),
                ('n_neighbour_dist', models.FloatField(help_text='Distance to the nearest neighbour (deg)')),
                ('vs_max_int', models.FloatField(help_text='Maximum value of all measurement pair variability t-statistics for int flux.', null=True)),
                ('m_abs_max_int', models.FloatField(help_text='Maximum absolute value of all measurement pair modulation indices for int flux.', null=True)),
                ('vs_max_peak', models.FloatField(help_text='Maximum value of all measurement pair variability t-statistics for peak flux.', null=True)),
                ('m_abs_max_peak', models.FloatField(help_text='Maximum absolute value of all measurement pair modulation indices for peak flux.', null=True)),
                ('n_meas', models.IntegerField(help_text='total measurements of the source')),
                ('n_meas_sel', models.IntegerField(help_text='total selavy extracted measurements of the source')),
                ('n_meas_forced', models.IntegerField(help_text='total force extracted measurements of the source')),
                ('n_rel', models.IntegerField(help_text='total relations of the source with other sources')),
                ('n_sibl', models.IntegerField(help_text='total siblings of the source')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the Survey e.g. NVSS.', max_length=32, unique=True)),
                ('comment', models.TextField(blank=True, default='', max_length=1000)),
                ('frequency', models.IntegerField(help_text='Frequency of the survey.')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Tagulous_Source_tags',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('slug', models.SlugField()),
                ('count', models.IntegerField(default=0, help_text='Internal counter of how many times this tag is in use')),
                ('protected', models.BooleanField(default=False, help_text='Will not be deleted when the count reaches 0')),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
                'unique_together': {('slug',)},
            },
            bases=(tagulous.models.models.BaseTagModel, models.Model),
        ),
        migrations.CreateModel(
            name='SurveySource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the survey source.', max_length=100)),
                ('ra', models.FloatField(help_text='RA of the survey source (Deg).')),
                ('ra_err', models.FloatField(help_text='RA error of the survey source (Deg).')),
                ('dec', models.FloatField(help_text='DEC of the survey source (Deg).')),
                ('dec_err', models.FloatField(help_text='DEC error of the survey source (Deg).')),
                ('bmaj', models.FloatField(help_text='The major axis of the Gaussian fit to the survey source (arcsecs).')),
                ('bmin', models.FloatField(help_text='The minor axis of the Gaussian fit to the survey source (arcsecs).')),
                ('pa', models.FloatField(help_text='Position angle of Gaussian fit east of north to bmaj (Deg).')),
                ('flux_peak', models.FloatField(help_text='Peak flux of the Guassian fit (Jy).')),
                ('flux_peak_err', models.FloatField(help_text='Peak flux error of the Gaussian fit (Jy).')),
                ('flux_int', models.FloatField(help_text='Integrated flux of the Guassian fit (Jy).')),
                ('flux_int_err', models.FloatField(help_text='Integrated flux of the Guassian fit (Jy).')),
                ('alpha', models.FloatField(default=0, help_text='Spectral index of the survey source.')),
                ('image_name', models.CharField(blank=True, help_text='Name of survey image where measurement was made.', max_length=100)),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Survey')),
            ],
        ),
        migrations.CreateModel(
            name='SourceFav',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField(blank=True, default='', help_text='Why did you include this as favourite', max_length=500)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Source')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='source',
            name='cross_match_sources',
            field=models.ManyToManyField(through='vast_pipeline.CrossMatch', to='vast_pipeline.SurveySource'),
        ),
        migrations.AddField(
            model_name='source',
            name='related',
            field=models.ManyToManyField(through='vast_pipeline.RelatedSource', to='vast_pipeline.Source'),
        ),
        migrations.AddField(
            model_name='source',
            name='run',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Run'),
        ),
        migrations.AddField(
            model_name='source',
            name='tags',
            field=tagulous.models.fields.TagField(_set_tag_meta=True, autocomplete_settings={'width': '100%'}, autocomplete_view='vast_pipeline:source_tags_autocomplete', help_text='Enter a comma-separated tag string', space_delimiter=False, to='vast_pipeline.Tagulous_Source_tags'),
        ),
        migrations.CreateModel(
            name='SkyRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('centre_ra', models.FloatField()),
                ('centre_dec', models.FloatField()),
                ('width_ra', models.FloatField()),
                ('width_dec', models.FloatField()),
                ('xtr_radius', models.FloatField()),
                ('x', models.FloatField()),
                ('y', models.FloatField()),
                ('z', models.FloatField()),
                ('run', models.ManyToManyField(to='vast_pipeline.Run')),
            ],
        ),
        migrations.AddField(
            model_name='relatedsource',
            name='from_source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Source'),
        ),
        migrations.AddField(
            model_name='relatedsource',
            name='to_source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='related_sources', to='vast_pipeline.Source'),
        ),
        migrations.CreateModel(
            name='MeasurementPair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vs_peak', models.FloatField(help_text='Variability metric: t-statistic for peak fluxes.')),
                ('m_peak', models.FloatField(help_text='Variability metric: modulation index for peak fluxes.')),
                ('vs_int', models.FloatField(help_text='Variability metric: t-statistic for integrated fluxes.')),
                ('m_int', models.FloatField(help_text='Variability metric: modulation index for integrated fluxes.')),
                ('measurement_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='measurement_pairs_a', to='vast_pipeline.Measurement')),
                ('measurement_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='measurement_pairs_b', to='vast_pipeline.Measurement')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Source')),
            ],
        ),
        migrations.AddField(
            model_name='measurement',
            name='source',
            field=models.ManyToManyField(through='vast_pipeline.Association', to='vast_pipeline.Source'),
        ),
        migrations.AddField(
            model_name='image',
            name='run',
            field=models.ManyToManyField(to='vast_pipeline.Run'),
        ),
        migrations.AddField(
            model_name='image',
            name='skyreg',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.SkyRegion'),
        ),
        migrations.AddField(
            model_name='crossmatch',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Source'),
        ),
        migrations.AddField(
            model_name='crossmatch',
            name='survey_source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.SurveySource'),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(auto_now_add=True)),
                ('comment', models.TextField()),
                ('object_id', models.PositiveIntegerField()),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
        ),
        migrations.AddField(
            model_name='association',
            name='meas',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Measurement'),
        ),
        migrations.AddField(
            model_name='association',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vast_pipeline.Source'),
        ),
        migrations.AddConstraint(
            model_name='relatedsource',
            constraint=models.UniqueConstraint(fields=('from_source', 'to_source'), name='vast_pipeline_relatedsource_unique_pair'),
        ),
        migrations.AddConstraint(
            model_name='measurementpair',
            constraint=models.UniqueConstraint(fields=('source', 'measurement_a', 'measurement_b'), name='vast_pipeline_measurementpair_unique_pair'),
        ),
    ]