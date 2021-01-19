import os
import sys
import django
import warnings

from astropy.utils.exceptions import AstropyWarning
warnings.simplefilter("ignore", category=AstropyWarning)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webinterface.settings')
dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, dir_path)
django.setup()
