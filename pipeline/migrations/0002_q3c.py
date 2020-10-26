# Generated by Django 2.2.5 on 2020-02-19 10:46

from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('pipeline', '0001_initial')
    ]

    operations = [
        migrations.RunSQL(
            ["CREATE EXTENSION IF NOT EXISTS q3c;"],#upgrade
            ["DROP EXTENSION IF EXISTS q3c;"],#downgrade
        ),
        migrations.RunSQL(
            ["CREATE INDEX ON pipeline_measurement (q3c_ang2ipix(ra, dec));"],
            ["DROP INDEX pipeline_measurement_q3c_ang2ipix_idx;"],
        ),
        migrations.RunSQL(
            ["CLUSTER pipeline_measurement_q3c_ang2ipix_idx ON pipeline_measurement;"],
            [],
        ),
        migrations.RunSQL(
            ["ANALYZE pipeline_measurement;"],
            [],
        ),
        migrations.RunSQL(
            ["CREATE INDEX ON pipeline_source (q3c_ang2ipix(wavg_ra, wavg_dec));"],
            ["DROP INDEX pipeline_source_q3c_ang2ipix_idx;"],
        ),
        migrations.RunSQL(
            ["CLUSTER pipeline_source_q3c_ang2ipix_idx ON pipeline_source;"],
            [],
        ),
        migrations.RunSQL(
            ["ANALYZE pipeline_source;"],
            [],
        ),
    ]