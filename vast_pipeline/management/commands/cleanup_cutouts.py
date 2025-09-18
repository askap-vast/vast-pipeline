import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from vast_pipeline.models import ImageCutout

from argparse import ArgumentParser


CUTOFF_DAYS = settings.CUTOFF_DAYS
MAX_SIZE_GB = settings.MAX_SIZE_GB
CUTOUTS_PATH = settings.MEDIA_ROOT


class Command(BaseCommand):
    help = 'Deletes old ImageCutouts based on last_accessed or if storage exceeds limit'

    def get_dir_size(self, path):
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        return total

    def delete_cutout(self, cutout):
        try:
            path = cutout.image.path
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                os.remove(path)
                self.stdout.write(f"Deleted file: {path}")
            else:
                file_size = 0
                self.stdout.write(f"File not found: {path}")

            with transaction.atomic():
                deleted_id = cutout.id
                cutout.delete()
                self.stdout.write(f"Deleted DB record ID: {deleted_id}")
        except Exception as e:
            self.stdout.write(f"Error deleting {cutout.id}: {str(e)}")
            file_size = 0

        return file_size

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Enables arguments for the command.

        Args:
            parser (ArgumentParser): The parser object of the command.

        Returns:
            None
        """
        # positional arguments
        parser.add_argument(
            '--cutoff-days',
            type=int,
            required=False,
            help="Remove data older than this number of days. Default to CUTOFF_DAYS provided in settings",
            default=CUTOFF_DAYS
        )

        parser.add_argument(
            '--max-size-gb',
            type=float,
            required=False,
            default=MAX_SIZE_GB,
            help="Maximum size of the cache in GB. Default to MAX_SIZE_GB provided in settings.",
        )

    def handle(self, *args, **kwargs):

        if not CUTOUTS_PATH:
            self.stdout.write("CUTOUTS_PATH is not set. Aborting cleanup.")
            return

        cutoff_days = kwargs['cutoff_days']
        max_size_gb = kwargs['max_size_gb']
        
        now = timezone.now()

        # delete based on age
        total_bytes = self.get_dir_size(CUTOUTS_PATH)
        threshold = now - timedelta(days=cutoff_days)
        old_cutouts = ImageCutout.objects.filter(last_accessed__lt=threshold)
        self.stdout.write(f"Deleting {old_cutouts.count()} cutouts older than {cutoff_days} days.")
        for cutout in old_cutouts:
            reclaimed_size_bytes = self.delete_cutout(cutout)
            total_bytes -= reclaimed_size_bytes

        # get total directory size
        total_gb = total_bytes / (1024 ** 3)
        self.stdout.write(f"Current cutout dir size: {total_gb:.2f} GB")

        if total_gb > max_size_gb:
            self.stdout.write(f"Cutout size exceeds {max_size_gb}GB. Trimming...")
            # sorting based on oldest accessed
            cutouts = ImageCutout.objects.order_by('last_accessed')
            for cutout in cutouts:
                reclaimed_size_bytes = self.delete_cutout(cutout)
                total_bytes -= reclaimed_size_bytes
                total_gb = total_bytes / (1024 ** 3)
                if total_gb <= max_size_gb:
                    self.stdout.write(f"Trimmed down to {total_gb:.2f} GB.")
                    break
        else:
            self.stdout.write("Cutout size is within the limit. No trimming needed.")
