from .base import *  # noqa

ALLOWED_HOSTS = ['sdo.kdl.kcl.ac.uk']

INTERNAL_IPS = INTERNAL_IPS + ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_sdo_liv',
        'USER': 'app_sdo',
        'PASSWORD': '',
        'HOST': ''
    },
}

SECRET_KEY = ''
