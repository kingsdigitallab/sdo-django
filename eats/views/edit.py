import os.path
from io import StringIO

from lxml import etree

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import render
from django.apps import apps

from eats.settings import app_name, app_path
from eats.models import (
    Authority, AuthorityRecord, Date, Entity, EntityRelationshipType,
    EntityTypeList, Name, NamePartType, NameRelationshipType, NameType,
    PropertyAssertion, RegisteredImport, UserProfile)
from eats.forms.edit import (
    AuthorityRecordCreateForm, AuthorityRecordSearchForm, DateForm,
    EntityNoteForm, EntityRelationshipForm, EntityRelationshipNoteForm,
    EntitySelectorForm, EntityTypeForm, ExistenceForm, GenericFormSet,
    ImportForm, NameForm, NameNoteForm, NamePartForm, NameRelationshipForm,
    NameRelationshipFormSet, ReferenceForm)
from eats.views.main import get_model_preferences, \
    get_name_search_results, get_record_search_results, search
from eats.eatsml.exporter import Exporter
from eats.eatsml.importer import Importer


class EATSAuthenticationException (Exception):
    """Exception class for authentication failures."""

    def __init__(self, url):
        # url is a URL to redirect to.
        self.url = url

    def get_url(self):
        return self.url


def get_editable_authorities(user, authority=None):
    """Return a profile and QuerySet of editable authorities. Raise an
    EATSAuthenticationException if there is no user profile or no
    editable authorities.

    If authority is supplied, raise an exception if that authority is
    not found among the editable authorities.

    """
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        # QAZ: send the user to a 'permission denied' page.
        raise EATSAuthenticationException('/')
    editable_authorities = profile.editable_authorities.all()
    if authority and authority not in editable_authorities:
        # QAZ: send the user to a 'permission denied' page.
        raise EATSAuthenticationException('/')
    elif not editable_authorities.count():
        # QAZ: send the user to a 'permission denied' page.
        raise EATSAuthenticationException('/')
    return profile, editable_authorities


@login_required()
def create_entity(request):
    """View to create a new entity with an existence assertion, using
    details from the logged in user's defaults. On successful
    creation, redirect to the edit page for the new entity."""
    try:
        profile, editable_authorities = get_editable_authorities(request.user)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    if profile.authority in editable_authorities:
        authority = profile.authority
    elif editable_authorities.count() == 1:
        authority = editable_authorities[0]
    else:
        # QAZ: send the user to an error page specifying that it isn't
        # possible to know which authority should be used for the
        # existence assertion.
        return HttpResponseRedirect('/')
    entity = Entity()
    entity.save(authority=authority)
    kw_args = {'model_name': 'entity', 'object_id': entity.id}
    return HttpResponseRedirect(reverse(edit_model_object, kwargs=kw_args))


@login_required()
def create_date(request, assertion_id):
    """View to create a date for an assertion."""
    assertion = get_object_or_404(PropertyAssertion, pk=assertion_id)
    authority = assertion.authority_record.authority
    try:
        profile, editable_authorities = get_editable_authorities(request.user,
                                                                 authority)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    calendar_id = profile.calendar.id
    date_type_id = profile.date_type.id
    initial_data = {'start_date_calendar': calendar_id,
                    'start_date_type': date_type_id,
                    'end_date_calendar': calendar_id,
                    'end_date_type': date_type_id,
                    'point_date_calendar': calendar_id,
                    'point_date_type': date_type_id,
                    'start_terminus_post_calendar': calendar_id,
                    'start_terminus_post_type': date_type_id,
                    'start_terminus_ante_calendar': calendar_id,
                    'start_terminus_ante_type': date_type_id,
                    'point_terminus_post_calendar': calendar_id,
                    'point_terminus_post_type': date_type_id,
                    'point_terminus_ante_calendar': calendar_id,
                    'point_terminus_ante_type': date_type_id,
                    'end_terminus_post_calendar': calendar_id,
                    'end_terminus_post_type': date_type_id,
                    'end_terminus_ante_calendar': calendar_id,
                    'end_terminus_ante_type': date_type_id,
                    'date_period': profile.date_period.id}
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['assertion'] = assertion_id
        form = DateForm(data=post_data)
        if form.is_valid():
            date = form.save()
            kw_args = {}
            if post_data.get('submit_continue'):
                kw_args['model_name'] = 'date'
                kw_args['object_id'] = date.id
            else:
                # Redirect to the page for the assertion this date is
                # associated with.
                property_type = date.assertion.get_type()
                if property_type == 'name':
                    kw_args['model_name'] = 'name'
                    kw_args['object_id'] = date.assertion.name.id
                else:
                    kw_args['model_name'] = 'entity'
                    kw_args['object_id'] = date.assertion.entity.id
            return HttpResponseRedirect(reverse(edit_model_object,
                                                kwargs=kw_args))
    else:
        form = DateForm(initial=initial_data)
    context_data = {'form': form}
    return render(request, 'eats/edit/add_date.html', context_data)


@login_required()
def create_name(request, entity_id):
    """View to create a Name and associate it with an entity."""
    entity = get_object_or_404(Entity, pk=entity_id)
    try:
        profile, editable_authorities = get_editable_authorities(request.user)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    number_name_part_forms = 4
    number_name_note_forms = 1
    name_part_forms = []
    name_note_forms = []
    authority_records = get_authority_records(entity, editable_authorities)
    # select the first NameType with 'is_default' set as True (EATS allows
    # multiple defaults, because...?)
    default_name_type = NameType.objects.order_by('-is_default')[0]
    initial_data = {'language': profile.language.id,
                    'script': profile.script.id,
                    'name_type': default_name_type.pk}
    extra_data = {}
    context_data = {}
    extra_data['name_types'] = NameType.objects.filter(
        authority__in=editable_authorities)
    name_part_types = NamePartType.objects.filter(
        authority__in=editable_authorities)
    name_id = None
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['entity'] = entity.id
        # NameType is limited by the Authority. Therefore we have to
        # get a valid form, from which we can get the Authority, and
        # then limit the NameTypes to those associated with the
        # Authority. This requires creating the form again, with the
        # extra information.
        name_form = NameForm(authority_records, extra_data, data=post_data)
        if name_form.is_valid():
            authority_record = name_form.cleaned_data['authority_record']
            extra_data['name_types'] = NameType.objects.filter(
                authority=authority_record.authority)
            name_form = NameForm(authority_records, extra_data, data=post_data)
        if name_form.is_valid():
            name = name_form.save()
            name_id = name.id
            # NamePartType is limited by the Authority and Language.
            language = name.language
            name_part_types = NamePartType.objects\
                .filter(system_name_part_type__languages=language)\
                .filter(authority=authority_record.authority)
    else:
        post_data = None
        if len(authority_records) == 1:
            authority = authority_records[0].authority
            extra_data['name_types'] = NameType.objects.filter(
                authority=authority)
            name_part_types = NamePartType.objects.filter(
                authority=authority)
        name_form = NameForm(authority_records, extra_data,
                             initial=initial_data)
    # Create the inline forms.
    extra_data['name_part_types'] = name_part_types
    # Name part inline forms.
    name_part_type_select_ids = []
    for i in range(1, number_name_part_forms + 1):
        prefix = 'name_part_%d' % (i)
        if name_id is not None:
            post_data['%s-name' % (prefix)] = name_id
        name_part_form = NamePartForm(
            extra_data, data=post_data, prefix=prefix)
        name_part_form.is_new_form = True
        name_part_forms.append(name_part_form)
        # This is a gross hack. There really ought to be a way to get
        # the ID of the widget.
        name_part_type_select_ids.append(
            'id_%s' % (name_part_form.add_prefix('name_part_type')))
    for i in range(1, number_name_note_forms + 1):
        prefix = 'name_note_%d' % (i)
        if name_id is not None:
            post_data['%s-name' % (prefix)] = name_id
        name_note_form = NameNoteForm(data=post_data, prefix=prefix)
        name_note_form.is_new_form = True
        name_note_forms.append(name_note_form)
    if name_form.is_valid():
        valid_forms = []
        has_errors = False
        for form in name_part_forms + name_note_forms:
            if form.has_post_data():
                if form.is_valid():
                    valid_forms.append(form)
                else:
                    has_errors = True
        if not has_errors:
            # Create and save a PropertyAssertion.
            is_preferred = name_form.cleaned_data.get('is_preferred')
            assertion = PropertyAssertion(entity=entity, name=name,
                                          authority_record=authority_record,
                                          is_preferred=is_preferred)
            assertion.save()
            # Save the name form again in order to prompt the creation
            # of SearchNames.
            name_form.save()
            # Save the associated forms.
            for form in valid_forms:
                form.save()
            transaction.commit()
            kw_args = {}
            if post_data.get('submit_continue'):
                kw_args['model_name'] = 'name'
                kw_args['object_id'] = name_id
            else:
                kw_args['model_name'] = 'entity'
                kw_args['object_id'] = entity.id
            return HttpResponseRedirect(reverse(edit_model_object,
                                                kwargs=kw_args))
    transaction.rollback()
    context_data['authority_records'] = authority_records
    # Create mappings between authority ID and name (part) types, for
    # use by the JavaScript select changer.
    context_data['name_type_map'] = map_by_authority(extra_data['name_types'])
    context_data['name_part_type_map'] = map_by_authority(name_part_types)
    context_data['name_part_type_select_ids'] = name_part_type_select_ids
    context_data['name_form'] = name_form
    context_data['name_part_forms'] = name_part_forms
    context_data['name_note_forms'] = name_note_forms
    return render(request, 'eats/edit/add_name.html', context_data)


def map_by_authority(model_objects):
    """Return a dictionary keying model_objects by each object's
    authority_id."""
    object_map = {}
    for model_object in model_objects:
        authority_id = model_object.authority_id
        if authority_id in object_map:
            object_map[authority_id].append(model_object)
        else:
            object_map[authority_id] = [model_object]
    return object_map


@login_required()
def select_authority_record(request):
    """View for selecting or creating an authority record for an
    Existence property assertion."""
    # QAZ: Ensure that the user has permission to assign a record from
    # the authority.
    try:
        profile, editable_authorities = get_editable_authorities(request.user)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    context_data = {'show_search': True}
    search_form = AuthorityRecordSearchForm(editable_authorities)
    create_form = AuthorityRecordCreateForm(editable_authorities)
    if request.method == 'POST':
        if request.POST.get('submit_search'):
            search_form = AuthorityRecordSearchForm(
                editable_authorities, data=request.POST)
            if search_form.is_valid():
                authority_id = search_form.cleaned_data['search_authority']
                authority = Authority.objects.get(pk=authority_id)
                base_id = authority.base_id
                base_url = authority.base_url
                record_id = search_form.cleaned_data['search_record_id']
                record_url = search_form.cleaned_data['search_record_url']
                queries = []
                # When searching, take into account the possible split
                # of an ID or URL into a base element (associated with
                # the authority) and a record-specific element.
                if record_id:
                    queries.append(Q(authority_system_id=record_id))
                    queries.append(Q(authority_system_id=base_id + record_id))
                    if record_id.startswith(base_id):
                        index = len(base_id)
                        queries.append(
                            Q(authority_system_id=record_id[index:]))
                if record_url:
                    queries.append(Q(authority_system_url=record_url))
                    queries.append(
                        Q(authority_system_url=base_url + record_url))
                    if record_url.startswith(base_url):
                        index = len(base_url)
                        queries.append(
                            Q(authority_system_url=record_url[index:]))
                Qs = None
                for query in queries:
                    if Qs:
                        Qs = Qs | query
                    else:
                        Qs = query
                records = AuthorityRecord.objects.filter(
                    authority=authority).filter(Qs)
                context_data['search_results'] = records
        elif request.POST.get('submit_create'):
            context_data['show_search'] = False
            create_form = AuthorityRecordCreateForm(
                editable_authorities, data=request.POST)
            # Populate the search form only with the hidden fields for
            # tracking the link to the opening window's widgets.
            data = {'authority_record_id_widget_id':
                    request.POST.get('authority_record_id_widget_id'),
                    'authority_record_name_widget_id':
                    request.POST.get('authority_record_name_widget_id')}
            search_form = AuthorityRecordSearchForm(
                editable_authorities, data=data)
            if create_form.is_valid():
                authority_record = create_form.save()
                context_data['create_result'] = authority_record
    context_data['search_form'] = search_form
    context_data['create_form'] = create_form
    context_data['authorities'] = editable_authorities
    return render(request, 'eats/edit/authority_record.html', context_data)


@login_required()
def select_entity(request):
    """View for searching for and selecting an entity to be supplied to an
    entity relationship form."""
    try:
        profile, editable_authorities = get_editable_authorities(request.user)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    context_data = {}
    results = set([])
    if request.method == 'POST':
        post_data = request.POST
    else:
        post_data = None
    form = EntitySelectorForm(editable_authorities, data=post_data)
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
    context_data['form'] = form
    context_data['entity_selector'] = True
    context_data['eats_search_results'] = results
    return render(request, 'eats/edit/select_entity.html', context_data)


def get_authority_records(entity, authorities):
    """Return a QuerySet of authority records available to entity
    and which are associated with one of the authorities."""
    return entity.get_authority_records().filter(authority__in=authorities)


@login_required()
def delete_entity(request, entity_id):
    """View to confirm the deletion of an entity."""
    # QAZ: This must be disabled once the site is edited by multiple
    # organisations.
    model_name = Entity._meta.model_name
    entity_object = get_object_or_404(Entity, pk=entity_id)
    if request.method == 'POST':
        kw_args = {}
        if request.POST.get('submit_delete'):
            # Delete the object.
            entity_object.delete()
            return HttpResponseRedirect(reverse(search))
        else:
            kw_args['model_name'] = model_name
            kw_args['object_id'] = entity_id
            return HttpResponseRedirect(
                reverse(edit_model_object, kwargs=kw_args))
    else:
        # Assemble some context to aid in helping the user determine
        # whether this object should be deleted.
        context_data = {
            'object_type': model_name,
            'object_value': entity_object,
        }
        return render(request, 'eats/edit/confirm_delete.html', context_data)


@login_required()
def delete_object(request, model_name, object_id):
    """View to confirm the deletion of an object."""
    try:
        model = apps.get_model('{}.{}'.format(app_name, model_name))
        eats_object = model.objects.get(pk=object_id)
    except BaseException:
        raise Http404
    if model == Date:
        assertion = eats_object.assertion
    elif model == Name:
        assertion = eats_object.assertion
    else:
        raise Http404
    authority = assertion.authority_record.authority
    try:
        profile, editable_authorities = get_editable_authorities(request.user,
                                                                 authority)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    if request.method == 'POST':
        kw_args = {}
        if request.POST.get('submit_delete'):
            # Go to the edit page for the 'parent' object of the
            # deleted object.
            if model == Name:
                kw_args['model_name'] = Entity._meta.model_name
                kw_args['object_id'] = Entity.objects.get(
                    assertions__name__pk=object_id).id
            else:
                parent_model_name = Entity._meta.model_name
                assertion = PropertyAssertion.objects.get(dates__pk=object_id)
                if assertion.name:
                    parent_model_name = Name._meta.model_name
                    object_id = assertion.name.id
                else:
                    object_id = assertion.entity.id
                kw_args['model_name'] = parent_model_name
                kw_args['object_id'] = object_id
            # Delete the object.
            eats_object.delete()
        else:
            kw_args['model_name'] = model_name
            kw_args['object_id'] = object_id
        return HttpResponseRedirect(reverse(edit_model_object, kwargs=kw_args))
    else:
        # Assemble some context to aid in helping the user determine
        # whether this object should be deleted.
        context_data = {
            'object_type': model_name,
            'object_value': eats_object,
        }
        return render(request, 'eats/edit/confirm_delete.html', context_data)


def edit_date(request, date, editable_authorities):
    """View to edit an existing Date object."""
    # QAZ: display errors on the template.
    context_data = {'date': date, 'entity': date.assertion.entity}
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['assertion'] = date.assertion.id
        if post_data.get('submit_delete'):
            return HttpResponseRedirect(reverse(delete_object,
                                                kwargs={'model_name': 'date',
                                                        'object_id': date.id}))
        form = DateForm(instance=date, data=post_data)
        if form.is_valid():
            form.save()
            kw_args = {}
            if post_data.get('submit_continue'):
                kw_args['model_name'] = 'date'
                kw_args['object_id'] = date.id
            else:
                # Redirect to the page for the assertion this date is
                # associated with.
                property_type = date.assertion.get_type()
                if property_type == 'name':
                    kw_args['model_name'] = 'name'
                    kw_args['object_id'] = date.assertion.name.id
                else:
                    kw_args['model_name'] = 'entity'
                    kw_args['object_id'] = date.assertion.entity.id
            return HttpResponseRedirect(reverse(edit_model_object,
                                                kwargs=kw_args))
    else:
        form = DateForm(instance=date)
    context_data['form'] = form
    return render(request, 'eats/edit/edit_date.html', context_data)


def edit_entity(request, entity, editable_authorities):
    """View to edit an existing Entity object."""
    context_data = {'entity': entity}
    authority_records = get_authority_records(entity, editable_authorities)
    usable_entity_types = EntityTypeList.objects.filter(
        authority__in=editable_authorities)
    usable_entity_relationship_types = EntityRelationshipType.objects.filter(
        authority__in=editable_authorities)
    usable_name_relationship_types = NameRelationshipType.objects.filter(
        authority__in=editable_authorities)
    usable_names = Name.objects.filter(assertion__entity=entity).filter(
        assertion__authority_record__authority__in=editable_authorities)
    user_prefs = get_model_preferences(request.user)
    assertion_type_data = {
        'existence': {'query': Q(existence__isnull=False),
                      'form_class': ExistenceForm, 'new_forms': 1},
        'entity_type': {'query': Q(entity_type__isnull=False),
                        'form_class': EntityTypeForm, 'new_forms': 1,
                        'data': {'entity_types': usable_entity_types}},
        'name': {'query': Q(name__isnull=False)},
        'name_relationship': {'query': Q(name_relationship__isnull=False),
                              'form_class': NameRelationshipForm,
                              'form_set_class': NameRelationshipFormSet,
                              'data': {'names': usable_names,
                                       'name_relationship_types':
                                           usable_name_relationship_types},
                              'new_forms': 1},
        'entity_relationship': {
            'query': Q(entity_relationship__isnull=False),
            'form_class': EntityRelationshipForm,
            'new_forms': 2,
            'data': {'entity_relationship_types':
                     usable_entity_relationship_types,
                     'user_prefs': user_prefs},
            'inline': {'related_name': 'notes',
                       'new_forms': 1,
                       'form_class': EntityRelationshipNoteForm}},
        'note': {'query': Q(note__isnull=False),
                 'form_class': EntityNoteForm, 'new_forms': 1},
        'reference': {'query': Q(reference__isnull=False),
                      'form_class': ReferenceForm, 'new_forms': 2},
        # 'generic_property': [Q(generic_property__isnull=False), GenericForm]
    }
    editable_lookup = Q(authority_record__authority__in=editable_authorities)
    form_data = {
        'errors': False, 'creations': [], 'saves': [], 'deletions': [],
        'inline_saves': [], 'inline_deletions': [], 'bound_instance_forms': [],
        'bound_new_forms': [], 'bound_inline_instance_forms': [],
        'bound_inline_new_forms': [], 'existence_saves': []}
    if request.method == 'POST':
        post_data = request.POST
    else:
        post_data = None
    # Create the lists of forms and assertions.
    for assertion_type, assertion_data in list(assertion_type_data.items()):
        assertions = PropertyAssertion.objects\
            .filter(assertion_data['query'])\
            .filter(Q(entity=entity))
        editable_assertions = assertions.filter(editable_lookup)
        non_editable_assertions = assertions.exclude(editable_lookup)
        form_class = assertion_data.get('form_class')
        if form_class:
            # Create a formset for each assertion type.
            form_set_class = assertion_data.get('form_set_class',
                                                GenericFormSet)
            extra_data = assertion_data.get('data', {})
            inline = assertion_data.get('inline', {})
            form_set = form_set_class(assertion_type, form_class,
                                      authority_records)
            form_set.create_forms(editable_assertions, extra_data, post_data,
                                  assertion_data.get('new_forms'), inline)
            bound_instance_forms, bound_new_forms = form_set.get_bound_forms()
            form_data['bound_instance_forms'].extend(bound_instance_forms)
            form_data['bound_new_forms'].extend(bound_new_forms)
            (bound_inline_instance_forms,
             bound_inline_new_forms) = form_set.get_bound_inline_forms()
            form_data['bound_inline_instance_forms'].extend(
                bound_inline_instance_forms)
            form_data['bound_inline_new_forms'].extend(bound_inline_new_forms)
            context_data['%s_form_set' % (assertion_type)] = form_set
        else:
            # No form, just a list of assertions.
            context_data[assertion_type + '_editable'] = editable_assertions
        context_data[assertion_type + '_non_editable'] = \
            non_editable_assertions
    # Validate the forms.
    if post_data is not None:
        if request.POST.get('submit_delete'):
            return HttpResponseRedirect(
                reverse(delete_entity, kwargs={'entity_id': entity.id}))
        for form in form_data['bound_instance_forms']:
            if form.is_valid():
                if form.cleaned_data.get('delete'):
                    form_data['deletions'].append((form.property,
                                                   form.assertion))
                elif isinstance(form, ExistenceForm):
                    form_data['existence_saves'].append((form.assertion, form))
                else:
                    authority_record = form.cleaned_data['authority_record']
                    form.assertion.authority_record = authority_record
                    form_data['saves'].append((form.assertion, form))
            else:
                form_data['errors'] = True
        for form in form_data['bound_new_forms']:
            if form.is_valid():
                if not form.cleaned_data.get('delete'):
                    form_data['creations'].append(form)
            else:
                form_data['errors'] = True
        for form in form_data['bound_inline_instance_forms']:
            if form.is_valid():
                if form.cleaned_data.get('delete'):
                    form_data['inline_deletions'].append(form.instance)
                else:
                    form_data['inline_saves'].append(form)
            else:
                form_data['errors'] = True
        for form in form_data['bound_inline_new_forms']:
            if form.is_valid():
                if not form.cleaned_data.get('delete'):
                    form_data['inline_saves'].append(form)
            else:
                form_data['errors'] = True
        if not form_data['errors']:
            for form in form_data['creations']:
                new_property = form.save()
                authority_record = form.cleaned_data['authority_record']
                is_preferred = form.cleaned_data.get('is_preferred')
                kw_args = {'entity': entity,
                           'authority_record': authority_record,
                           form.property_field: new_property,
                           'is_preferred': is_preferred}
                assertion = PropertyAssertion(**kw_args)
                assertion.save()
            for assertion, form in form_data['saves']:
                assertion.save()
                form.save()
            for form in form_data['inline_saves']:
                form.save()
            for eats_property, assertion in form_data['deletions']:
                eats_property.delete()
                assertion.delete()
            for instance in form_data['inline_deletions']:
                instance.delete()
            for assertion, form in form_data['existence_saves']:
                form.save()
                authority_record = form.cleaned_data['authority_record']
                # Change any assertions that are associated with this
                # assertion's old authority record to use the new one.
                assertions = PropertyAssertion.objects\
                    .filter(entity=assertion.entity,
                            authority_record=assertion.authority_record)\
                    .exclude(pk=assertion.id)
                for non_existence_assertion in assertions:
                    non_existence_assertion.authority_record = authority_record
                    non_existence_assertion.save()
                assertion.authority_record = authority_record
                assertion.save()
            return HttpResponseRedirect(
                reverse(edit_model_object, kwargs={'model_name': 'entity',
                                                   'object_id': entity.id}))
    # Add in reverse entity relationships (ie, those in which the
    # current entity plays the related_entity role). These are not
    # handled as the other assertions, since they are not assertions
    # of the current entity.
    reverse_entity_relationships = entity.get_reverse_relationships()
    context_data['reverse_entity_relationships'] = reverse_entity_relationships
    return render(request, 'eats/edit/edit_entity.html', context_data)


def edit_name(request, name, editable_authorities):
    """View to edit an existing Name object."""
    # Much of the code here is a duplicate or close copy of the code
    # in create_name.
    number_name_part_forms = 2
    number_name_note_forms = 1
    name_part_forms = []
    name_note_forms = []
    assertion = name.assertion
    authority_records = get_authority_records(assertion.entity,
                                              editable_authorities)
    extra_data = {}
    context_data = {}
    extra_data['name_types'] = NameType.objects.filter(
        authority__in=editable_authorities)
    name_part_types = NamePartType.objects.filter(
        authority__in=editable_authorities)
    if request.method == 'POST':
        if request.POST.get('submit_delete'):
            return HttpResponseRedirect(reverse(delete_object,
                                                kwargs={'model_name': 'name',
                                                        'object_id': name.id}))
        post_data = request.POST.copy()
        # NameType is limited by the Authority.
        name_form = NameForm(authority_records, extra_data, instance=name,
                             data=post_data)
        if name_form.is_valid():
            authority_record = name_form.cleaned_data['authority_record']
            extra_data['name_types'] = NameType.objects.filter(
                authority=authority_record.authority)
            name_form = NameForm(authority_records, extra_data, instance=name,
                                 data=post_data)
        if name_form.is_valid():
            # NamePartType is limited by the Authority and Language.
            language = name_form.cleaned_data['language']
            name_part_types = NamePartType.objects\
                .filter(system_name_part_type__languages=language)\
                .filter(authority=authority_record.authority)
    else:
        post_data = None
        initial_data = {'authority_record': assertion.authority_record.id,
                        'is_preferred': assertion.is_preferred}
        extra_data['name_type_choices'] = NameType.objects.filter(
            authority=assertion.authority_record.authority)
        name_form = NameForm(authority_records, extra_data, instance=name,
                             initial=initial_data)
        extra_data['name_part_type_choices'] = NamePartType.objects.filter(
            authority=assertion.authority_record.authority)
    # Create the inline forms.
    extra_data['name_part_types'] = name_part_types
    name_part_type_select_ids = []
    # Instanced name part inline forms.
    for name_part in name.name_parts.all():
        prefix = 'name_part_%d' % (name_part.id)
        name_part_form = NamePartForm(extra_data, prefix=prefix,
                                      instance=name_part, data=post_data)
        name_part_forms.append(name_part_form)
        # This is a gross hack. There really ought to be a way to get
        # the ID of the widget.
        name_part_type_select_ids.append(
            'id_%s' % (name_part_form.add_prefix('name_part_type')))
    # New name part inline forms.
    for i in range(1, number_name_part_forms + 1):
        prefix = 'name_part_new_%d' % (i)
        if post_data is not None:
            post_data['%s-name' % (prefix)] = name.id
        name_part_form = NamePartForm(
            extra_data, prefix=prefix, data=post_data)
        name_part_form.is_new_form = True
        name_part_forms.append(name_part_form)
        # This is a gross hack. There really ought to be a way to get
        # the ID of the widget.
        name_part_type_select_ids.append(
            'id_%s' % (name_part_form.add_prefix('name_part_type')))
    # Instance name note inline forms.
    for name_note in name.notes.all():
        prefix = 'name_note_%d' % (name_note.id)
        name_note_form = NameNoteForm(prefix=prefix, instance=name_note,
                                      data=post_data)
        name_note_forms.append(name_note_form)
    # New name note inline forms.
    for i in range(1, number_name_note_forms + 1):
        prefix = 'name_note_new_%d' % (i)
        if post_data is not None:
            post_data['%s-name' % (prefix)] = name.id
        name_note_form = NameNoteForm(prefix=prefix, data=post_data)
        name_note_form.is_new_form = True
        name_note_forms.append(name_note_form)
    if post_data is not None:
        form_data = {'saves': [], 'creations': [], 'deletions': []}
        has_errors = False
        for form in [name_form] + name_part_forms + name_note_forms:
            if form.is_new_form:
                if form.has_post_data():
                    if form.is_valid():
                        if not form.cleaned_data.get('delete'):
                            form_data['saves'].append(form)
                    else:
                        has_errors = True
                        break
            elif form.is_valid():
                if form.cleaned_data.get('delete'):
                    form_data['deletions'].append(form)
                else:
                    form_data['saves'].append(form)
            else:
                has_errors = True
                break
        if not has_errors:
            for form in form_data['saves']:
                form.save()
            for form in form_data['deletions']:
                form.instance.delete()
            # Save changes to the PropertyAssertion.
            assertion.is_preferred = name_form.cleaned_data.get('is_preferred')
            assertion.authority_record = name_form.cleaned_data.get(
                'authority_record')
            assertion.save()
            kw_args = {}
            if request.POST.get('submit_continue'):
                kw_args['model_name'] = 'name'
                kw_args['object_id'] = name.id
            else:
                kw_args['model_name'] = 'entity'
                kw_args['object_id'] = assertion.entity.id
            return HttpResponseRedirect(reverse(edit_model_object,
                                                kwargs=kw_args))
    context_data['assertion'] = assertion
    context_data['authority_records'] = authority_records
    context_data['name'] = name
    context_data['name_form'] = name_form
    # Create mappings between authority ID and name (part) types, for
    # use by the JavaScript select changer.
    context_data['name_type_map'] = map_by_authority(extra_data['name_types'])
    context_data['name_part_type_map'] = map_by_authority(name_part_types)
    context_data['name_part_type_select_ids'] = name_part_type_select_ids
    context_data['name_part_forms'] = name_part_forms
    context_data['name_note_forms'] = name_note_forms
    context_data['dates'] = assertion.dates.all()
    context_data['edit_form'] = True
    return render(request, 'eats/edit/edit_name.html', context_data)


@login_required()
def edit_model_object(request, model_name, object_id):
    """Return a template for editing the object with object_id in the
    model with model_name.

    Arguments:
    model_name -- string name of the model to which the object being
                  edited belongs
    object_id -- string database id of the object being edited

    """
    try:
        profile, editable_authorities = get_editable_authorities(request.user)
    except EATSAuthenticationException as e:
        return HttpResponseRedirect(e.get_url())
    # Dictionary mapping model names to editing view functions.
    edit_views = {
        'date': edit_date,
        'entity': edit_entity,
        'name': edit_name,
    }

    view_function = edit_views[model_name]
    if view_function is None:
        raise Http404
    try:
        model = apps.get_model('{}.{}'.format(app_name, model_name))
        eats_object = model.objects.get(pk=object_id)
    except BaseException:
        raise Http404
    return view_function(request, eats_object, editable_authorities)


@login_required()
def display_import(request, import_id):
    """Display the details of an import."""
    import_object = get_object_or_404(RegisteredImport, pk=import_id)
    context_data = {'import': import_object}
    return render(request, 'eats/edit/display_import.html', context_data)


@login_required()
def display_import_raw(request, import_id):
    """Display the XML of the imported document."""
    import_object = get_object_or_404(RegisteredImport, pk=import_id)
    return HttpResponse(import_object.raw_xml, content_type='text/xml')


@login_required()
def display_import_processed(request, import_id):
    """Display the XML of the imported document, annotated with the
    IDs of the created objects."""
    import_object = get_object_or_404(RegisteredImport, pk=import_id)
    return HttpResponse(import_object.processed_xml, content_type='text/xml')


@login_required()
def import_eatsml(request):
    """Import POSTed EATSML file."""
    if request.method == 'POST':
        import_form = ImportForm(request.POST, request.FILES)
        if import_form.is_valid():
            eatsml_file = StringIO()
            for chunk in request.FILES['import_file'].chunks():
                eatsml_file.write(chunk)
            eatsml_file.seek(0)
            try:
                raw_root, processed_root = Importer(request.user).import_file(
                    eatsml_file)
            except Exception as e:
                transaction.rollback()
                response = render(request,
                                  '500.html', {'message': e})
                response.status_code = 500
                return response
            description = import_form.cleaned_data['description']
            raw_xml = etree.tostring(raw_root, encoding='utf-8',
                                     pretty_print=True)
            processed_xml = etree.tostring(processed_root, encoding='utf-8',
                                           pretty_print=True)
            registered_import = RegisteredImport(importer=request.user,
                                                 description=description,
                                                 raw_xml=raw_xml,
                                                 processed_xml=processed_xml)
            registered_import.save()
            transaction.commit()
            return HttpResponseRedirect(reverse(
                display_import, kwargs={'import_id': registered_import.id}))
    else:
        import_form = ImportForm()
    import_list = RegisteredImport.objects.values(
        'id', 'importer__username', 'description', 'import_date')
    paginator = Paginator(import_list, 100)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        imports = paginator.page(page)
    except (EmptyPage, InvalidPage):
        imports = paginator.page(paginator.num_pages)
    context_data = {'form': import_form, 'imports': imports}
    return render(request, 'eats/edit/import.html', context_data)


def export_eatsml(request, authority_id=None):
    if authority_id is None:
        entity_objects = Entity.objects.all()
    else:
        entity_objects = Entity.objects.filter(
            assertions__authority_record__authority=authority_id).distinct()
    try:
        eatsml_root = Exporter().export_entities(entity_objects)
    except Exception as e:
        response = render(request, '500.html', {'message': str(e)})
        response.status_code = 500
        return response
    xml = etree.tostring(eatsml_root, encoding='utf-8', pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


@login_required()
def export_base_eatsml(request):
    """Export the infrastructure elements of the EATS server."""
    exporter = Exporter()
    exporter.set_user(request.user)
    try:
        eatsml_root = exporter.export_infrastructure(limited=True,
                                                     annotated=True)
    except Exception as e:
        response = render(request, '500.html', {'message': str(e)})
        response.status_code = 500
        return response
    xml = etree.tostring(eatsml_root, encoding='utf-8', pretty_print=True)
    return HttpResponse(xml, content_type='text/xml')


@login_required()
def export_xslt_list(request):
    """Export the list of XSLTs required for the EATSML client interface."""
    try:
        xml = open(os.path.join(app_path, 'eatsml/xslt_list.xml'))
    except IOError:
        raise Http404
    return HttpResponse(xml, content_type='text/xml')


@login_required()
def export_xslt(request, xslt):
    """Export the XSLT xslt."""
    try:
        xml = open(os.path.join(app_path, 'eatsml/%s.xsl' % xslt))
    except IOError:
        raise Http404
    return HttpResponse(xml, content_type='text/xml')


@user_passes_test(lambda u: u.is_superuser)
def update_name_search_forms(request):
    """Update the search forms for all of the names in the system."""
    names = Name.objects.all()
    for name in names:
        name.save()
    context_data = {'count': names.count()}
    return render(request, 'eats/edit/name_search_form_update.html',
                  context_data)
