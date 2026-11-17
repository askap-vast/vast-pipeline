# Minimal Django setup for dask workers
import os
import sys
import logging
import django
import warnings

from astropy.utils.exceptions import AstropyWarning
warnings.simplefilter("ignore", category=AstropyWarning)


class _HeartbeatFilter(logging.Filter):
    """Drop the heartbeat error a worker logs when it is killed in a restart."""

    def filter(self, record):
        return "Failed to communicate with scheduler during heartbeat" not in record.getMessage()


logging.getLogger("distributed.worker").addFilter(_HeartbeatFilter())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webinterface.settings')
dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, dir_path)
django.setup()
