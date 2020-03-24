from django.contrib import admin
from eats.models import Authority, Calendar, DatePeriod, DateType, \
    EntityRelationshipType, EntityTypeList, Language, NamePartType, \
    NameRelationshipType, NameType, Script, SystemNamePartType, \
    UserProfile


class AuthorityAdmin (admin.ModelAdmin):
    pass


class CalendarAdmin (admin.ModelAdmin):
    pass


class DatePeriodAdmin (admin.ModelAdmin):
    pass


class DateTypeAdmin (admin.ModelAdmin):
    pass


class EntityRelationshipTypeAdmin (admin.ModelAdmin):
    pass


class EntityTypeListAdmin (admin.ModelAdmin):
    pass


class LanguageAdmin (admin.ModelAdmin):
    pass


class NamePartTypeAdmin (admin.ModelAdmin):
    pass


class NameRelationshipTypeAdmin (admin.ModelAdmin):
    pass


class NameTypeAdmin (admin.ModelAdmin):
    pass


class ScriptAdmin (admin.ModelAdmin):
    pass


class SystemNamePartTypeAdmin (admin.ModelAdmin):
    pass


class UserProfileAdmin (admin.ModelAdmin):
    pass


admin.site.register(Authority, AuthorityAdmin)
admin.site.register(Calendar, CalendarAdmin)
admin.site.register(DatePeriod, DatePeriodAdmin)
admin.site.register(DateType, DateTypeAdmin)
admin.site.register(EntityRelationshipType, EntityRelationshipTypeAdmin)
admin.site.register(EntityTypeList, EntityTypeListAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(NamePartType, NamePartTypeAdmin)
admin.site.register(NameRelationshipType, NameRelationshipTypeAdmin)
admin.site.register(NameType, NameTypeAdmin)
admin.site.register(Script, ScriptAdmin)
admin.site.register(SystemNamePartType, SystemNamePartTypeAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
