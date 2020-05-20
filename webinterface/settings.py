"""
Django settings for pipelinedev project.

Generated by 'django-admin startproject' using Django 2.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import environ
from typing import List

# Load the Django congig from the .env file
env = environ.Env()
environ.Env.read_env()


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', cast=str, default='FillMeUPWithSomeComplicatedString')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', cast=bool, default=True)

ALLOWED_HOSTS: List[str] = env('ALLOWED_HOSTS', cast=list, default=[])

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework_datatables',
    # pipeline app and others
    'pipeline.apps.PipelineConfig',
] + env('EXTRA_APPS', cast=list, default=[])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
] + env('EXTRA_MIDDLEWARE', cast=list, default=[])

ROOT_URLCONF = 'webinterface.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR + '/templates/', ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'unit_tags': 'pipeline.utils.unit_tags'
            }
        },
    },
]

WSGI_APPLICATION = 'webinterface.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': env.db()
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# REST framework settings
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_datatables.renderers.DatatablesRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_datatables.filters.DatatablesFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework_datatables.pagination.DatatablesPageNumberPagination',
    'PAGE_SIZE': 100,
}

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = env('STATIC_URL', cast=str, default='/static/')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)
STATIC_ROOT = env('STATIC_ROOT', cast=str, default=os.path.join(BASE_DIR, 'staticfiles'))

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
        'format': '{asctime} {process:d} {thread:d} {name} {levelname} {message}',
        'style': '{',
        },
        'default': {
        'format': '{asctime} {module} {levelname} {message}',
        'style': '{',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # root logger
        '': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'INFO',
        },
        'Aegean': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'INFO',
        },
    }
}

# PIPELINE settings
# project default folder
PIPELINE_WORKING_DIR = env('PIPELINE_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'pipeline-runs'))
if '/' not in PIPELINE_WORKING_DIR:
    PIPELINE_WORKING_DIR = os.path.join(BASE_DIR, PIPELINE_WORKING_DIR)

# reference surveys default folder
SURVEYS_WORKING_DIR = env('SURVEYS_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'reference-surveys'))
if '/' not in SURVEYS_WORKING_DIR:
    SURVEYS_WORKING_DIR = os.path.join(BASE_DIR, SURVEYS_WORKING_DIR)

# allowed source finders
SOURCE_FINDERS = ['selavy']

# default source finder
DEFAULT_SOURCE_FINDER = 'selavy'

# minimum default accepted error on flux
FLUX_DEFAULT_MIN_ERROR = env('FLUX_DEFAULT_MIN_ERROR', cast=float, default=0.001)

# minimum default accepted error on ra and dec
POS_DEFAULT_MIN_ERROR = env('POS_DEFAULT_MIN_ERROR', cast=float, default=0.01)
