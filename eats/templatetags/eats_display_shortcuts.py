from django import template

register = template.Library()
@register.inclusion_tag('eats/search_authority_name.html')
def eats_display_name_authority(name):
    return {
        'authority_name': name.get_authority().get_short_name(),
        'name': name,
        'url': name.get_authority_record().get_url(),
    }


@register.inclusion_tag('eats/view/linked_authority_record_id.html')
def eats_display_linked_authority_record_id(authority_record):
    return {
        'id': authority_record.get_id() or authority_record.get_url(),
        'url': authority_record.get_url(),
    }


@register.inclusion_tag('eats/view/linked_authority_record.html')
def eats_display_linked_authority_record(authority_record, abbreviated=False):
    if abbreviated:
        authority = authority_record.authority.get_short_name()
    else:
        authority = authority_record.authority.authority
    return {
        'id': authority_record.get_id() or authority_record.get_url(),
        'url': authority_record.get_url(),
        'authority': authority,
    }


@register.inclusion_tag('eats/view/date_display.html')
def eats_display_dates_for_property(property):
    return {'dates': property.assertion.dates.all()}
