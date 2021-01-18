"""Model definitions for EATS."""

from datetime import datetime
from django import forms
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.conf import settings

import eats.names as namehandler


def get_default_object(model, authority=None):
    """Return the system-wide default object for the model.

    Arguments:
    - `model`: model class
    - `authority`: optional authority object

    Each authority has its own set of defaults; if `authority` is not
    provided and `model` is not Authority, the default authority will
    be found and then used to get the default for `model`.

    """
    if model == Authority:
        try:
            default = Authority.objects.get(is_default=True)
        except Authority.DoesNotExist:
            try:
                default = Authority.objects.all()[0]
            except IndexError:
                raise Authority.DoesNotExist(
                    'No authority exists in the system, making it impossible '
                    'to proceed.')
        except Authority.MultipleObjectsReturned:
            # This should only occur if the database data has been
            # changed outside of this app. Separating this case out
            # (rather than just setting default to the first object in
            # a filter query) allows for easy adding of logging or
            # other error handling in this case.
            default = Authority.objects.filter(is_default=True)[0]
    else:
        if authority is None:
            authority = get_default_object(Authority)
        default = authority.get_default_object(model)
    return default


def get_new_authority_record_details(authority):
    """Return a dictionary of ID and URL details (the actual values and
    whether they are complete or not) for a new authority record
    linked to authority.

    Arguments:
    authority -- Authority object

    """
    # Different authorities will have different algorithms for
    # determining new details, so use the appropriate function for
    # each.
    try:
        functions = getattr(settings, 'EATS_AUTHORITY_RECORD_FUNCTIONS')
        function_name = functions[authority.authority]
        if type(function_name) in (type(''), type('')):
            function = _import_function(function_name)
        else:
            function = function_name
    except (AttributeError, KeyError):
        function = default_get_new_authority_record_details
    return function(AuthorityRecord, authority)


def _import_function(function_name):
    """Import a function by name."""
    # QAZ: deal with the possible problems here, if there is no '.',
    # or no such module/function.
    split_index = function_name.rindex('.')
    module = function_name[:split_index]
    function = function_name[split_index + 1:]
    temp = __import__(module, globals(), locals(), [function], -1)
    return getattr(temp, function)


def default_get_new_authority_record_details(model, authority):
    """Return a tuple of id and URL for a new authority record. This
    function provides a default implementation.

    Arguments:
    model -- AuthorityRecord model class
    authority -- Authority object

    """
    prefix = 'entity-'
    try:
        last_id = model.objects.filter(authority=authority).order_by(
            '-authority_system_id')[0].authority_system_id
    except IndexError:
        last_id = '%s000000' % prefix
    number = int(last_id[-6:]) + 1
    id = '%s%06d' % (prefix, number)
    # QAZ: add a sanity check that the generated ID does not already
    # exist, due to using multiple schemes over time for ID
    # generation.
    data = {'id': id, 'is_complete_id': True,
            'url': '%s.html' % (id), 'is_complete_url': False}
    return data


class Authority (models.Model):
    """An authority is an individual, organisation or group that
    asserts some information about entities. It is not necessarily the
    case that the authority is the source of this information."""
    # Name of the authority
    authority = models.CharField(max_length=100, unique=True)
    abbreviated_name = models.CharField(max_length=15, blank=True)
    # The base ID for this authority's records. This is concatenated
    # with AuthorityRecord.authority_system_id to form a full ID for a
    # record. Useful in the case where the ID is a URI.
    base_id = models.CharField(max_length=255, blank=True)
    # The base URL for this authority's records. This is concatenated
    # with AuthorityRecord.authority_system_url to form a full URL for
    # a record.
    base_url = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField()
    default_calendar = models.ForeignKey('Calendar', on_delete=models.CASCADE)
    default_date_period = models.ForeignKey(
        'DatePeriod', on_delete=models.CASCADE)
    default_date_type = models.ForeignKey('DateType', on_delete=models.CASCADE)
    default_language = models.ForeignKey('Language', on_delete=models.CASCADE)
    default_script = models.ForeignKey('Script', on_delete=models.CASCADE)
    # Possible link to an entity representing this authority.
    # entity = models.ForeignKey(Entity, null=True, blank=True, unique=True)
    last_modified = models.DateTimeField(auto_now=True)

    def get_short_name(self):
        """Return the short name of self."""
        return self.abbreviated_name or self.authority

    def get_default_object(self, model):
        """Return this authority's default `model` object."""
        if model == Calendar:
            default = self.default_calendar
        elif model == DatePeriod:
            default = self.default_date_period
        elif model == DateType:
            default = self.default_date_type
        elif model == Language:
            default = self.default_language
        elif model == NameType:
            try:
                default = self.nametype_set.get(is_default=True)
            except NameType.DoesNotExist:
                try:
                    default = self.nametype_set.all()[0]
                except IndexError:
                    raise NameType.DoesNotExist(
                        'No name types exist in the system, making it '
                        'impossible to proceed.')
            except NameType.MultipleObjectsReturned:
                # This should only occur if the database data has been
                # changed outside of this app. Separating this case
                # out (rather than just setting default to the first
                # object in a filter query) allows for easy adding of
                # logging or other error handling in this case.
                default = self.nametype_set.filter(is_default=True)[0]
        elif model == Script:
            default = self.default_script
        else:
            # QAZ: figure out proper error handling.
            raise Exception('Authority objects have no default %s object.'
                            % model._meta.object_name)
        return default

    def __str__(self):
        return self.authority

    class Meta:
        verbose_name_plural = 'Authorities'


class AuthorityRecord (models.Model):
    """A record associated with an authority that identifies a
    resource in that authority's system."""
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    authority_system_id = models.CharField(
        max_length=100, blank=True, verbose_name='record ID')
    is_complete_id = models.BooleanField('Is complete ID?', default=False)
    authority_system_url = models.CharField(
        max_length=255, blank=True, verbose_name='record URL')
    is_complete_url = models.BooleanField('Is complete URL?', default=False)
    last_modified = models.DateTimeField(auto_now=True)

    def get_id(self):
        """Return a full ID for this authority record."""
        prefix = ''
        if not(self.is_complete_id):
            prefix = self.authority.base_id
        system_id = '%s%s' % (prefix, self.authority_system_id)
        return system_id

    def get_url(self):
        """Return a full URL for this authority record."""
        prefix = ''
        if not(self.is_complete_url):
            # QAZ: does there need to be escaping of this at some
            # point? Can't do it here, since we don't know where it
            # will be rendered, but if it goes into HTML, it should
            # be.
            prefix = self.authority.base_url
        # This doesn't use a proper URL joining library because the
        # parts are not guaranteed to be complete units (eg,
        # http://www.example.com/prefix- + part).
        return '%s%s' % (prefix, self.authority_system_url)

    def get_entities(self):
        """Return a list of entities that have at least one property
        authorised by this record."""
        entities = Entity.objects.filter(
            assertions__authority_record=self).distinct()
        return entities

    def __str__(self):
        id = self.get_id()
        if not id:
            id = self.get_url()
        return '%s: %s' % (self.authority.get_short_name(), id)

    class Meta:
        unique_together = (('authority', 'authority_system_id',
                            'authority_system_url'),)


class Entity (models.Model):
    """EATS entities are anything about which some information is
    asserted by an authority."""
    last_modified = models.DateTimeField(auto_now=True)

    def get_absolute_url(self):
        return '/eats/{}'.format(self.id)

    def delete(self):
        """Override the default delete method to handle the deletion of all of
        the properties associated with the entity."""
        properties = []
        for klass in (EntityType, EntityRelationship, Name,
                      NameRelationship, EntityNote, EntityReference,
                      GenericProperty):
            properties.append(klass.objects.filter(assertion__entity=self))
        # Also delete those properties that are associated with other
        # entities but refer to self.
        properties.append(EntityRelationship.objects.filter(
            related_entity=self))
        # QAZ: This should not be necessary, since name relationship
        # are within names of the same entity.
        properties.append(NameRelationship.objects.filter(
            related_name__assertion__entity=self))
        # Delete Existences last, since other properties depend on them.
        properties.append(Existence.objects.filter(assertion__entity=self))
        for object_property in properties:
            object_property.delete()
        super(Entity, self).delete()

    def save(self, authority=None, create_existence=True, *args, **kwargs):
        """Override the default save method to allow for the automatic
        creation of auxiliary information when a new entity is added."""
        if self.id is None and create_existence:
            super(Entity, self).save(*args, **kwargs)
            # Create new PropertyAssertion, Existence and
            # AuthorityRecord records, and link them together and to
            # the new entity.
            existence = Existence()
            existence.save()
            record_data = get_new_authority_record_details(authority)
            authority_record = AuthorityRecord(
                authority=authority, authority_system_id=record_data['id'],
                is_complete_id=record_data['is_complete_id'],
                authority_system_url=record_data['url'],
                is_complete_url=record_data['is_complete_url'])
            authority_record.save()
            assertion = PropertyAssertion(
                entity=self, authority_record=authority_record,
                existence=existence, is_preferred=True)
            assertion.save()
        else:
            super(Entity, self).save(*args, **kwargs)

    def get_authority_records(self):
        """Return a QuerySet of AuthorityRecord objects for the Existence
        records of the entity."""
        records = AuthorityRecord.objects.filter(assertions__entity=self)\
            .filter(assertions__existence__isnull=False).distinct()
        return records

    def get_preferred_authority_records(self, user_prefs=None):
        """Return a QuerySet of AuthorityRecord objects for the existence
        records of the entity that match the user preferences. The
        system default is used if a parameter is not supplied."""
        user_prefs = user_prefs or {}
        authority = user_prefs.get('authority', get_default_object(Authority))
        records = self.get_authority_records().filter(authority=authority)
        return records

    def get_entity_types(self):
        """Return a QuerySet of EntityType objects for the entity."""
        return EntityType.objects.filter(assertion__entity=self)

    def get_preferred_entity_types(self, user_prefs=None):
        """Return a QuerySet of EntityType objects for the entity that match
        the user preferences."""
        user_prefs = user_prefs or {}
        authority = user_prefs.get('authority', get_default_object(Authority))
        return EntityType.objects.filter(
            assertion__authority_record__authority=authority)\
            .filter(assertion__entity=self)\
            .order_by('-assertion__is_preferred')

    def get_notes(self, note_filter=None):
        """Return a QuerySet of EntityNote objects for this entity, optionally
        filtered by note_filter."""
        notes = EntityNote.objects.filter(assertion__entity=self)
        if note_filter:
            notes = notes.filter(note_filter)
        return notes

    def get_internal_notes(self):
        """Return a QuerySet of EntityNote objects for the entity that are
        internal."""
        note_filter = Q(is_internal=True)
        return self.get_notes(note_filter)

    def get_external_notes(self):
        """Return a QuerySet of EntityNote objects for the entity that are
        external."""
        note_filter = Q(is_internal=False)
        return self.get_notes(note_filter)

    def get_references(self):
        """Return a QuerySet of EntityReference objects for the entity."""
        return EntityReference.objects.filter(assertion__entity=self)

    def get_dates(self):
        """Return a QuerySet of Existence Date objects for the entity."""
        return Date.objects.filter(assertion__entity=self)\
            .filter(assertion__existence__isnull=False)

    def get_names(self):
        """Return a QuerySet of all of the names of this entity."""
        return Name.objects.select_related()\
            .filter(assertion__entity=self)\
            .order_by('-assertion__is_preferred')

    def get_preferred_authority_names(self, user_prefs=None):
        """Return a QuerySet of Name objects for the entity that match the
        user's preferred authority. The system default is used if a
        parameter is not supplied.

        Arguments:
        user_prefs -- dictionary containing the user's preferences

        """
        user_prefs = user_prefs or {}
        authority = user_prefs.get('authority', get_default_object(Authority))
        authority_filter = Q(assertion__authority_record__authority=authority)
        return self.get_names().filter(authority_filter)

    def get_non_preferred_authority_names(self, user_prefs=None):
        """Return a QuerySet of Name objects for the entity that do not match
        the user's preferred authority.

        Arguments:
        user_prefs -- dictionary containing the user's preferences

        """
        user_prefs = user_prefs or {}
        names = self.get_names()
        authority = user_prefs.get('authority', get_default_object(Authority))
        authority_filter = Q(assertion__authority_record__authority=authority)
        return names.exclude(authority_filter)\
            .order_by('assertion__authority_record__authority__authority')

    def get_single_name_object(self, user_prefs=None):
        """Return a name object, trying to accomodate user_prefs but
        falling back where necessary. Returns None if no names are
        found.

        Arguments:
        user_prefs -- dictionary containing the user's preferences

        """
        user_prefs = user_prefs or {}
        authority = user_prefs.get('authority', get_default_object(Authority))
        language = user_prefs.get('language', get_default_object(Language,
                                                                 authority))
        script = user_prefs.get('script', get_default_object(Script,
                                                             authority))
        authority_filter = Q(assertion__authority_record__authority=authority)
        language_filter = Q(language=language)
        script_filter = Q(script=script)
        # All names.
        names = self.get_names()
        # Authorised names.
        authorised_names = names.filter(authority_filter)
        if not authorised_names:
            authorised_names = names
        # Authorised names in language.
        language_names = authorised_names.filter(language_filter)
        if not language_names:
            language_names = authorised_names
        # Authorised names in language in script.
        script_names = language_names.filter(script_filter)
        if not script_names:
            script_names = language_names
        # Since we're going to return the string form of a single
        # name, get one which is preferred if possible.
        preferred_names = script_names.order_by('-assertion__is_preferred')
        try:
            return preferred_names[0]
        except IndexError:
            return None

    def get_single_name(self, user_prefs=None):
        """Return a single name string, trying to accomodate user_prefs but
        falling back where necessary.

        Arguments:
        user_prefs -- dictionary containing the user's preferences

        """
        preferred_name = self.get_single_name_object(user_prefs)
        if preferred_name is None:
            name_string = '[No name defined]'
        else:
            name_string = str(preferred_name)
        return name_string

    def get_relationships(self):
        """Return a QuerySet of EntityRelationships for this entity."""
        return EntityRelationship.objects.filter(assertion__entity=self)

    def get_reverse_relationships(self):
        """Return a QuerySet of EntityRelationships for this entity where the
        entity is the related entity."""
        return EntityRelationship.objects.filter(related_entity=self)

    def __str__(self):
        return str(self.get_single_name())

    class Meta:
        verbose_name_plural = 'Entities'


class EntityTypeList (models.Model):
    entity_type = models.CharField(max_length=30)
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('entity_type', 'authority'),)

    def __str__(self):
        return '%s (%s)' % (self.entity_type, self.authority.get_short_name())


class EntityType (models.Model):
    # This may look strange (why not just have the authority here
    # rather than in EntityTypeList?), but is necessary. Since
    # EntityType is linked to from PropertyAssertion, each record in
    # this table may be referenced only once.
    entity_type = models.ForeignKey(EntityTypeList, on_delete=models.CASCADE)

    def __str__(self):
        return self.entity_type.entity_type


class EntityNote (models.Model):
    note = models.TextField()
    is_internal = models.BooleanField('Internal?')

    def __str__(self):
        audience = 'external'
        if self.is_internal:
            audience = 'internal'
        return '[%s] %s' % (audience, self.note)


class EntityReference (models.Model):
    url = models.URLField()
    label = models.CharField(max_length=200)

    def __str__(self):
        return '%s at %s' % (self.label, self.url)


class EntityRelationshipType (models.Model):
    entity_relationship_type = models.CharField(max_length=100, unique=True)
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s (%s)' % (self.entity_relationship_type,
                            self.authority.get_short_name())


class EntityRelationshipTypeRelationship (models.Model):
    child_entity_relationship_type = models.ForeignKey(
        EntityRelationshipType, on_delete=models.CASCADE,
        related_name='entityrelationshiptype_child_set')
    parent_entity_relationship_type = models.ForeignKey(
        EntityRelationshipType, on_delete=models.CASCADE,
        related_name='entityrelationshiptype_parent_set')
    last_modified = models.DateTimeField(auto_now=True)


class EntityRelationship (models.Model):
    related_entity = models.ForeignKey(
        Entity, related_name='entity_relationships', on_delete=models.CASCADE)
    entity_relationship_type = models.ForeignKey(
        EntityRelationshipType, on_delete=models.CASCADE)

    def __str__(self):
        return 'This entity %s %s' % (self.entity_relationship_type,
                                      self.related_entity)


class EntityRelationshipNote (models.Model):
    entity_relationship = models.ForeignKey(
        EntityRelationship, related_name='notes', on_delete=models.CASCADE)
    note = models.TextField()
    is_internal = models.BooleanField('Internal?')

    def __str__(self):
        audience = 'external'
        if self.is_internal:
            audience = 'internal'
        return '[%s] %s' % (audience, self.note)


class Existence (models.Model):

    # Indeed, there are no fields defined here. Existence is a
    # property only so that it can be hung off PropertyAssertion (thus
    # allowing for dates, etc.).
    #
    # The system assumes that if there is a non-Existence property
    # associated with an AuthorityRecord, there is also an Existence
    # property associated with that same record.
    #
    # QAZ: this should be enforced at the editing level, at least - so
    # that the form only shows AuthorityRecords that are associated
    # with the entity via an Existence property in any of the drop
    # downs.

    def authority(self):
        """Return the authority associated with this existence."""
        return self.assertion.authority_record.authority

    def save(self, *args, **kwargs):
        # Only one Existence is allowed per Entity and AuthorityRecord
        # combination.
        # QAZ: Implement this.
        super(Existence, self).save(*args, **kwargs)

    def delete(self):
        # An existence may not be deleted if the associated
        # AuthorityRecord is associated with another property for the
        # entity.
        # QAZ: implement this.
        super(Existence, self).delete()

    def __str__(self):
        return '%s' % (self.assertion.entity)


class SystemNamePartType (models.Model):
    """Name part types that are used by the system in its code for
    assembling names. These are mapped to from the authority supplied
    NamePartType objects."""
    name_part_type = models.CharField(max_length=200, unique=True)
    description = models.TextField()

    def __str__(self):
        return '%s' % (self.name_part_type)


class Language (models.Model):
    language_code = models.CharField(max_length=3, unique=True)
    language_name = models.CharField(max_length=30, unique=True)
    # A mapping to allowable name part types for this language.
    system_name_part_types = models.ManyToManyField(SystemNamePartType,
                                                    related_name='languages')
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.language_name)

    class Meta:
        ordering = ['language_name']


class Script (models.Model):
    script_code = models.CharField(max_length=4, unique=True)
    script_name = models.CharField(max_length=30, unique=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.script_name)

    class Meta:
        ordering = ['script_name']


class NameType (models.Model):
    name_type = models.CharField(max_length=30)
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    is_default = models.BooleanField()
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('name_type', 'authority'),)

    def __str__(self):
        return self.name_type


class Name (models.Model):
    name_type = models.ForeignKey(NameType, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    script = models.ForeignKey(Script, on_delete=models.CASCADE)
    display_form = models.CharField(max_length=800, blank=True)

    def save(self, *args, **kwargs):
        self.display_form = namehandler.clean_name(self.display_form)
        super(Name, self).save(*args, **kwargs)
        self.update_search_names()

    def is_preferred(self):
        """Return Boolean of whether this name is preferred by the
        authority."""
        return self.assertion.is_preferred

    def get_display_form(self):
        """Return the display form of name."""
        if self.display_form:
            return self.display_form
        else:
            # Get the name composed from the name parts.
            name = self.get_assembled_form() or 'No derivable name exists'
            return name

    def get_assembled_form(self):
        """Return the assembled form of name. This is the form taken
        from automatically assembling the name parts, and is empty if
        there are none such."""
        return namehandler.assemble_name(self)

    def get_authority_record(self):
        """Return the AuthorityRecord object for name."""
        return self.assertion.authority_record

    def get_authority(self):
        """Return the Authority object for name."""
        return self.get_authority_record().authority

    def update_search_names(self):
        """Update the search names for name."""
        # If we are creating the name, we may not have a property
        # assertion yet, so do not update the search names.
        try:
            entity = self.assertion.entity
        except AttributeError:
            return
        language_code = self.language.language_code
        script_code = self.script.script_code
        # First delete any existing search names for this name.
        self.search_names.all().delete()
        # Create the new search names and insert them.
        search_forms = []
        if self.display_form:
            new_search_forms = namehandler.create_search_forms(
                self.display_form, language_code, script_code)
            search_forms.extend(new_search_forms)
        assembled_name = namehandler.assemble_name(self)
        new_search_forms = namehandler.create_search_forms(
            assembled_name, language_code, script_code)
        search_forms.extend(new_search_forms)
        for search_form in search_forms:
            search_name = SearchName(entity=entity, name=self,
                                     name_form=search_form)
            search_name.save()

    def __str__(self):
        return self.get_display_form()


class NameNote (models.Model):
    name = models.ForeignKey(Name, related_name='notes',
                             on_delete=models.CASCADE)
    note = models.TextField()
    is_internal = models.BooleanField('Internal?')

    def __str__(self):
        audience = 'external'
        if self.is_internal:
            audience = 'internal'
        return '[%s] %s' % (audience, self.note)


class NamePartType (models.Model):
    name_part_type = models.CharField(max_length=200)
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    system_name_part_type = models.ForeignKey(
        SystemNamePartType, on_delete=models.CASCADE)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_part_type

    class Meta:
        unique_together = (('name_part_type', 'authority'),)
        ordering = ['name_part_type']


class NamePart (models.Model):
    name = models.ForeignKey(
        Name, related_name='name_parts', on_delete=models.CASCADE)
    name_part_type = models.ForeignKey(NamePartType, on_delete=models.CASCADE)
    language = models.ForeignKey(
        Language, null=True, blank=True, on_delete=models.CASCADE)
    script = models.ForeignKey(
        Script, null=True, blank=True, on_delete=models.CASCADE)
    name_part = models.CharField(max_length=100)

    class Meta:
        unique_together = (('name', 'name_part_type'),)

    def save(self, *args, **kwargs):
        self.name_part = namehandler.clean_name(self.name_part)
        super(NamePart, self).save(*args, **kwargs)
        self.name.update_search_names()

    def delete(self):
        """Override delete method to regenerate the search names for this
        part's name."""
        name = self.name
        super(NamePart, self).delete()
        name.update_search_names()

    def to_dict(self):
        """Return a dictionary of name part details."""
        # Language and script are optional on name parts, so fall back
        # if they are not set. This should surely be done by Django...
        try:
            language = self.language.language_code
        except AttributeError:
            language = None
        try:
            script = self.script.script_code
        except AttributeError:
            script = None
        return {'type': self.name_part_type.name_part_type,
                'language_code': language,
                'script_code': script,
                'name_part': self.name_part}

    def __str__(self):
        return '%s (%s)' % (self.name_part,
                            self.name_part_type.name_part_type)


class NameRelationshipType (models.Model):
    name_relationship_type = models.CharField(max_length=30)
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('name_relationship_type', 'authority'),)

    def __str__(self):
        return '%s (%s)' % (self.name_relationship_type,
                            self.authority.get_short_name())


class NameRelationship (models.Model):
    name = models.ForeignKey(
        Name, related_name='name_start_relationships',
        on_delete=models.CASCADE)
    related_name = models.ForeignKey(
        Name, related_name='name_end_relationships', on_delete=models.CASCADE)
    name_relationship_type = models.ForeignKey(
        NameRelationshipType, on_delete=models.CASCADE)


class UserDefinedProperty (models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Properties'


class UserDefinedPropertyConstrainedValue (models.Model):
    property = models.ForeignKey(UserDefinedProperty, on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    def __str__(self):
        return self.value


class GenericProperty (models.Model):
    property = models.ForeignKey(UserDefinedProperty, on_delete=models.CASCADE)
    # QAZ: needs to be constrained to those values which have a
    # property_id matching property here.
    constrained_value = models.ForeignKey(
        UserDefinedPropertyConstrainedValue, on_delete=models.CASCADE)
    free_value = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Generic properties'


class PropertyAssertion (models.Model):
    entity = models.ForeignKey(
        Entity, related_name='assertions', on_delete=models.CASCADE)
    authority_record = models.ForeignKey(
        AuthorityRecord, related_name='assertions', on_delete=models.CASCADE)
    authority_record_checked = models.DateField(default=datetime.now,
                                                null=True, blank=True)
    existence = models.OneToOneField(
        Existence, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    entity_type = models.OneToOneField(
        EntityType, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    name = models.OneToOneField(
        Name, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    entity_relationship = models.OneToOneField(
        EntityRelationship, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    name_relationship = models.OneToOneField(
        NameRelationship, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    note = models.OneToOneField(
        EntityNote, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    reference = models.OneToOneField(
        EntityReference, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    generic_property = models.OneToOneField(
        GenericProperty, null=True, blank=True, related_name='assertion',
        on_delete=models.CASCADE)
    # is_preferred indicates that a property is a preferred one of its
    # type by the authority. Multiple properties of the same type may
    # be preferred. What this means is left to the client - for
    # example, two names may be preferred, distinguished by their
    # linguistic context.
    is_preferred = models.BooleanField('Is preferred property?')

    def get_type(self):
        """Return the name of the type of property being asserted."""
        if self.existence:
            klass = Existence
        elif self.entity_type:
            klass = EntityType
        elif self.name:
            klass = Name
        elif self.entity_relationship:
            klass = EntityRelationship
        elif self.name_relationship:
            klass = NameRelationship
        elif self.note:
            klass = EntityNote
        elif self.reference:
            klass = EntityReference
        elif self.generic_property:
            klass = GenericProperty
        return klass._meta.verbose_name

    def is_valid(self):
        validity_check = PropertyAssertionValidationForm(
            forms.model_to_dict(self))
        return validity_check.is_valid()

    def save(self, *args, **kwargs):
        # QAZ: Only one Existence is allowed per Entity and AuthorityRecord
        # combination - implement this.
        #
        # Model validation is what is required here; for now, fake it
        # as per http://www.pointy-stick.com/blog/2008/10/15/
        # django-tip-poor-mans-model-validation/
        #
        # Note that this does break in Django 1.2.
        if not self.is_valid():
            raise Exception('Attempting to save an invalid model.')
        return super(PropertyAssertion, self).save(*args, **kwargs)

    def __str__(self):
        return 'assertion that entity %s has %s property authorised in %s' \
            % (self.entity, self.get_type(), self.authority_record)


class PropertyAssertionValidationForm (forms.ModelForm):

    """Form for performing model validation for property assertions,
    until we get real model validation."""

    class Meta:
        model = PropertyAssertion
        fields = '__all__'

    def clean(self):
        authority_record = self.cleaned_data.get('authority_record')
        entity = self.cleaned_data.get('entity')
        if not self.cleaned_data.get('existence'):
            existences = Existence.objects.filter(
                assertion__entity=entity,
                assertion__authority_record=authority_record)
            if not existences.count():
                raise forms.ValidationError(
                    'an existence property assertion associated with this '
                    'authority record must already exist')


class DatePeriod (models.Model):
    date_period = models.CharField(
        max_length=40, verbose_name='Period covered')
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.date_period


class Calendar (models.Model):
    calendar = models.CharField(max_length=100)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.calendar


class DateType (models.Model):
    date_type = models.CharField(max_length=100)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.date_type


class Date (models.Model):
    assertion = models.ForeignKey(
        PropertyAssertion, related_name='dates', on_delete=models.CASCADE)
    date_period = models.ForeignKey(DatePeriod, on_delete=models.CASCADE)
    start_terminus_post = models.CharField('Date', max_length=100, blank=True)
    start_terminus_post_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='start_terminus_post_calendar_set', null=True,
        on_delete=models.CASCADE)
    start_terminus_post_normalised = models.CharField(
        'Normalised form', max_length=100, blank=True)
    start_terminus_post_type = models.ForeignKey(
        DateType, verbose_name='Type',
        related_name='start_terminus_post_type_set', null=True,
        on_delete=models.CASCADE)
    start_terminus_post_confident = models.BooleanField(
        'Confident', default=True)
    start_date = models.CharField('Date', max_length=100, blank=True)
    start_date_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='start_date_calendar_set', null=True,
        on_delete=models.CASCADE)
    start_date_normalised = models.CharField(
        'Normalised form', max_length=100, blank=True)
    start_date_type = models.ForeignKey(
        DateType, verbose_name='Type', related_name='start_date_type_set',
        null=True, on_delete=models.CASCADE)
    start_date_confident = models.BooleanField(
        'Confident', default=True)
    start_terminus_ante = models.CharField('Date', max_length=100, blank=True)
    start_terminus_ante_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='start_terminus_ante_calendar_set', null=True,
        on_delete=models.CASCADE)
    start_terminus_ante_normalised = models.CharField(
        'Normalised form', max_length=100, null=True, blank=True)
    start_terminus_ante_type = models.ForeignKey(
        DateType, verbose_name='Type',
        related_name='start_terminus_ante_type_set', null=True,
        on_delete=models.CASCADE)
    start_terminus_ante_confident = models.BooleanField(
        'Confident', default=True)
    point_terminus_post = models.CharField('Date', max_length=100, blank=True)
    point_terminus_post_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='point_terminus_post_calendar_set', null=True,
        on_delete=models.CASCADE)
    point_terminus_post_normalised = models.CharField(
        'Normalised form', max_length=100, blank=True)
    point_terminus_post_type = models.ForeignKey(
        DateType, verbose_name='Type',
        related_name='point_terminus_post_type_set', null=True,
        on_delete=models.CASCADE)
    point_terminus_post_confident = models.BooleanField(
        'Confident', default=True)
    point_date = models.CharField('Date', max_length=100, blank=True)
    point_date_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='point_date_calendar_set', null=True,
        on_delete=models.CASCADE)
    point_date_normalised = models.CharField('Normalised form', max_length=100,
                                             blank=True)
    point_date_type = models.ForeignKey(DateType, verbose_name='Type',
                                        related_name='point_date_type_set',
                                        null=True, on_delete=models.CASCADE)
    point_date_confident = models.BooleanField('Confident', default=True)
    point_terminus_ante = models.CharField('Date', max_length=100, blank=True)
    point_terminus_ante_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='point_terminus_ante_calendar_set', null=True,
        on_delete=models.CASCADE)
    point_terminus_ante_normalised = models.CharField(
        'Normalised form', max_length=100, null=True, blank=True)
    point_terminus_ante_type = models.ForeignKey(
        DateType, verbose_name='Type',
        related_name='point_terminus_ante_type_set', null=True,
        on_delete=models.CASCADE)
    point_terminus_ante_confident = models.BooleanField(
        'Confident', default=True)
    end_terminus_post = models.CharField('Date', max_length=100, blank=True)
    end_terminus_post_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='end_terminus_post_calendar_set', null=True,
        on_delete=models.CASCADE)
    end_terminus_post_normalised = models.CharField(
        'Normalised form', max_length=100, blank=True)
    end_terminus_post_type = models.ForeignKey(
        DateType, verbose_name='Type',
        related_name='end_terminus_post_type_set', null=True,
        on_delete=models.CASCADE)
    end_terminus_post_confident = models.BooleanField(
        'Confident', default=True)
    end_date = models.CharField('Date', max_length=100, blank=True)
    end_date_calendar = models.ForeignKey(Calendar, verbose_name='Calendar',
                                          related_name='end_date_calendar_set',
                                          null=True, on_delete=models.CASCADE)
    end_date_normalised = models.CharField('Normalised form', max_length=100,
                                           blank=True)
    end_date_type = models.ForeignKey(
        DateType, verbose_name='Type', null=True,
        related_name='end_date_type_set', on_delete=models.CASCADE)
    end_date_confident = models.BooleanField('Confident', default=True)
    end_terminus_ante = models.CharField('Date', max_length=100, blank=True)
    end_terminus_ante_calendar = models.ForeignKey(
        Calendar, verbose_name='Calendar',
        related_name='end_terminus_ante_calendar_set', null=True,
        on_delete=models.CASCADE)
    end_terminus_ante_normalised = models.CharField(
        'Normalised form', max_length=100, null=True, blank=True)
    end_terminus_ante_type = models.ForeignKey(
        DateType, verbose_name='Type',
        related_name='end_terminus_ante_type_set', null=True,
        on_delete=models.CASCADE)
    end_terminus_ante_confident = models.BooleanField(
        'Confident', default=True)
    note = models.TextField(blank=True)

    @staticmethod
    def _get_type_affix(date_type):
        """Return a date affix based on the date type."""
        date_type = str(date_type)
        affix = ''
        if date_type == 'circa':
            affix = 'c. '
        return affix

    @staticmethod
    def _get_confidence_affix(confident):
        """Return a date affix based on the date confidence."""
        affix = ''
        if not confident:
            affix = '?'
        return affix

    @staticmethod
    def _get_calendar_affix(calendar):
        """Return a date affix based on the calendar."""
        affix = ''
        default_calendar = get_default_object(Calendar)
        if calendar != default_calendar:
            affix = ' (%s calendar)' % (calendar)
        return affix

    def _get_period_affix(self):
        """Return a date affix based on the date period."""
        affix = ''
        if str(self.date_period) == 'floruit':
            affix = 'fl. '
        return affix

    def _assemble_date_part(self, date_part):
        """Return a string form of a date part (point date, end
        terminus post, etc).

        Arguments:
        date_part -- string name of date part

        """
        assembled_date_part = ''
        date = getattr(self, date_part)
        if date:
            type_affix = self._get_type_affix(
                getattr(self, date_part + '_type'))
            confidence_affix = self._get_confidence_affix(
                getattr(self, date_part + '_confident'))
            calendar_affix = self._get_calendar_affix(
                getattr(self, date_part + '_calendar'))
            assembled_date_part = '%s%s%s%s' % (
                type_affix, date, confidence_affix, calendar_affix)
        return assembled_date_part

    def _assemble_date_segment(self, date_segment):
        """Return a string form of a date segment (start, end, or point).

        Arguments:
        date_segment -- string name of date segment

        """
        date = self._assemble_date_part(date_segment + '_date')
        if not date:
            post_date = self._assemble_date_part(
                date_segment + '_terminus_post')
            ante_date = self._assemble_date_part(
                date_segment + '_terminus_ante')
            if post_date:
                date = 'at or after %s' % post_date
                if ante_date:
                    date = '%s and ' % date
            if ante_date:
                date = '%sat or before %s' % (date, ante_date)
        return date

    def __str__(self):
        if self.point_date or self.point_terminus_post or \
           self.point_terminus_ante:
            date = self._assemble_date_segment('point')
        else:
            start_date = self._assemble_date_segment('start')
            end_date = self._assemble_date_segment('end')
            date = '%s \N{EN DASH} %s' % (start_date, end_date)
        if date:
            period_prefix = self._get_period_affix()
            date = '%s %s' % (period_prefix, date)
            date = date.strip()
        else:
            date = '[unspecified]'
        return date


class Source (models.Model):
    assertion = models.ForeignKey(PropertyAssertion, on_delete=models.CASCADE)
    source_title = models.CharField(max_length=200)
    source_reference = models.CharField(max_length=200)


class SearchName (models.Model):
    """Model for the searchable names for an entity, derived from a
    name."""
    entity = models.ForeignKey(
        Entity, related_name='search_names', on_delete=models.CASCADE)
    name = models.ForeignKey(
        Name, related_name='search_names', on_delete=models.CASCADE)
    name_form = models.CharField(max_length=800)


class UserProfile (models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE)  # Required by Django
    # Authority assertions user has permission to
    # create/update/delete.
    editable_authorities = models.ManyToManyField(
        Authority, blank=True, related_name='editors')
    # Preferences for display.
    authority = models.ForeignKey(Authority, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    script = models.ForeignKey(Script, on_delete=models.CASCADE)
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    date_type = models.ForeignKey(DateType, on_delete=models.CASCADE)
    date_period = models.ForeignKey(DatePeriod, on_delete=models.CASCADE)
    name_type = models.ForeignKey(NameType, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.user)


class RegisteredImport (models.Model):
    importer = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    raw_xml = models.TextField()
    processed_xml = models.TextField()
    import_date = models.DateTimeField(auto_now_add=True)
