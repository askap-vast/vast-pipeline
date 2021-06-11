import os
import environ

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
ALLOWED_HOSTS = env('ALLOWED_HOSTS', cast=list, default=[])
INTERNAL_IPS = [
    '127.0.0.1',
]

SITE_ID = 1

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
    'social_django',
    'crispy_forms',
    'django_q',
    'tagulous',
    # pipeline app and others
    'vast_pipeline',
] + env('EXTRA_APPS', cast=list, default=[])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
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
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'vast_pipeline.context_processors.maintainance_banner',
                'vast_pipeline.context_processors.pipeline_version',
            ],
            'libraries': {
                'unit_tags': 'vast_pipeline.utils.unit_tags'
            }
        },
    },
]

WSGI_APPLICATION = 'webinterface.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Authentication
# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]

# docs @ https://python-social-auth.readthedocs.io/en/latest/backends/github.html#github
AUTHENTICATION_BACKENDS = [
    'social_core.backends.github.GithubOrganizationOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_URL = 'logout'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_ERROR_URL = 'login'

SOCIAL_AUTH_STRATEGY = 'social_django.strategy.DjangoStrategy'
SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'
SOCIAL_AUTH_POSTGRES_JSONFIELD = True
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['email']
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'vast_pipeline.utils.auth.create_admin_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'vast_pipeline.utils.auth.load_github_avatar',
    'social_core.pipeline.user.user_details',
)

SOCIAL_AUTH_GITHUB_ORG_KEY = env('SOCIAL_AUTH_GITHUB_KEY', cast=str, default='')
SOCIAL_AUTH_GITHUB_ORG_SECRET = env('SOCIAL_AUTH_GITHUB_SECRET', cast=str, default='')
SOCIAL_AUTH_GITHUB_ORG_NAME = env('SOCIAL_AUTH_GITHUB_ORG_NAME', cast=str, default='')
SOCIAL_AUTH_GITHUB_ADMIN_TEAM = env('SOCIAL_AUTH_GITHUB_ADMIN_TEAM', cast=str, default='')
SOCIAL_AUTH_GITHUB_ORG_SCOPE = ['read:org', 'user:email']

CRISPY_TEMPLATE_PACK = "bootstrap4"

TNS_API_KEY = env('TNS_API_KEY', default=None)
TNS_USER_AGENT = env('TNS_USER_AGENT', default=None)

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': env.db()
}

# Cache (necessary to run pipeline jobs from UI)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'pipeline_cache_table',
    }
}

# Django Queue Cluster
Q_CLUSTER = {
    'name': 'VastPipeline',
    'workers': 3,
    'timeout': 86400,
    'queue_limit': 6,
    'ack_failures': True,
    'bulk': 10,
    'orm': 'default',# same as above in DATABASES but can be changed
    'label': 'Django Q tasks',
    'daemonize_workers': False,
    'recycle': 100,
    'retry': 86402
}

# REST framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
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
BASE_URL = env('BASE_URL', cast=str, default=None)
STATIC_URL = env('STATIC_URL', cast=str, default='/static/')
if BASE_URL:
    STATIC_URL = '/' + BASE_URL.strip('/') + '/' + STATIC_URL.strip('/') + '/'
STATICFILES_DIRS = env('STATICFILES_DIRS', cast=list, default=[os.path.join(BASE_DIR, 'static')])
STATIC_ROOT = env('STATIC_ROOT', cast=str, default=os.path.join(BASE_DIR, 'staticfiles'))
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
    }
}

# PRODUCTION SETTINGS
if not DEBUG:
    # ideally you want to check the site rating at https://securityheaders.com/
    # as suggested here https://adamj.eu/tech/2019/04/10/how-to-score-a+-for-security-headers-on-your-django-website/
    # SECURE_SSL_REDIRECT = True # set this to True when your reverse proxy server does not redirect http to https
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000 # see https://docs.djangoproject.com/en/3.1/ref/middleware/#http-strict-transport-security
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'same-origin' # see https://docs.djangoproject.com/en/3.0/ref/middleware/#referrer-policy
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # from https://ubuntu.com/blog/django-behind-a-proxy-fixing-absolute-urls
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# PIPELINE settings
# project default folder
PIPELINE_WORKING_DIR = env('PIPELINE_WORKING_DIR', cast=str, default=os.path.join(BASE_DIR, 'pipeline-runs'))
if '/' not in PIPELINE_WORKING_DIR:
    PIPELINE_WORKING_DIR = os.path.join(BASE_DIR, PIPELINE_WORKING_DIR)

# raw image data folder (containing FITS files, selavy, etc)
RAW_IMAGE_DIR = env('RAW_IMAGE_DIR', cast=str, default=os.path.join(BASE_DIR, 'raw-images'))
if '/' not in RAW_IMAGE_DIR:
    RAW_IMAGE_DIR = os.path.join(BASE_DIR, RAW_IMAGE_DIR)

# extra user-supplied data folder, relative to the user's home directory on the deployment machine
HOME_DATA_DIR = env('HOME_DATA_DIR', cast=str, default='vast-pipeline-extra-data')

# allowed source finders
SOURCE_FINDERS = ['selavy']

# default source finder
DEFAULT_SOURCE_FINDER = 'selavy'

# defaults source association methods
DEFAULT_ASSOCIATION_METHODS = ['basic', 'advanced', 'deruiter']

# minimum default accepted error on flux
FLUX_DEFAULT_MIN_ERROR = env('FLUX_DEFAULT_MIN_ERROR', cast=float, default=0.001)

# minimum default accepted error on ra and dec
POS_DEFAULT_MIN_ERROR = env('POS_DEFAULT_MIN_ERROR', cast=float, default=0.01)

# Default pipeline run config values
PIPE_RUN_CONFIG_DEFAULTS = {
    'image_files': [],
    'selavy_files': [],
    'background_files': [],
    'noise_files': [],
    'source_finder': 'selavy',
    'monitor': False,
    'monitor_min_sigma': 3.0,
    'monitor_edge_buffer_scale': 1.2,
    'monitor_cluster_threshold': 3.0,
    'monitor_allow_nan': False,
    'astrometric_uncertainty_ra': 1,
    'astrometric_uncertainty_dec': 1,
    'association_parallel': False,
    'association_epoch_duplicate_radius': 2.5,
    'association_method': 'basic',
    'association_radius': 10.,
    'association_de_ruiter_radius': 5.68,
    'association_beamwidth_limit': 1.5,
    'new_source_min_sigma': 5.0,
    'flux_perc_error': 0,
    'use_condon_errors': True,
    'selavy_local_rms_zero_fill_value': 0.2,
    'create_measurements_arrow_files': False,
    'suppress_astropy_warnings': True,
    'source_aggregate_pair_metrics_min_abs_vs': 4.3,
}

# default max concurrent pipeline runs
MAX_PIPELINE_RUNS = env('MAX_PIPELINE_RUNS', cast=int, default=3)

# maximum number of images for non-admin runs
MAX_PIPERUN_IMAGES = env('MAX_PIPERUN_IMAGES', cast=int, default=200)

# pipeline maintainance message/banner
PIPELINE_MAINTAINANCE_MESSAGE = env('PIPELINE_MAINTAINANCE_MESSAGE', cast=str, default=None)
