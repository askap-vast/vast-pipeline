from django.db import migrations, transaction
from vast_pipeline.utils.utils import deg2hms, deg2dms


def update_source_names(apps, schema_editor):
    """Update source names from the v0.2.0 ASKAP_... convention to J..."""
    Source = apps.get_model("vast_pipeline", "Source")
    while Source.objects.filter(name__startswith="ASKAP_").exists():
        # do the updates in transaction batches of 1000 in case the source table is large
        with transaction.atomic():
            for source in Source.objects.filter(name__startswith="ASKAP_")[:1000]:
                source.name = (
                    f"J{deg2hms(source.wavg_ra, precision=1)}"
                    f"{deg2dms(source.wavg_dec, precision=0)}"
                ).replace(":", "")
                source.save()


def reverse_update_source_names(apps, schema_editor):
    """Update source names from J... to the v0.2.0 ASKAP_... convention"""
    Source = apps.get_model("vast_pipeline", "Source")
    while Source.objects.filter(name__startswith="J").exists():
        # do the updates in transaction batches of 1000 in case the source table is large
        with transaction.atomic():
            for source in Source.objects.filter(name__startswith="J")[:1000]:
                source.name = (
                    f"ASKAP_{deg2hms(source.wavg_ra, precision=2)}"
                    f"{deg2dms(source.wavg_dec, precision=2)}"
                ).replace(":", "")
                source.save()


class Migration(migrations.Migration):
    atomic = False  # disable transactions, the source table may be large

    dependencies = [
        ("vast_pipeline", "0003_auto_20210402_2136"),
    ]

    operations = [
        migrations.RunPython(
            update_source_names, reverse_code=reverse_update_source_names
        ),
    ]
