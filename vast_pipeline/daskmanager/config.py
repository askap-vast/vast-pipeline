import os
import dask
import dask.distributed


dask_config = dask.config.config

# update the worker to load the initialisation script
basefolder = os.path.dirname(__file__)
worker_init_file_path = os.path.join(basefolder, 'worker_init.py')
dask_config['distributed']['worker']['preload'].append(worker_init_file_path)

# set the new config as default
dask.config.update_defaults(dask_config)
