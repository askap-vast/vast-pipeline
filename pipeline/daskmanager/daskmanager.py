# code from https://github.com/MoonVision/django-dask-demo

import logging

from dask.distributed import Client, LocalCluster
from django.conf import settings as s


logger = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = (
                super(Singleton, cls).__call__(*args, **kwargs)
            )
        return cls._instances[cls]


class DaskManager(metaclass=Singleton):
    def __init__(self):
        if not s.DASK_SCHEDULER_HOST and not s.DASK_SCHEDULER_PORT:
            # assume a local cluster
            logger.info('Starting local Dask Cluster')
            self.cluster = LocalCluster()
            self.client = Client()
            logger.info('Connected to local Dask Cluster')
        else:
            self.client = Client(
                f'{s.DASK_SCHEDULER_HOST}:{s.DASK_SCHEDULER_PORT}'
            )
            self.cluster = self.client.cluster
            logger.info('Connected to Dask Cluster')

    @classmethod
    def persist(self, collection):
        return self.client.persist(collection)
