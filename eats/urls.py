from django.conf.urls import url
from eats.views import edit, main

urlpatterns = [
    url(r'^$', main.index),
    url(r'^(?P<entity_id>\d+)/$', main.display_entity),
    url(r'^(?P<entity_id>\d+)/eatsml/full/', main.display_entity_full_eatsml),
    url(r'^(?P<entity_id>\d+)/eatsml/', main.display_entity_eatsml),
    url(r'^(?P<entity_id>\d+)/xtm/', main.display_entity_xtm),
    url(r'^(?P<entity_id>\d+)/eac/(?P<authority_record_id>\d+)/',
        main.display_entity_eac),
    url(r'^search/$', main.search, name='search'),  # Human usable search
    url(r'^lookup/$', main.lookup),  # Machine usable search, used by clients
    url(r'^entities/types/$', main.entity_types),
    url(r'^entities/(?P<entity_type_id>\d+)/$',
        main.entities_by_type, name='entities_by_type'),
    url(r'^get_names/$', main.get_names),
    url(r'^get_primary_authority_records/$',
        main.get_primary_authority_records),

    # Human usable import from EATSML
    url(r'^edit/import/$', edit.import_eatsml),
    url(r'^edit/import/(?P<import_id>\d+)/$', edit.display_import),
    url(r'^edit/import/(?P<import_id>\d+)/raw/$', edit.display_import_raw),
    url(r'^edit/import/(?P<import_id>\d+)/processed/$',
        edit.display_import_processed),
    url(r'^edit/export/eatsml/$', edit.export_eatsml),
    url(r'^edit/export/eatsml/base/$', edit.export_base_eatsml),
    url(r'^edit/export/eatsml/(?P<authority_id>\d+)/$', edit.export_eatsml),
    url(r'^edit/export/xslt/$', edit.export_xslt_list),
    url(r'^edit/export/xslt/(?P<xslt>[A-Za-z0-9_\-]+)/', edit.export_xslt),
    url(r'^edit/create_entity/$', edit.create_entity, name='create_entity'),
    url(r'^edit/create_date/(?P<assertion_id>\d+)/$', edit.create_date),
    url(r'^edit/create_name/(?P<entity_id>\d+)/$', edit.create_name),
    url(r'^edit/select_entity/$', edit.select_entity),
    url(r'^edit/select_authority_record/$', edit.select_authority_record),
    url(r'^edit/delete/entity/(?P<entity_id>\d+)/$', edit.delete_entity),
    url(r'^edit/delete/(?P<model_name>[^/]+)/(?P<object_id>\d+)/$',
        edit.delete_object),
    url(r'^edit/(?P<model_name>[^/]+)/(?P<object_id>\d+)/$',
        edit.edit_model_object, name='edit_model_object'),
    url(r'^edit/update_name_search_forms/$', edit.update_name_search_forms),


]
