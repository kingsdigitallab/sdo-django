from .base import *  # noqa

ALLOWED_HOSTS = ['sdo3-data.kdl.kcl.ac.uk']

CACHE_REDIS_DATABASE = '1'
CACHES['default']['LOCATION'] = 'redis://127.0.0.1:6379/' + CACHE_REDIS_DATABASE  # noqa

INTERNAL_IPS = INTERNAL_IPS + ['']
ALLOWED_HOSTS = ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_sdo3_data',
        'USER': 'app_sdo3',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
