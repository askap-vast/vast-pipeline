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
    # pipeline app and others
    'pipeline',
] + env('EXTRA_APPS', cast=list, default=[])

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
            ],
            'libraries': {
                'unit_tags': 'pipeline.utils.unit_tags'
            }
        },
    },
]

WSGI_APPLICATION = 'webinterface.wsgi.application'


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

AUTHENTICATION_BACKENDS = [
    'social_core.backends.github.GithubTeamOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_URL = 'logout'
LOGOUT_REDIRECT_URL = 'login'

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
    'pipeline.utils.auth.create_admin_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'pipeline.utils.auth.load_github_avatar',
    'social_core.pipeline.user.user_details',
)

SOCIAL_AUTH_GITHUB_TEAM_KEY = env('SOCIAL_AUTH_GITHUB_KEY', cast=str, default='')
SOCIAL_AUTH_GITHUB_TEAM_SECRET = env('SOCIAL_AUTH_GITHUB_SECRET', cast=str, default='')
SOCIAL_AUTH_GITHUB_TEAM_ID = env('SOCIAL_AUTH_GITHUB_TEAM_ID', cast=str, default='')
SOCIAL_AUTH_GITHUB_TEAM_ADMIN = env('SOCIAL_AUTH_GITHUB_TEAM_ADMIN', cast=str, default='')
SOCIAL_AUTH_GITHUB_TEAM_SCOPE = ['read:org', 'user:email']


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': env.db()
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
