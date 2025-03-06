# Original code from https://github.com/MoonVision/django-dask-demo

import logging
import random
import time

from dask.distributed import Client, LocalCluster
from django.conf import settings as s
from . import config # noqa: F401

logger = logging.getLogger(__name__)

def _start_cluster():
    logger.info('Starting local Dask Cluster')
    cluster = LocalCluster(
            n_workers=int(s.DASK_NUM_WORKERS),
            threads_per_worker=s.DASK_THREADS_PER_WORKER,
            host=s.DASK_SCHEDULER_HOST,
            scheduler_port=int(s.DASK_SCHEDULER_PORT)
        )
    client = Client(cluster)
    logger.info('Connected to local Dask Cluster')
    return client

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = (
                super(Singleton, cls).__call__(*args, **kwargs)
            )
        return cls._instances[cls]

class DaskManager(metaclass=Singleton):
    def __init__(self, skip_connect: bool = False):
        self.dedicated_client = True
        if skip_connect:
            self.client = _start_cluster()
        else:
            try:
                logger.info('Attempting to connect to existing Dask Cluster')
                self.client = Client(
                    f'{s.DASK_SCHEDULER_HOST}:{s.DASK_SCHEDULER_PORT}',
                )
                self.dedicated_client = False
                logger.info('Connected to Dask Cluster at %s:%s',
                            s.DASK_SCHEDULER_HOST, s.DASK_SCHEDULER_PORT)
            except Exception:
                logger.warning('Could not connect to Dask Cluster - starting locally instead')
                self.client = _start_cluster()
        
        self.num_workers = len(self.client.scheduler_info()['workers'].keys())

    def persist(self, collection):
        return self.client.persist(collection)

    def compute(self, collection, **kwargs):
        return self.client.compute(collection, **kwargs)
    
    def get_n_random_workers(self, n):
        """Return n random workers from the pool"""
        return random.sample(list(self.client.scheduler_info()['workers'].keys()), n)

    def restart(self):
        """Restart the cluster and flush all memory"""
        self.client.restart()

    def shutdown(self):
        """Shut down the cluster safely"""
        logger.info("Shutting down Dask client")
        
        logger.info("Cancelling futures...")
        self.client.cancel(self.client.futures)
        
        logger.info("Retiring workers...")
        self.client.retire_workers()
        time.sleep(1)
        
        logger.debug("Running shutdown...")
        self.client.shutdown()
        logger.debug("Running close...")
        self.client.close()
        logger.info("Dask client shut down.")
