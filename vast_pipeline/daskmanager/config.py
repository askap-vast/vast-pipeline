# Set up configuration options for dask
# see https://docs.dask.org/en/latest/configuration.html
import os
import dask
import dask.distributed

dask_config = dask.config.config

# Update the workers to load the initialisation script
basefolder = os.path.dirname(__file__)
worker_init_file_path = os.path.join(basefolder, 'worker_init.py')
dask_config['distributed']['worker']['preload'].append(worker_init_file_path)

# Disallow pyarrow string conversion
dask_config['dataframe']['convert-string'] = False

# Memory configuration for workers
# NOTE: These are set to False to stop memory overflow spill-to-disk
# pause and terminate conditions on the workers which can happen
# routinely durin the IO steps in the pipeline, when a subset
# of workers read a set of FITS files into memory.
dask_config['distributed']['worker']['memory']['target'] = False
dask_config['distributed']['worker']['memory']['spill'] = 0.9
dask_config['distributed']['worker']['memory']['pause'] = False
dask_config['distributed']['worker']['memory']['terminate'] = False

# Further distributed configuration
# (see: https://distributed.dask.org/en/stable/worker-memory.html)
dask_config['distributed']['multiprocessing-method'] = 'spawn'
dask_config['distributed']['admin']['log-length'] = 0
dask_config['distributed']['admin']['low-level-log-length'] = 0

# Add logging config
# See: https://docs.dask.org/en/latest/how-to/debug.html#logs
dask_config['logging'] = {}
dask_config['logging']['distributed'] = 'error'
dask_config['logging']['shuffle'] = 'error'

# Set the new config as default
dask.config.update_defaults(dask_config)
