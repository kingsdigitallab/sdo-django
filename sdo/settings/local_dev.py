from .base import *  # noqa

ALLOWED_HOSTS = ['127.0.0.1',
                 'localhost',
                 '[::1]',
                 'sdo3-dev.kdl.kcl.ac.uk']

CACHE_REDIS_DATABASE = '2'
CACHES['default']['LOCATION'] = 'redis://127.0.0.1:6379/' + CACHE_REDIS_DATABASE  # noqa

DEBUG = True

INTERNAL_IPS = INTERNAL_IPS + ['']

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'app_sdo3_dev',
        'USER': 'app_sdo3',
        'PASSWORD': '',
        'HOST': ''
    },
}

LOGGING_LEVEL = logging.DEBUG

LOGGING['loggers']['sdo']['level'] = LOGGING_LEVEL

SECRET_KEY = ''

# -----------------------------------------------------------------------------
# Django Debug Toolbar
# http://django-debug-toolbar.readthedocs.org/en/latest/
# -----------------------------------------------------------------------------

try:
    import debug_toolbar  # noqa

    INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar', ]
    MIDDLEWARE += [
        'debug_toolbar.middleware.DebugToolbarMiddleware']
    DEBUG_TOOLBAR_PATCH_SETTINGS = True
except ImportError:
    pass
