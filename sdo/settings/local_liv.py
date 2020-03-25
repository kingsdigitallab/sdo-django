from .base import *  # noqa

ALLOWED_HOSTS = ['sdo3.kdl.kcl.ac.uk']

INTERNAL_IPS = INTERNAL_IPS + ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_sdo3_liv',
        'USER': 'app_sdo3',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
