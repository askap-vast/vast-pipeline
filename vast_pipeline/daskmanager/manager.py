# Original code from https://github.com/MoonVision/django-dask-demo

import logging
import random
import time
from typing import Dict, Optional, Union

import pandas as pd
import pyarrow as pa
import dask.dataframe as dd

from dask.distributed import Client, LocalCluster, Semaphore, WorkerPlugin
from distributed.comm.core import CommClosedError
from django.conf import settings as s
from . import config # noqa: F401

logger = logging.getLogger(__name__)

def _start_cluster():
    logger.info('Starting local Dask Cluster...')
    logger.info(f"n_workers: {s.DASK_NUM_WORKERS}")
    logger.info(f"threads_per_worker: {s.DASK_THREADS_PER_WORKER}")
    logger.info(f"memory per worker: {s.DASK_MEM_PER_WORKER}")
    logger.info(f"scheduler_host: {s.DASK_SCHEDULER_HOST}")
    logger.info(f"scheduler_port: {s.DASK_SCHEDULER_PORT}")
    logger.info(f"dashboard_host: {s.DASK_DASHBOARD_HOST}")
    logger.info(f"dashboard_port: {s.DASK_DASHBOARD_PORT}")

    cluster = LocalCluster(
            n_workers=int(s.DASK_NUM_WORKERS),
            threads_per_worker=s.DASK_THREADS_PER_WORKER,
            host=s.DASK_SCHEDULER_HOST,
            scheduler_port=int(s.DASK_SCHEDULER_PORT),
            memory_limit=s.DASK_MEM_PER_WORKER,
            dashboard_address=f"{s.DASK_DASHBOARD_HOST}:{s.DASK_DASHBOARD_PORT}",
        )
    client = Client(cluster)
    # Register our new plugin to log worker names
    client.register_plugin(LogWorkerNamePlugin())
    logger.info('Connected to local Dask Cluster')
    return client

def get_io_semaphore(num_workers: int=None):
    """
    Generate a dask semaphore object labelled `io_throttle` for limiting the
    number of parallel IO operations
    
    num_workers:
        Number of workers. If not specified it defaults to the number specified
        in the dask settings.
    """

    if num_workers is None:
        num_workers = int(s.DASK_NUM_IO_WORKERS)
    return Semaphore(name='io_throttle', max_leases=num_workers)

def get_db_semaphore(num_workers: int=None):
    """
    Generate a dask semaphore object labelled `db_throttle` for limiting the
    number of parallel uploads to the database.
    
    num_workers:
        Number of workers. If not specified it defaults to the number specified
        in the dask settings.
    """
    if num_workers is None:
        num_workers = int(s.DASK_NUM_DB_WORKERS)
    return Semaphore(name='db_throttle', max_leases=num_workers)

class WorkerLogFilter(logging.Filter):
    """
    Logging filter to inject the worker id into the LogRecord.
    """
    def __init__(self, worker = '0'):
        self.worker = worker

    def filter(self, record):
        # Inject worker ID to the LogeRecord
        record.msg = f'WORKER:{self.worker} {record.msg}'
        return True

class QuietStreamHandler(logging.StreamHandler):
    """
    Custom logging handler that prevents writing to
    stderr by the workers.
    """
    def __init__(self):
        super().__init__()

    def emit(self, record):
        # Override emit to do nothing
        pass

class LogWorkerNamePlugin(WorkerPlugin):
    """
    A Dask WorkerPlugin to log the worker name in worker logging messages.
    Also sets up a custom logging handler to prevent
    workers from writing to stderr.
    """
    def setup(self, worker):
        worker_name = worker.name
        logger = logging.getLogger('')
        logger.setLevel(logging.DEBUG)
        # Find the existing StreamHandler and remove it
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)
        # Add the QuietStreamHandler to suppress stderr output
        quiet_handler = QuietStreamHandler()
        logger.addHandler(quiet_handler)

        # Add a filter to inject worker name into log records
        worker_filter = WorkerLogFilter(worker=worker_name)

        for handler in logger.handlers:
            handler.addFilter(worker_filter)

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
        
        self.num_workers = len(self.client.scheduler_info(-1)['workers'].keys())

    def persist(self, collection):
        return self.client.persist(collection)

    def compute(self, collection, **kwargs):
        return self.client.compute(collection, **kwargs)
    
    def get_n_random_workers(self, n):
        """Return n random workers from the pool"""
        logger.debug("Getting %d random workers...", n)
        return random.sample(list(self.client.scheduler_info(-1)['workers'].keys()), n)

    def log_cluster_memory(self):
        workers = self.client.scheduler_info(-1)['workers']
        logger.info("Logging memory usage for %d workers...", len(workers))
        for addr, info in workers.items():
            memory_limit = info['memory_limit'] / 1e9

            mem_metrics = info['metrics']
            managed = mem_metrics['managed_bytes'] / 1e9
            spilled_memory = mem_metrics['spilled_bytes']['memory'] / 1e9
            spilled_disk = mem_metrics['spilled_bytes']['disk'] / 1e9
            memory_used = mem_metrics['memory'] / 1e9

            logger.info(f"Worker {addr}: {memory_used:.2f}GB (managed: {managed:.2f}GB, spilled disk: {spilled_disk:.2f}GB, spilled memory: {spilled_memory:.2f}GB) of {memory_limit:.2f}GB.")

    def restart(self):
        """Restart the cluster and flush all memory"""
        self.client.restart()

    def checkpoint_and_restart(
        self,
        checkpoints: Dict[str, Union[pd.DataFrame, dd.DataFrame]],
        schema: Optional[Dict[str, pa.DataType]] = None,
        timeout: int = 180,
    ) -> None:
        """Save dataframes to parquet on disk then restart all workers.

        Each entry in `checkpoints` maps an output path to a DataFrame (either
        pandas or Dask).  Dask DataFrames are written as a directory of part
        files; pandas DataFrames are written as a single file.  Once every
        dataframe has been flushed to disk the cluster workers are restarted via
        :meth:`restart_workers`, clearing all in-memory futures.

        The caller is responsible for reloading the saved parquets after this
        method returns, e.g. with ``dd.read_parquet(path)``.

        Args:
            checkpoints:
                Mapping of output path (str or path-like) to DataFrame.  Dask
                DataFrames are written with ``overwrite=True`` so the call is
                idempotent across re-runs.
            schema:
                Optional ``{field_name: pa.DataType}`` dict for columns whose
                types cannot be inferred correctly (e.g. list-typed columns
                such as ``'related'``).  Only the listed fields are included in
                the partial schema passed to ``to_parquet``; all other column
                types are inferred normally by Dask.
            timeout:
                Seconds to wait for workers to come back online after
                restarting.  Passed through to :meth:`restart_workers`.
            """
        logger.info(
            "Checkpointing %d dataframe(s) to disk before cluster restart...",
            len(checkpoints),
        )

        for path, df in checkpoints.items():
            path = str(path)
            if isinstance(df, dd.DataFrame):
                logger.info("Writing Dask DataFrame to parquet directory: %s", path)
                # write_index: preserve named indexes (e.g. 'source') but drop
                # unnamed integer indexes.
                write_index = df._meta.index.name is not None
                df.to_parquet(path, overwrite=True, write_index=write_index, schema=schema)
            elif isinstance(df, pd.DataFrame):
                logger.info("Writing pandas DataFrame to parquet file: %s", path)
                df.to_parquet(path)
            else:
                raise TypeError(
                    f"Expected a pandas or Dask DataFrame for path '{path}', "
                    f"got {type(df).__name__}"
                )

        self.restart_workers(timeout=timeout)

    def restart_workers(self, timeout: int = 180) -> None:
        """Restart all workers to clear their memory between pipeline steps.

        Logs the current cluster memory state, cancels any outstanding futures,
        restarts all workers (clearing all persisted data), and updates the
        cached worker count.

        This should only be called once all required persisted Dask futures for
        the current step have been computed and their results saved (e.g. to
        parquet or returned as pandas DataFrames). Any persisted data that has
        not been materialised will be lost.

        Args:
            timeout: Seconds to wait for workers to shut down and come back
                online after restarting. Defaults to 180.
        """
        logger.info("Restarting Dask workers to clear memory...")
        self.log_cluster_memory()

        # Cancel any futures still tracked by the client before restarting so
        # the scheduler does not attempt to resubmit them on the new workers.
        # client.cancel() is fire-and-forget, so sleep briefly to give workers
        # time to actually stop their in-flight tasks before the nanny sends
        # SIGTERM.
        if self.client.futures:
            logger.info("Cancelling %d outstanding futures...", len(self.client.futures))
            self.client.cancel(list(self.client.futures))
            time.sleep(5)

        try:
            self.client.restart(timeout=timeout)
        except CommClosedError:
            # The scheduler's batched TCP comm to a dying worker can be closed
            # mid-restart.  Wait briefly for the scheduler to settle, then
            # retry once.
            logger.warning(
                "CommClosedError during worker restart; waiting 5 s and retrying..."
            )
            time.sleep(5)
            self.client.restart(timeout=timeout)
        except TimeoutError:
            # Workers did not shut down within `timeout` seconds (likely still
            # draining I/O or GC).  Wait for the nanny SIGKILL cycle to
            # complete (another `timeout` seconds) and retry once.
            logger.warning(
                "Worker restart timed out after %d s; waiting and retrying with "
                "%d s timeout...",
                timeout,
                timeout * 2,
            )
            time.sleep(10)
            self.client.restart(timeout=timeout * 2)

        self.num_workers = len(self.client.scheduler_info(-1)["workers"].keys())
        logger.info(
            "Dask workers restarted successfully. %d workers available.",
            self.num_workers,
        )

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
