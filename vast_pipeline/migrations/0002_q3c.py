# Generated by Django 2.2.5 on 2020-02-19 10:46

from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('vast_pipeline', '0001_initial')
    ]

    operations = [
        migrations.RunSQL(
            ["CREATE EXTENSION IF NOT EXISTS q3c;"],#upgrade
            ["DROP EXTENSION IF EXISTS q3c;"],#downgrade
        ),
        migrations.RunSQL(
            ["CREATE INDEX ON vast_pipeline_measurement (q3c_ang2ipix(ra, dec));"],
            ["DROP INDEX vast_pipeline_measurement_q3c_ang2ipix_idx;"],
        ),
        migrations.RunSQL(
            ["CLUSTER vast_pipeline_measurement_q3c_ang2ipix_idx ON vast_pipeline_measurement;"],
            [],
        ),
        migrations.RunSQL(
            ["ANALYZE vast_pipeline_measurement;"],
            [],
        ),
        migrations.RunSQL(
            ["CREATE INDEX ON vast_pipeline_source (q3c_ang2ipix(wavg_ra, wavg_dec));"],
            ["DROP INDEX vast_pipeline_source_q3c_ang2ipix_idx;"],
        ),
        migrations.RunSQL(
            ["CLUSTER vast_pipeline_source_q3c_ang2ipix_idx ON vast_pipeline_source;"],
            [],
        ),
        migrations.RunSQL(
            ["ANALYZE vast_pipeline_source;"],
            [],
        ),
    ]