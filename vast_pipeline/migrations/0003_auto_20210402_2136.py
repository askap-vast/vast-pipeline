# Generated by Django 3.1.7 on 2021-04-02 21:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vast_pipeline', '0002_q3c'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='m_abs_significant_max_int',
            field=models.FloatField(default=0.0, help_text='Maximum absolute value of all measurement pair modulation indices for int flux that exceed variability.source_aggregate_pair_metrics_min_abs_vs in the pipeline run configuration.'),
        ),
        migrations.AlterField(
            model_name='source',
            name='m_abs_significant_max_peak',
            field=models.FloatField(default=0.0, help_text='Maximum absolute value of all measurement pair modulation indices for  peak flux that exceed variability.source_aggregate_pair_metrics_min_abs_vs in the pipeline run configuration.'),
        ),
        migrations.AlterField(
            model_name='source',
            name='vs_abs_significant_max_int',
            field=models.FloatField(default=0.0, help_text='Maximum value of all measurement pair variability t-statistics for int flux that exceed variability.source_aggregate_pair_metrics_min_abs_vs in the pipeline run configuration.'),
        ),
        migrations.AlterField(
            model_name='source',
            name='vs_abs_significant_max_peak',
            field=models.FloatField(default=0.0, help_text='Maximum absolute value of all measurement pair variability t-statistics for peak flux that exceed variability.source_aggregate_pair_metrics_min_abs_vs in the pipeline run configuration.'),
        ),
    ]
