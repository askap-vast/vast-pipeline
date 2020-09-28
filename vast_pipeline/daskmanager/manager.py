# code from https://github.com/MoonVision/django-dask-demo

import logging

from dask.distributed import Client, LocalCluster
from django.conf import settings as s
from . import config


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
        try:
            logger.info('Trying connecting to Dask Cluster')
            self.client = Client(
                f'{s.DASK_SCHEDULER_HOST}:{s.DASK_SCHEDULER_PORT}'
            )
            logger.info('Connected to Dask Cluster')
        except Exception:
            # assume a local cluster
            logger.info('Starting local Dask Cluster')
            cluster = LocalCluster(
                host=s.DASK_SCHEDULER_HOST,
                scheduler_port=int(s.DASK_SCHEDULER_PORT)
            )
            self.client = Client(cluster)
            logger.info('Connected to local Dask Cluster')

    def persist(self, collection):
        return self.client.persist(collection)

    def compute(self, collection):
        return self.client.compute(collection)

    def get_nr_workers(self):
        return len(self.client.scheduler_info()['workers'].keys())
