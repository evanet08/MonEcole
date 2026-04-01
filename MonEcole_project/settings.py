from pathlib import Path
import os
import sys
import logging
from decouple import config
from django.contrib.messages import constants as messages

# Logging UTF-8
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setStream(sys.stdout)
        handler.stream.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent

# Messages
try:
    MESSAGE_TAGS = {
        messages.DEBUG: 'alert-info',
        messages.INFO: 'alert-info',
        messages.SUCCESS: 'alert-success',
        messages.WARNING: 'alert-warning',
        messages.ERROR: 'alert-danger',
    }
except Exception:
    pass

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default='True', cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')
if '.monecole.pro' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.monecole.pro')
# Ensure wildcard covers all subdomains in production
if '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

# Auth is handled by PersonnelAuthMiddleware + session — no Django auth backends needed

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'MonEcole_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'MonEcole_app.middleware.auth.PersonnelAuthMiddleware',
    'MonEcole_app.middleware.tenant.TenantMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'MonEcole_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'MonEcole_project.wsgi.application'

# ── Databases ──
# default = spoke (db_monecole) — données opérationnelles établissement
# countryStructure = hub — données structurelles nationales
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    },
    'countryStructure': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': 'countryStructure',
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    },
}

DATABASE_ROUTERS = ['MonEcole_app.db_routers.CountryStructureRouter']

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/login/'
LOGOUT_REDIRECT_URL = '/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Bujumbura'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': sys.stdout,
        },
    },
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(asctime)s %(message)s',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

CSRF_TRUSTED_ORIGINS = [
    'https://monecole.pro',
    'https://www.monecole.pro',
    'http://monecole.pro',
    'http://www.monecole.pro',
    'https://*.monecole.pro',
    'http://*.monecole.pro',
]

# ── Brevo Email API ──
BREVO_API_KEY = config('BREVO_API_KEY', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@monecole.pro')
DEFAULT_FROM_NAME = config('DEFAULT_FROM_NAME', default='MonEcole')

# ── Twilio WhatsApp ──
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')
TWILIO_MESSAGING_SERVICE_SID = config('TWILIO_MESSAGING_SERVICE_SID', default='')
