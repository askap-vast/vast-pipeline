# Original code from https://github.com/MoonVision/django-dask-demo

import logging
import random
import time

from dask.distributed import Client, LocalCluster
from django.conf import settings as s
from . import config # noqa: F401

logger = logging.getLogger(__name__)

def _start_cluster():
    logger.info('Starting local Dask Cluster...')
    logger.info(f"n_workers: {s.DASK_NUM_WORKERS}")
    logger.info(f"threads_per_worker: {s.DASK_THREADS_PER_WORKER}")
    logger.info(f"scheduler_host: {s.DASK_SCHEDULER_HOST}")
    logger.info(f"scheduler_port: {s.DASK_SCHEDULER_PORT}")
    logger.info(f"dashboard_host: {s.DASK_DASHBOARD_HOST}")
    logger.info(f"dashboard_port: {s.DASK_DASHBOARD_PORT}")

    cluster = LocalCluster(
            n_workers=int(s.DASK_NUM_WORKERS),
            threads_per_worker=s.DASK_THREADS_PER_WORKER,
            host=s.DASK_SCHEDULER_HOST,
            scheduler_port=int(s.DASK_SCHEDULER_PORT),
            dashboard_address=f"{s.DASK_DASHBOARD_HOST}:{s.DASK_DASHBOARD_PORT}",
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
            client_ip = f'{s.DASK_SCHEDULER_HOST}:{s.DASK_SCHEDULER_PORT}'
            try:
                logger.info('Attempting to connect to existing Dask Cluster')
                self.client = Client(client_ip)
                self.dedicated_client = False
                logger.info('Connected to Dask Cluster at %s',client_ip)
            except Exception:
                logger.warning('Could not connect to Dask Cluster at %s - starting locally instead', client_ip)
                self.client = _start_cluster()
        
        self.num_workers = len(self.client.scheduler_info()['workers'].keys())

    def persist(self, collection):
        return self.client.persist(collection)

    def compute(self, collection, **kwargs):
        return self.client.compute(collection, **kwargs)
    
    def get_n_random_workers(self, n):
        """Return n random workers from the pool"""
        logger.debug("Getting %d random workers...", n)
        return random.sample(list(self.client.scheduler_info()['workers'].keys()), n)

    def restart(self):
        """Restart the cluster and flush all memory"""
        self.client.restart()

    def shutdown(self):
        """Shut down the cluster safely"""
        logger.info("Shutting down Dask Cluster")

        logger.info("Cancelling futures...")
        self.client.cancel(self.client.futures)

        logger.info("Retiring workers...")
        self.client.retire_workers()
        time.sleep(1)

        logger.debug("Running shutdown...")
        self.client.shutdown()
        logger.debug("Running close...")
        self.client.close()
        logger.info("Dask Cluster shut down.")
