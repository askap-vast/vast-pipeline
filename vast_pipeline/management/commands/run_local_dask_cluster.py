import logging

from time import sleep
from vast_pipeline.daskmanager.manager import DaskManager
from django.core.management.base import BaseCommand, CommandError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    This script run a local Dask cluster
    """
    help = 'Run a local Dask cluster'

    def handle(self, *args, **options):
        dm = DaskManager()
        # self.stdout.write(self.style.INFO(dm.client))
        self.stdout.write(self.style.SUCCESS(str(dm.client)))
        addr = dm.client.cluster.scheduler_info['address'].split(':')[1]
        dashboard_port = str(
            dm.client.cluster.scheduler_info['services']['dashboard']
        )
        self.stdout.write(self.style.SUCCESS(
            'Cluster dashboard: ' +
            ':'.join(['http', addr, dashboard_port])
        ))

        try:
            while True:
                sleep(3600)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in Dask cluster:\n{e}'))
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.SUCCESS('Shutting down Dask cluster'))
