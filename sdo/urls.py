from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from kdl_ldap.signal_handlers import \
    register_signal_handlers as kdl_ldap_register_signal_hadlers

kdl_ldap_register_signal_hadlers()


admin.autodiscover()

urlpatterns = [
    path('', include('archives.urls')),
    path('admin/', admin.site.urls),
    path('eats/', include('eats.urls')),
    path('accounts/', include('django.contrib.auth.urls')),

]

# -----------------------------------------------------------------------------
# Django Debug Toolbar URLS
# -----------------------------------------------------------------------------
try:
    if settings.DEBUG:
        import debug_toolbar
        urlpatterns = [
            re_path(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
except ImportError:
    pass

# -----------------------------------------------------------------------------
# Static file DEBUGGING
# -----------------------------------------------------------------------------
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    import os.path

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=os.path.join(settings.MEDIA_ROOT))
