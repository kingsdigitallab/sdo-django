import os.path

from lxml import etree

from django.contrib.sites.models import Site
from django.shortcuts import render_to_response, render
from django.http import HttpResponse, Http404
from django.template import RequestContext, Context, loader
from django.views.generic import ListView
from django.db.models import Q

import eats.names as namehandler
from eats.models import (
    Authority, AuthorityRecord, Calendar, DatePeriod, DateType, Entity,
    EntityTypeList, Language, Name, NameType, Script, UserProfile,
    get_default_object)
from eats.forms.main import SearchForm
from eats.settings import app_path
from eats.eatsml.exporter import Exporter

to_xtm_xslt = etree.parse(os.path.join(app_path, 'xsl/eatsml-to-xtm.xsl'))
to_xtm_transform = etree.XSLT(to_xtm_xslt)
to_eac_xslt = etree.parse(os.path.join(
    app_path, 'xsl/eatsml-to-eac-individual.xsl'))
to_eac_transform = etree.XSLT(to_eac_xslt)


def index(request):
    return render(request, 'eats/view/index.html')


def get_user_defaults():
    """Return a dictionary of the user default objects."""
    authority = get_default_object(Authority)
    language = get_default_object(Language, authority)
    script = get_default_object(Script, authority)
    calendar = get_default_object(Calendar, authority)
    date_type = get_default_object(DateType, authority)
    date_period = get_default_object(DatePeriod, authority)
    name_type = get_default_object(NameType, authority)
    return {'authority': authority, 'language': language,
            'script': script, 'calendar': calendar,
            'date_type': date_type, 'date_period': date_period,
            'name_type': name_type}


def create_default_profile(user):
    """Create a default profile for user and return it."""
    defaults = get_user_defaults()
    user_profile = UserProfile(user=user, **defaults)
    user_profile.save()
    return user_profile


def get_model_preferences(user):
    """Return a dictionary of the user's preferred objects."""
    if user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            # Create a default profile.
            profile = create_default_profile(user)
        preferences = {'authority': profile.authority,
                       'language': profile.language,
                       'script': profile.script,
                       'calendar': profile.calendar}
    else:
        preferences = get_user_defaults()
    return preferences


def display_entity(request, entity_id):
    """Display entity details in HTML."""
    try:
        entity_object = Entity.objects.get(pk=int(entity_id))
    except Entity.DoesNotExist:
        raise Http404
    current_site = Site.objects.get_current()
    # QAZ: Hack to specify which, if any, authority records are suitable
    # for producing EAC-CPF.
    entity_types = ('person', 'family', 'organisation')
    eac_authority_records = [
        entity_type.assertion.authority_record for
        entity_type in entity_object.get_entity_types()
        if str(entity_type) in entity_types]
    context_data = {
        'entity': entity_object,
        'eac_authority_records': eac_authority_records,
        'site': current_site}
    return render(request, 'eats/view/display_entity.html', context_data)


def display_entity_eatsml(request, entity_id):
    """Display entity details in EATSML."""
    try:
        entity_object = Entity.objects.get(pk=int(entity_id))
    except Entity.DoesNotExist:
        raise Http404
    try:
        eatsml_root = Exporter().export_entities([entity_object])
    except Exception as e:
        response = render_to_response('500.html', {'message': e.message},
                                      context_instance=RequestContext(request))
        response.status_code = 500
        return response
    xml = etree.tostring(eatsml_root, encoding='utf-8',
                         pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


def display_entity_full_eatsml(request, entity_id):
    """Display full entity details in EATSML."""
    try:
        entity_object = Entity.objects.get(pk=int(entity_id))
    except Entity.DoesNotExist:
        raise Http404
    try:
        eatsml_root = Exporter().export_entities(
            [entity_object], full_details=True)
    except Exception as e:
        response = render_to_response('500.html', {'message': e.message},
                                      context_instance=RequestContext(request))
        response.status_code = 500
        return response
    xml = etree.tostring(eatsml_root, encoding='utf-8',
                         pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


def display_entity_xtm(request, entity_id):
    """Display entity details in XTM."""
    try:
        entity_object = Entity.objects.get(pk=int(entity_id))
    except Entity.DoesNotExist:
        raise Http404
    current_site = Site.objects.get_current()
    # QAZ: The following is a hack. There must be a proper way to get
    # the base URL. And in fact this base URL should really be part of
    # the EATSML.
    path = entity_object.get_absolute_url()
    if path[-1] == '/':
        path = path[:-1]
    path = path[:path.rfind('/') + 1]
    base_psi_url = "'http://%s%s'" % (current_site.domain, path)
    eatsml_root = Exporter().export_entities([entity_object])
    xtm_tree = to_xtm_transform(eatsml_root, base_psi_url=base_psi_url)
    xml = etree.tostring(xtm_tree.getroot(), encoding='utf-8',
                         pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


def display_entity_eac(request, entity_id, authority_record_id):
    """Display entity details in EAC."""
    try:
        entity = Entity.objects.get(pk=int(entity_id))
    except Entity.DoesNotExist:
        raise Http404
    try:
        authority_record = AuthorityRecord.objects.get(
            pk=int(authority_record_id))
    except AuthorityRecord.DoesNotExist:
        raise Http404
    if authority_record not in entity.get_authority_records():
        raise Http404
    current_site = Site.objects.get_current()
    eatsml_root = Exporter().export_entities([entity])
    eac_tree = to_eac_transform(
        eatsml_root, entity_id="'%s'" % entity_id,
        authority_record_id="'%s'" % authority_record_id,
        base_url="'%s'" % current_site.domain)
    xml = etree.tostring(eac_tree.getroot(), encoding='utf-8',
                         pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


def search(request):
    """View for HTML search form and results."""
    results = set([])
    preferences = get_model_preferences(request.user)
    if request.GET:
        form_data = request.GET
    else:
        form_data = None
    authority_id = preferences['authority'].id
    form = SearchForm(initial={'authority': authority_id}, data=form_data)
    if form.is_valid():
        if form.cleaned_data['name']:
            name = form.cleaned_data['name']
            results = get_name_search_results(name)
        else:
            authority = form.cleaned_data['authority']
            record_id = form.cleaned_data['record_id']
            record_url = form.cleaned_data['record_url']
            results = get_record_search_results(authority, record_id,
                                                record_url)
    context_data = {'eats_full_search_form': form,
                    'eats_search_results': results}
    return render(request, 'eats/view/search.html', context_data)


def lookup(request):
    """View for EATSML search results."""
    results = set([])
    search_terms = request.GET.copy()
    name = search_terms.get('name', '')
    authority = search_terms.get('authority', '')
    record_id = search_terms.get('record_id', '')
    record_url = search_terms.get('record_url', '')
    if name:
        results = get_name_search_results(name)
    elif authority and (record_id or record_url):
        results = get_record_search_results(authority, record_id,
                                            record_url)
    from eats.eatsml.exporter import Exporter
    exporter = Exporter()
    exporter.set_user(request.user)
    try:
        eatsml_root = exporter.export_entities(list(results), annotated=True)
    except Exception as e:
        response = render_to_response('500.html', {'message': e.message},
                                      context_instance=RequestContext(request))
        response.status_code = 500
        return response
    xml = etree.tostring(eatsml_root, encoding='utf-8', pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


def get_name_search_results(name):
    """Return a list of Entity objects which have names matching
    argument name_string.

    Arguments:
    name -- string name

    """
    name = namehandler.unpunctuate_name(name)
    name = namehandler.clean_name(name)
    name_parts = name.split()
    queries = []
    for name_part in name_parts:
        query_terms = [name_part]
        ascii_form = namehandler.asciify_name(name_part)
        if ascii_form and ascii_form != name_part:
            query_terms.append(ascii_form)
        queries.append(create_search_query(query_terms))
    sets = []
    for query in queries:
        sets.append(set(Entity.objects.filter(query)))
    intersected_set = sets[0]
    for i in range(1, len(sets)):
        intersected_set = intersected_set.intersection(sets[i])
    entity_list = list(intersected_set)
    entity_list.sort(key=Entity.get_single_name)
    return entity_list


def create_search_query(terms):
    """Return a Q search query for terms."""
    query = None
    for term in terms:
        if query is None:
            query = Q(search_names__name_form__istartswith=term) | \
                Q(search_names__name_form__icontains=' %s' % (term))
        else:
            query = query | Q(search_names__name_form__istartswith=term) | \
                Q(search_names__name_form__icontains=' %s' % (term))
    return query


def get_record_search_results(authority_id, record_id, record_url):
    """Return a list of Entity objects which are associated with the
    authority record defined by authority_id, record_id, and
    record_url."""
    queries = []
    if record_id:
        queries.append(
            Q(assertions__authority_record__authority_system_id=record_id))
    if record_url:
        queries.append(
            Q(assertions__authority_record__authority_system_url=record_url))
    Qs = None
    for query in queries:
        if Qs:
            Qs = Qs | query
        else:
            Qs = query
    results = set(
        Entity.objects.filter(
            Qs, assertions__authority_record__authority__pk=authority_id
        ).distinct())
    return results


def get_names(request):
    """Return an XML representation of all entity names, their primary
    authority ids, and their entity type."""
    compiled_names = {}
    for name in Name.objects.all().select_related():
        name_variants = namehandler.compile_variants(name)
        if name_variants:
            key = name.get_entity().primary_authority()
            if key in compiled_names:
                compiled_names[key][1].extend(name_variants)
            else:
                entity_type = name.get_entity().entity_type.entity_type
                compiled_names[key] = (entity_type, name_variants)
    template = loader.get_template('eats/all_names.xml')
    context = Context({'entities': compiled_names})
    return HttpResponse(template.render(context),
                        content_type='text/xml')


def get_primary_authority_records(request):
    """Return an XML document listing all primary authority keys which
    are associated with an entity."""
    authority = get_default_object(Authority)
    results = AuthorityRecord.objects.filter(
        assertions__existence__isnull=False, authority=authority)
    return ListView(
        request, results, template_name='eats/primary_authority_records.xml',
        allow_empty=True, content_type='text/xml')


def entity_types(request):
    """View to display a list of all the entity types."""
    entity_types = EntityTypeList.objects.all()
    context_data = {'entity_types': entity_types}
    return render(request, 'eats/view/entity_types.html', context_data)


def entities_by_type(request, entity_type_id):
    """View to display a list of all the entities of a given types."""
    try:
        entity_type = EntityTypeList.objects.get(pk=entity_type_id).entity_type
    except EntityTypeList.DoesNotExist:
        raise Http404
    entities = Entity.objects.filter(
        assertions__entity_type__entity_type=entity_type_id)
    context_data = {'entities': entities,
                    'entity_count': len(entities),
                    'entity_type': entity_type}
    return render(request, 'eats/view/entities_by_type.html', context_data)
