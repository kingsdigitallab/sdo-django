"""Definitions for the edit form and widget classes."""

from django import forms
from django.forms.utils import ErrorDict
from eats.models import (
    Authority, AuthorityRecord, Date, Entity, EntityNote, EntityReference,
    EntityRelationship, EntityRelationshipNote, EntityType, Existence,
    GenericProperty, Name, NameNote, NamePart, NameRelationship,
    PropertyAssertion)
from eats.forms.main import SearchForm


class GenericFormSet (object):

    def __init__(self, assertion_type, form_class, authority_records):
        self.assertion_type = assertion_type
        self.form_class = form_class
        self.authority_records = authority_records
        self.is_model_form = issubclass(self.form_class, forms.ModelForm)
        self.forms = {'all': []}
        self.bound_instance_forms = []
        self.bound_new_forms = []
        self.bound_inline_instance_forms = []
        self.bound_inline_new_forms = []

    def create_forms(self, assertions, extra_data,
                     post_data, new_forms, inline):
        """Create the instance and new forms."""
        # Instance forms.
        for assertion in assertions:
            form = self._create_instance_form(assertion, extra_data.copy(),
                                              post_data)
            self.forms['all'].append(form)
            if form.is_bound:
                self.bound_instance_forms.append(form)
            # Create instance and new forms for inline objects.
            if inline:
                eats_property = getattr(assertion, self.assertion_type)
                key = eats_property.id
                keyed_forms = self.forms.get(key, [])
                inline_name = inline['related_name']
                inline_form_class = inline['form_class']
                # Instance forms.
                inline_objects = getattr(eats_property, inline_name).all()
                for inline_object in inline_objects:
                    form = self._create_inline_instance_form(
                        inline_name, inline_object, inline_form_class,
                        post_data)
                    keyed_forms.append(form)
                    if form.is_bound:
                        self.bound_inline_instance_forms.append(form)
                # New forms.
                initial_data = {self.assertion_type: eats_property.id}
                for i in range(inline['new_forms']):
                    form = self._create_inline_new_form(
                        key, inline_name, inline_form_class, post_data, i,
                        initial_data)
                    keyed_forms.append(form)
                    if form.is_bound and form.has_post_data():
                        self.bound_inline_new_forms.append(form)
                self.forms[key] = keyed_forms
        # New forms.
        for i in range(new_forms):
            form = self._create_new_form(extra_data.copy(), post_data, i)
            self.forms['all'].append(form)
            # A new form should not be considered bound unless the
            # data passed to it is relevant to that form. This avoids
            # validation errors arising when a form is submitted that
            # does not include data for the new forms.
            if form.is_bound and form.has_post_data():
                self.bound_new_forms.append(form)

    def get_forms(self, key='all'):
        return self.forms.get(key, [])

    def get_bound_forms(self):
        return self.bound_instance_forms, self.bound_new_forms

    def get_bound_inline_forms(self):
        return self.bound_inline_instance_forms, self.bound_inline_new_forms

    def _create_instance_form(self, assertion, extra_data, post_data):
        """Return a form for the assertion."""
        eats_property = getattr(assertion, self.assertion_type)
        extra_data['assertion'] = assertion
        extra_data['property'] = eats_property
        initial_data = {'authority_record': assertion.authority_record.id,
                        'is_preferred': assertion.is_preferred}
        prefix = '%s_%d' % (self.assertion_type, eats_property.id)
        kw_args = {'initial': initial_data,
                   'prefix': prefix, 'data': post_data}
        if self.is_model_form:
            kw_args['instance'] = eats_property
        form = self.form_class(self.authority_records, extra_data, **kw_args)
        return form

    def _create_new_form(self, extra_data, post_data, count, initial=None):
        """Return a form for adding a new assertion, using the extra data."""
        prefix = '%s_new_%s' % (self.assertion_type, str(count))
        form = self.form_class(self.authority_records, extra_data,
                               prefix=prefix, data=post_data, initial=initial)
        form.is_new_form = True
        return form

    def _create_inline_instance_form(
            self, inline_name, instance, form_class, post_data):
        """Return a form for the inline instance."""
        prefix = '%s_%s_%d' % (self.assertion_type, inline_name, instance.id)
        form = form_class(instance=instance, prefix=prefix, data=post_data)
        return form

    def _create_inline_new_form(self, property_id, inline_name, form_class,
                                post_data, count, initial=None):
        """Return a form for adding a new inline object, using the extra
        data."""
        prefix = '%s_%s_%s_new_%s' % (self.assertion_type, str(
            property_id), inline_name, str(count))
        form = form_class(prefix=prefix, data=post_data, initial=initial)
        form.is_new_form = True
        return form


class NameRelationshipFormSet (GenericFormSet):

    def create_forms(self, assertions, extra_data, post_data, new_forms,
                     inlines):
        """Create the instance and new forms."""
        for assertion in assertions:
            key = assertion.name_relationship.name.id
            # Remove the current name from the list of possible
            # related names.
            extra_data['related_names'] = extra_data['names'].exclude(
                assertion=assertion)
            extra_data['name'] = Name.objects.filter(pk=key)
            form = self._create_instance_form(assertion, extra_data.copy(),
                                              post_data)
            keyed_forms = self.forms.get(key, [])
            keyed_forms.append(form)
            self.forms[key] = keyed_forms
            self.forms['all'].append(form)
            if form.is_bound:
                self.bound_instance_forms.append(form)
        for name in extra_data['names']:
            key = name.id
            keyed_forms = self.forms.get(key, [])
            extra_data['related_names'] = extra_data['names'].exclude(pk=key)
            extra_data['name'] = Name.objects.filter(pk=key)
            initial_data = {'name': key}
            for i in range(new_forms):
                form = self._create_new_form(extra_data.copy(), post_data,
                                             '%d_%d' % (key, i),
                                             initial=initial_data)
                keyed_forms.append(form)
                self.forms['all'].append(form)
                if form.is_bound and form.has_post_data():
                    self.bound_new_forms.append(form)
            self.forms[key] = keyed_forms


class NoteWidget (forms.Textarea):

    def __init__(self, *args, **kw_args):
        kw_args.setdefault('attrs', {}).update({'rows': '5'})
        super(NoteWidget, self).__init__(*args, **kw_args)


class EditForm (forms.ModelForm):

    # Fields which should be ignored when determining whether data has
    # been supplied for a form.
    unchecked_fields = ['authority_record']

    def __init__(self, *args, **kw_args):
        super(EditForm, self).__init__(*args, **kw_args)
        # Boolean indicator of whether this form is for creating a new
        # object (True) or for an existing object (False).
        self.is_new_form = False

    def clean(self):
        """Override the clean method, in order to ensure that forms for
        creating new objects are not marked as invalid if there is no
        data relevant to them."""
        if self.is_new_form and not self.has_post_data():
            self._errors = ErrorDict()
            self.cleaned_data = {}
        else:
            self.cleaned_data = super(EditForm, self).clean()
        return self.cleaned_data

    def has_post_data(self):
        """Return True if the form's data includes data keyed to fields in the
        form.

        Used to determine whether a form which has no instance (ie, a
        form for adding a new object) should be validated or not.

        """
        for name, field in list(self.fields.items()):
            if name not in self.unchecked_fields:
                if self.data.get(self.add_prefix(name)):
                    return True
        return False


class PropertyForm (EditForm):

    """Class for forms that represent a property, and therefore also
    covers the assertion that goes with it."""

    # Fields relating to the PropertyAssertion that goes with this
    # property.
    authority_record = forms.ModelChoiceField(
        AuthorityRecord.objects.all(), required=True, error_messages={
            'required': 'An authority record must be selected'},
        widget=forms.Select(
            attrs={'onchange': 'limit_type_selects(); return true;'}))
    is_preferred = forms.BooleanField(required=False)

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(PropertyForm, self).__init__(*args, **kw_args)
        self.assertion = extra_data.get('assertion')
        self.property = extra_data.get('property')
        self.fields['authority_record'].queryset = authority_records
        self.fields['authority_record'].choices = create_choice_list(
            authority_records, True)


class InlinePropertyForm (PropertyForm):

    """Class for forms that represent a property and which are edited
    inline as part of another form. Such forms allow for the deletion
    of the property."""

    delete = forms.BooleanField(required=False)


class AuthorityRecordCreateForm (forms.ModelForm):

    authority = forms.ModelChoiceField(
        Authority.objects.all(), required=True, widget=forms.Select(
            attrs={'onchange': 'display_authority_data(this); return true;'}))

    def __init__(self, authorities, *args, **kw_args):
        super(AuthorityRecordCreateForm, self).__init__(*args, **kw_args)
        self.fields['authority'].queryset = authorities
        self.fields['authority'].choices = create_choice_list(
            authorities, True)

    def clean(self):
        # Require that at least one of record ID and record URL
        # is filled in.
        self.cleaned_data = super(AuthorityRecordCreateForm, self).clean()
        if not self.errors and self.cleaned_data:
            record_id = self.cleaned_data['authority_system_id']
            record_url = self.cleaned_data['authority_system_url']
            if not (record_id or record_url):
                raise forms.ValidationError(
                    'You must fill in at least one of the record ID and '
                    'record URL fields')
        return self.cleaned_data

    class Meta:
        model = AuthorityRecord
        fields = '__all__'


class AuthorityRecordSearchForm (forms.Form):

    authority_record_id_widget_id = forms.CharField(widget=forms.HiddenInput)
    authority_record_name_widget_id = forms.CharField(widget=forms.HiddenInput)
    search_authority = forms.ChoiceField(choices=[[]], label='Authority')
    search_record_id = forms.CharField(
        max_length=200, required=False, label='Record ID')
    search_record_url = forms.CharField(
        max_length=400, required=False, label='Record URL')

    def __init__(self, authorities, *args, **kw_args):
        super(AuthorityRecordSearchForm, self).__init__(*args, **kw_args)
        self.fields['search_authority'].queryset = authorities
        self.fields['search_authority'].choices = create_choice_list(
            authorities, True)

    def clean(self):
        # Require that at least one of record ID and record URL
        # is filled in.
        if not self.errors and self.cleaned_data:
            record_id = self.cleaned_data['search_record_id']
            record_url = self.cleaned_data['search_record_url']
            if not (record_id or record_url):
                raise forms.ValidationError(
                    'You must fill in at least one of the record ID and '
                    'record URL fields')
        return self.cleaned_data


class DateForm (forms.ModelForm):

    start_terminus_post = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    start_date = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    start_terminus_ante = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    end_terminus_post = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    end_date = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    end_terminus_ante = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    point_terminus_post = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    point_date = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    point_terminus_ante = forms.CharField(widget=forms.TextInput(
        attrs={'onchange': 'update_normalised_date(this.id)'}), required=False)
    note = forms.CharField(widget=NoteWidget, required=False)

    def clean(self):
        self.cleaned_data = super(DateForm, self).clean()
        if not self.errors and self.cleaned_data:
            if not (self.cleaned_data['start_date'] or  # noqa
                    self.cleaned_data['end_date'] or  # noqa
                    self.cleaned_data['point_date'] or  # noqa
                    self.cleaned_data['start_terminus_post'] or  # noqa
                    self.cleaned_data['start_terminus_ante'] or  # noqa
                    self.cleaned_data['end_terminus_post'] or  # noqa
                    self.cleaned_data['end_terminus_ante'] or  # noqa
                    self.cleaned_data['point_terminus_post'] or  # noqa
                    self.cleaned_data['point_terminus_ante']):
                message = 'The date must have some date part set'
                raise forms.ValidationError(message)
        return self.cleaned_data

    class Meta:
        model = Date
        fields = '__all__'


class EntityTypeForm (InlinePropertyForm):

    property_field = 'entity_type'

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(EntityTypeForm, self).__init__(
            authority_records, extra_data, *args, **kw_args)
        entity_types = extra_data.get('entity_types')
        self.fields['entity_type'].queryset = entity_types
        self.fields['entity_type'].choices = create_choice_list(entity_types)

    def clean(self):
        # Need validation to check that the entity type specified is
        # associated with the same authority as the authority record
        # selected.
        self.cleaned_data = super(EntityTypeForm, self).clean()
        if not self.errors and self.cleaned_data:
            entity_type_authority = self.cleaned_data['entity_type'].authority
            authority_record = self.cleaned_data['authority_record']
            if entity_type_authority != authority_record.authority:
                raise forms.ValidationError(
                    'The entity type must be associated with the same '
                    'authority as the authority record.')
        return self.cleaned_data

    class Meta:
        model = EntityType
        fields = '__all__'


class ExistenceForm (forms.ModelForm):

    """Class for the inline forms for editing existences.

    This class does not inherit from InlinePropertyForm because it is
    in the unique position of being the source of possible authority
    records, rather than dependant on them.

    """
    # Fields which should be ignored when determining whether data has
    # been supplied for a form.
    unchecked_fields = []
    property_field = 'existence'
    delete = forms.BooleanField(required=False)
    authority_record = forms.ModelChoiceField(
        AuthorityRecord.objects.all(), widget=forms.HiddenInput)
    authority_record_name = forms.CharField(widget=forms.TextInput(
        attrs={'disabled': 'disabled'}), required=False)
    is_preferred = forms.BooleanField(required=False)

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(ExistenceForm, self).__init__(*args, **kw_args)
        self.assertion = extra_data.get('assertion')
        self.property = extra_data.get('property')
        self.is_new_form = False
        # Sneakily add an authority record name. The conditional
        # checks kw_args and not self.instance since self.instance
        # will be an instance even if no instance was passed in to the
        # constructor.
        if kw_args.get('instance'):
            try:
                authority_record_name = str(
                    self.instance.assertion.authority_record)
            except BaseException:
                authority_record_name = '[invalid authority record]'
            self.initial['authority_record_name'] = authority_record_name

    def has_post_data(self):
        """Return True if the form's data includes data keyed to fields in the
        form.

        Used to determine whether a form which has no instance (ie, a
        form for adding a new object) should be validated or not.

        """
        for name, field in list(self.fields.items()):
            if name not in self.unchecked_fields:
                if self.data.get(self.add_prefix(name)):
                    return True
        return False

    def clean(self):
        self.cleaned_data = super(ExistenceForm, self).clean()
        if self.cleaned_data.get('delete'):
            # An Existence may not be deleted if its associated
            # AuthorityRecord is associated with any other properties
            # for the entity.
            entity = self.assertion.entity
            authority_record = self.assertion.authority_record
            has_dependent_records = PropertyAssertion.objects.filter(
                entity=entity, authority_record=authority_record,
                existence__isnull=True)
            if has_dependent_records:
                raise forms.ValidationError(
                    'An existence may not be deleted if its authority record '
                    'is associated with other properties.')
        return self.cleaned_data

    class Meta:
        model = Existence
        fields = '__all__'


class NameForm (PropertyForm):

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(NameForm, self).__init__(
            authority_records, extra_data, *args, **kw_args)
        name_types = extra_data.get('name_types')
        self.fields['name_type'].queryset = name_types
        name_type_choices = extra_data.get('name_type_choices', name_types)
        self.fields['name_type'].choices = create_choice_list(
            name_type_choices, True)

    class Meta:
        model = Name
        fields = '__all__'


class NamePartForm (EditForm):

    delete = forms.BooleanField(required=False)
    name = forms.ModelChoiceField(Name.objects.all(), widget=forms.HiddenInput)
    unchecked_fields = ['name']

    def __init__(self, extra_data, *args, **kw_args):
        super(NamePartForm, self).__init__(*args, **kw_args)
        name_part_types = extra_data.get('name_part_types')
        self.fields['name_part_type'].queryset = name_part_types
        name_part_type_choices = extra_data.get(
            'name_part_type_choices', name_part_types)
        self.fields['name_part_type'].choices = create_choice_list(
            name_part_type_choices)
        self.fields['name_part_type'].error_messages['required'] = \
            'The type may not be empty'
        self.fields['name_part'].error_messages['required'] = \
            'The name part may not be empty'

    class Meta:
        model = NamePart
        fields = '__all__'


class NameNoteForm (EditForm):

    delete = forms.BooleanField(required=False)
    name = forms.ModelChoiceField(Name.objects.all(), widget=forms.HiddenInput)
    note = forms.CharField(widget=NoteWidget, required=False)
    unchecked_fields = ['name']

    def __init__(self, *args, **kw_args):
        super(NameNoteForm, self).__init__(*args, **kw_args)
        self.fields['note'].error_messages['required'] = \
            'The note may not be empty'

    class Meta:
        model = NameNote
        fields = '__all__'


class NameRelationshipForm (InlinePropertyForm):

    name = forms.ModelChoiceField(Name.objects.all(), widget=forms.HiddenInput)
    property_field = 'name_relationship'
    unchecked_fields = ['authority_record', 'name']

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(NameRelationshipForm, self).__init__(
            authority_records, extra_data, *args, **kw_args)
        name = extra_data.get('name')
        self.fields['name'].queryset = name
        self.fields['name'].choices = create_choice_list(name)
        related_names = extra_data.get('related_names')
        self.fields['related_name'].queryset = related_names
        self.fields['related_name'].choices = create_choice_list(related_names)
        name_relationship_types = extra_data.get('name_relationship_types')
        self.fields['name_relationship_type'].queryset = \
            name_relationship_types
        self.fields['name_relationship_type'].choices = create_choice_list(
            name_relationship_types)

    def clean(self):
        # Need validation to check that the relationship type
        # specified is associated with the same authority as the
        # authority record selected. Similarly, that the name's
        # authority matches the related name's authority.
        self.cleaned_data = super(NameRelationshipForm, self).clean()
        if not self.errors and self.cleaned_data:
            error_messages = []
            relationship_type_authority = self.cleaned_data[
                'name_relationship_type'].authority
            related_name_authority = self.cleaned_data[
                'related_name'].get_authority()
            name_authority = self.cleaned_data['authority_record'].authority
            if relationship_type_authority != name_authority:
                error_messages.append(
                    'The name relationship type must be associated with the '
                    'same authority as the authority record.')
            if name_authority != related_name_authority:
                error_messages.append(
                    'The related name must be associated with the same '
                    'authority as the name.')
            if error_messages:
                raise forms.ValidationError(' '.join(error_messages))
        return self.cleaned_data

    class Meta:
        model = NameRelationship
        fields = '__all__'


class EntityRelationshipForm (InlinePropertyForm):

    property_field = 'entity_relationship'
    related_entity = forms.ModelChoiceField(
        Entity.objects.all(), widget=forms.HiddenInput)
    related_entity_name = forms.CharField(widget=forms.TextInput(
        attrs={'disabled': 'disabled'}), required=False)
    unchecked_fields = ['authority_record', 'related_entity_name']

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(EntityRelationshipForm, self).__init__(
            authority_records, extra_data, *args, **kw_args)
        entity_relationship_types = extra_data.get('entity_relationship_types')
        self.fields['entity_relationship_type'].queryset = \
            entity_relationship_types
        self.fields['entity_relationship_type'].choices = create_choice_list(
            entity_relationship_types)
        self.fields['entity_relationship_type'].error_messages = {
            'required': 'A relationship type must be selected'}
        # Sneakily add a related entity name. The conditional checks
        # kw_args and not self.instance since self.instance will be an
        # instance even if no instance was passed in to the
        # constructor.
        if kw_args.get('instance'):
            try:
                related_entity = self.instance.related_entity
                related_entity_name = related_entity.get_single_name(
                    extra_data.get('user_prefs'))
            except BaseException:
                related_entity_name = '[invalid entity]'
            self.initial['related_entity_name'] = related_entity_name

    def clean(self):
        # Need validation to check that the entity relationship type
        # specified is associated with the same authority as the
        # authority record selected.
        self.cleaned_data = super(EntityRelationshipForm, self).clean()
        if not self.errors and self.cleaned_data:
            entity_relationship_type_authority = self.cleaned_data[
                'entity_relationship_type'].authority
            authority_record = self.cleaned_data['authority_record']
            if entity_relationship_type_authority != \
               authority_record.authority:
                raise forms.ValidationError(
                    'The entity relationship must be associated with the '
                    'same authority as the authority record.')
        return self.cleaned_data

    class Meta:
        model = EntityRelationship
        fields = '__all__'


class EntityRelationshipNoteForm (EditForm):

    delete = forms.BooleanField(required=False)
    entity_relationship = forms.ModelChoiceField(
        EntityRelationship.objects.all(), widget=forms.HiddenInput)
    note = forms.CharField(widget=NoteWidget, required=False)
    unchecked_fields = ['entity_relationship']

    class Meta:
        model = EntityRelationshipNote
        fields = '__all__'


class EntityNoteForm (InlinePropertyForm):

    note = forms.CharField(widget=NoteWidget)
    property_field = 'note'

    def __init__(self, authority_records, extra_data, *args, **kw_args):
        super(EntityNoteForm, self).__init__(
            authority_records, extra_data, *args, **kw_args)
        self.fields['note'].error_messages['required'] = \
            'The note may not be empty'

    class Meta:
        model = EntityNote
        fields = '__all__'


class ReferenceForm (InlinePropertyForm):

    property_field = 'reference'

    class Meta:
        model = EntityReference
        fields = '__all__'


class GenericForm (EditForm):

    class Meta:
        model = GenericProperty
        fields = '__all__'


class EntitySelectorForm (SearchForm):

    entity_id_widget_id = forms.CharField(widget=forms.HiddenInput)
    entity_name_widget_id = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, authorities, *args, **kw_args):
        super(EntitySelectorForm, self).__init__(*args, **kw_args)
        self.fields['authority'].queryset = authorities
        self.fields['authority'].choices = create_choice_list(
            authorities, True)


class ImportForm (forms.Form):

    import_file = forms.FileField()
    description = forms.CharField(max_length=200)


def create_choice_list(qs, default=False):
    """Return a list of 2-tuples from the records in the QuerySet.

    If there is a single record and default is True, do not provide an
    empty option.

    """
    choices = [(record.id, str(record)) for record in qs]
    if not (qs.count() == 1 and default):
        choices = [('', '----------')] + choices
    return choices
