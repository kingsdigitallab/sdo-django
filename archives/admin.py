from django.contrib import admin

from archives.models import *
from archives.forms import DocumentForm


class AddressInline(admin.StackedInline):
    model = Address
    extra = 1


class ContainerStatementInline(admin.TabularInline):
    model = ContainerStatements
    extra = 1


class DocumentStatementInline(admin.TabularInline):
    model = DocumentStatements
    extra = 1


class CollectionStatementInline(admin.TabularInline):
    model = CollectionStatements
    extra = 1


class AddressAdmin(admin.ModelAdmin):
    search_fields = ['address1']


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier', 'description')
    inlines = [AddressInline]
    save_on_top = True
    search_fields = ['name']


class ContainerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'get_collection_full_name',
                    'box', 'folder', 'series', 'description', 'content_type')
    list_filter = ('content_type', 'collection')
    inlines = [ContainerStatementInline]
    search_fields = ['collection__name', 'collection__identifier',
                     'box', 'folder', 'series', 'description']
    fieldsets = [
        (None, {'fields': ['collection', 'content_type']}),
        ('Container Identifiers', {'fields': ['series', 'box', 'folder']}),
    ]
    save_on_top = True


class DocumentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'id_supplied', 'get_container_full_label',
                    'get_container_content_type', 'coverage_start', 'coverage_end', 'description')
    list_filter = ('container',)
    inlines = [DocumentStatementInline]
    form = DocumentForm
    save_on_top = True


class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_supplied', 'identifier',
                    'repository', 'description')
    inlines = [CollectionStatementInline]
    search_fields = ['name', 'identifier', 'description']
    save_on_top = True


admin.site.register(Collection, CollectionAdmin)
admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Container, ContainerAdmin)
admin.site.register(Document, DocumentAdmin)
