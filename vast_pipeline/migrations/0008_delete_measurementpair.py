# Generated by Django 3.2.9 on 2021-12-03 20:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vast_pipeline', '0007_alter_measurement_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MeasurementPair',
        ),
    ]
