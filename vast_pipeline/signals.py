"""Functions that are executed upon receiving an application signal."""
import logging
from typing import Type

from django.db.models import Count
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from vast_pipeline.models import Run, Image, SkyRegion


logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=Run, dispatch_uid="delete_orphans_for_run")
def delete_orphans_for_run(sender: Type[Run], instance: Run, using: str, **kwargs) -> None:
    """Delete any Image and SkyRegion objects that would be orphaned by deleting the
    given Run. Expects to recieve the arguments sent by the pre_delete signal. See
    <https://docs.djangoproject.com/en/3.1/ref/signals/#pre-delete>.

    Args:
        sender:
            Model class that sent the signal.
        instance:
            Model instance to be deleted.
        using:
            Database alias.

    Returns:
        None
    """
    image_orphans = (
        Image.objects.annotate(num_runs=Count("run"))
        .filter(run=instance, num_runs=1)
    )
    n_obj_deleted, deleted_dict = image_orphans.delete()
    logger.info(
        "Deleted %d objects: %s",
        n_obj_deleted,
        ", ".join([f"{model}: {n}" for model, n in deleted_dict.items()]),
    )

    skyreg_orphans = (
        SkyRegion.objects.annotate(num_runs=Count("run"))
        .filter(run=instance, num_runs=1)
    )
    n_obj_deleted, deleted_dict = skyreg_orphans.delete()
    logger.info(
        "Deleted %d objects: %s",
        n_obj_deleted,
        ", ".join([f"{model}: {n}" for model, n in deleted_dict.items()]),
    )
