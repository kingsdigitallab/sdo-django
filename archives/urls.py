from django.conf.urls import url
from archives.views import admin, main

urlpatterns = [
    url(r'^$', main.index, name='index'),
    url(r'^dates/$', main.dates),
    url(r'^document/(?P<id>\d+)$', main.document),
    url(r'^admin/export/xsd/(?P<schema_type>[\w\-\w]+)/$', admin.xsd),
    url(r'^admin/report/container/(?P<byContentType>\w+)/$', admin.container),
    url(r'^admin/report/repository/$', admin.repository),
    url(r'^admin/report/collection/$', admin.collection),
]