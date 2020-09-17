import os
import sys
import django


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webinterface.settings')
dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, dir_path)
django.setup()
