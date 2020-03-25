"""This module implements the exporting of EATS data into EATSML XML."""

import logging
from os.path import abspath, dirname, join

from lxml import etree
from django.db.models import Q
from django.db.models.query import QuerySet
from eats.models import UserProfile

from eats.models import Authority, AuthorityRecord, Calendar, \
    DatePeriod, DateType, Entity, EntityRelationshipType, EntityTypeList, \
    Language, NamePartType, NameRelationshipType, NameType, PropertyAssertion, \
    Script, SystemNamePartType
import eats.names

# Full path to this directory.
PATH = abspath(dirname(__file__))

# Logging constants.
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
FILE_LOG = join(PATH, 'export.log')
FILE_MODE = 'w'

# RelaxNG schema.
RNG_FILENAME = 'eatsml.rng'
RNG_PATH = join(PATH, RNG_FILENAME)
# Path for where to save export if it is invalid.
INVALID_FILE_PATH = join(PATH, 'invalid-export.xml')

DATE_PARTS = ('start_terminus_post', 'start_date', 'start_terminus_ante',
              'point_terminus_post', 'point_date', 'point_terminus_ante',
              'end_terminus_post', 'end_date', 'end_terminus_ante')
DATE_PART_SUFFIXES = ('_calendar', '_normalised', '_type', '_confident')

# Namespace constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'
XML = '{%s}' % (XML_NAMESPACE)
EATS_NAMESPACE = 'http://hdl.handle.net/10063/234'
EATS = '{%s}' % (EATS_NAMESPACE)
NSMAP = {None: EATS_NAMESPACE}

# Number of entities to export at a time (for memory saving purposes).
BATCH_NUMBER = 1000


class EATSExportError (Exception):

    """Class for identified errors in the export."""
    pass


class Exporter (object):

    """Class implementing an export of EATS data into EATSML XML."""

    def __init__(self):
        try:
            logging.basicConfig(level=LOG_LEVEL,
                                filename=FILE_LOG,
                                filemode=FILE_MODE,
                                format=LOG_FORMAT)
        except IOError as e:
            raise EATSExportError('Failed to set up logging: %s' % e)
        # Keep a list of the IDs of those entities that are to be
        # fully exported. Other, referenced, entities should not
        # export entity relationship assertions that point to entities
        # not in this list.
        self._primary_entity_ids = []
        # As the entities to be exported are processed, the
        # infrastructural objects they reference are tracked via their
        # IDs in the object_list dictionary. Sets are used because
        # each object my be referenced multiple times, while we only
        # wish to have each listed once.
        self._object_list = {
            'Authority': set(),
            'AuthorityRecord': set(),
            'Calendar': set(),
            'DatePeriod': set(),
            'DateType': set(),
            'Entity': set(),
            'EntityRelationshipType': set(),
            'EntityTypeList': set(),
            'Language': set(),
            'NamePartType': set(),
            'NameRelationshipType': set(),
            'NameType': set(),
            'Script': set(),
            'SystemNamePartType': set(),
        }
        self._user = None
        self._user_profile = None
        self._XML_true = self._get_XML_boolean(True)
        self._annotated = False
        self._full_details = False

    def set_user(self, user):
        """Set the user for this export.

        Arguments:
        user -- User object, with an associated profile

        """
        self._user = user
        if user.is_authenticated():
            self._user_profile = UserProfile.objects.get(user=user)

    def export_entities(self, entity_objects, annotated=False,
                        full_details=False):
        """Return the root element of an XML tree containing the
        exported entities.

        Arguments:
        entity_objects -- list or QuerySet of Entity objects
        annotated -- optional Boolean indicating if the data exported
                     should be annotated with the user's preferences
        full_details -- optioanl Boolean indicating if non-standard
                        data should be exported, such as all
                        constructed name forms

        """
        if annotated and self._user_profile is None:
            message = 'A user must be specified if the export is to be annotated'
            logging.error(message)
            raise EATSExportError(message)
        self._annotated = annotated
        self._full_details = full_details
        root = etree.Element(EATS + 'collection', nsmap=NSMAP)
        # Export the entities first in order to determine what
        # infrastructure elements are required.
        logging.info('Starting export')
        if entity_objects:
            self._export_entities(entity_objects, root)
            self._export_infrastructure(root)
        logging.info('Finished compiling XML')
        self._validate(root)
        logging.info('Finished export')
        return root

    def export_infrastructure(self, limited=False, annotated=False):
        """Return the root element of an XML tree containing the
        export of infrastructure elements.

        Arguments:
        limited -- optional Boolean indicating if the data exported should be
                   limited to those related to authorities the user can edit
        annotated -- optional Boolean indicating if the data exported
                     should be annotated with the user's preferences

        """
        if (limited or annotated) and self._user_profile is None:
            message = 'A user must be specified if the export is to be limited or annotated'
            logging.error(message)
            raise EATSExportError(message)
        self._annotated = annotated
        if limited:
            editable_authorities = self._user_profile.editable_authorities.all()
        else:
            editable_authorities = Authority.objects.all()
        editable_authorities_ids = editable_authorities.values('pk').query
        authority_filter = Q(authority__in=editable_authorities_ids)
        # Record the IDs of infrastructure objects, restricting them
        # by the editable authorities where appropriate.
        object_types = [
            (Authority, False),
            (Calendar, False),
            (DatePeriod, False),
            (DateType, False),
            (EntityRelationshipType, True),
            (EntityTypeList, True),
            (Language, False),
            (NamePartType, True),
            (NameRelationshipType, True),
            (NameType, True),
            (Script, False),
        ]
        for object_type in object_types:
            key = object_type[0]._meta.object_name
            if object_type[1]:
                objects = object_type[0].objects.filter(authority_filter)
            else:
                objects = object_type[0].objects.all()
            for eats_object in objects:
                self._object_list[key].add(eats_object.id)
        root = etree.Element(EATS + 'collection', nsmap=NSMAP)
        self._export_infrastructure(root)
        self._validate(root)
        return root

    def _export_entities(self, entity_objects, parent_element):
        """Export entity objects, attaching their XML nodes to parent."""
        # It is too memory expensive to deal with all entities at
        # once, if there are many of them, so do them in batches.
        if isinstance(entity_objects, QuerySet):
            count = entity_objects.count()
        else:
            count = len(entity_objects)
        logging.info('Exporting %d entities' % (count))
        entities_element = etree.SubElement(parent_element, EATS + 'entities')
        for lower_bound in range(0, count, BATCH_NUMBER):
            upper_bound = lower_bound + BATCH_NUMBER
            logging.info('Exporting entities %d to %d'
                         % (lower_bound, upper_bound))
            for entity_object in entity_objects[lower_bound:upper_bound]:
                self._primary_entity_ids.append(entity_object.id)
                self._export_entity(entity_object, entities_element)
        # We may have picked up some extra entities from the entity
        # relationships defined for an entity, so export those now.
        ids = tuple(self._object_list['Entity'])
        new_entity_objects = Entity.objects.filter(pk__in=ids)
        count = new_entity_objects.count()
        logging.info('Exporting potentially %d new entities' % (count))
        for lower_bound in range(0, count, BATCH_NUMBER):
            upper_bound = lower_bound + BATCH_NUMBER
            logging.info('Exporting potentially new entities %d to %d'
                         % (lower_bound, upper_bound))
            for entity_object in new_entity_objects[lower_bound:upper_bound]:
                if entity_object not in entity_objects:
                    self._export_entity(entity_object, entities_element, False)
        return

    def _export_entity(self, entity_object, parent_element, is_primary=True):
        """Export Entity object.

        Arguments:
        entity_object -- Entity object
        parent_element -- Element object
        is_primary -- Boolean indicator of whether to export all entity
                      relationships, or only those that refer to primary
                      entities

        """
        model_name = 'Entity'
        self._log_object(model_name, entity_object)
        entity_element = etree.SubElement(parent_element, EATS + 'entity')
        self._add_ids(entity_object, entity_element, 'entity')
        self._export_last_modified(entity_object, entity_element)
        if not is_primary:
            entity_element.set('is_related', self._XML_true)
        self._export_existences(entity_object, entity_element)
        self._export_entity_types(entity_object, entity_element)
        self._export_entity_notes(entity_object, entity_element)
        self._export_entity_references(entity_object, entity_element)
        self._export_names(entity_object, entity_element)
        self._export_entity_relationships(entity_object, entity_element,
                                          is_primary)
        self._export_name_relationships(entity_object, entity_element)
        return

    def _export_existences(self, entity_object, parent_element):
        """Export Existence property assertions for entity_object."""
        model_name = 'Existence'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, existence__isnull=False)
        if len(assertion_objects):
            existences_element = etree.SubElement(parent_element,
                                                  EATS + 'existence_assertions')
        for assertion_object in assertion_objects:
            self._log_assertion_object(model_name, assertion_object)
            existence_element = etree.SubElement(existences_element,
                                                 EATS + 'existence_assertion')
            self._add_ids(assertion_object, existence_element,
                          'existence_assertion')
            self._export_assertion_properties(assertion_object,
                                              existence_element)
            self._object_list['Authority'].add(
                assertion_object.authority_record.authority_id)
            self._object_list['AuthorityRecord'].add(
                assertion_object.authority_record_id)
            self._export_dates(assertion_object, existence_element)
        return

    def _export_entity_types(self, entity_object, parent_element):
        """Export EntityType property assertions for entity_object."""
        model_name = 'EntityType'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, entity_type__isnull=False)
        if len(assertion_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'entity_type_assertions')
        for assertion_object in assertion_objects:
            self._log_assertion_object(model_name, assertion_object)
            type_element = etree.SubElement(types_element,
                                            EATS + 'entity_type_assertion')
            self._add_ids(assertion_object, type_element,
                          'entity_type_assertion')
            self._export_assertion_properties(assertion_object, type_element)
            entity_type_id = assertion_object.entity_type.entity_type_id
            type_element.set('entity_type', 'entity_type-%d'
                             % (entity_type_id))
            self._object_list['EntityTypeList'].add(entity_type_id)
            self._export_dates(assertion_object, type_element)
        return

    def _export_entity_notes(self, entity_object, parent_element):
        """Export EntityNote property assertions for entity_object."""
        model_name = 'EntityNote'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, note__isnull=False)
        if len(assertion_objects):
            notes_element = etree.SubElement(parent_element,
                                             EATS + 'entity_note_assertions')
        for assertion_object in assertion_objects:
            self._log_assertion_object(model_name, assertion_object)
            note_element = etree.SubElement(notes_element,
                                            EATS + 'entity_note_assertion')
            self._add_ids(assertion_object, note_element, 'note_assertion')
            self._export_assertion_properties(assertion_object, note_element)
            note_element.set('is_internal', self._get_XML_boolean(
                assertion_object.note.is_internal))
            note_text_element = etree.SubElement(note_element, EATS + 'note')
            note_text_element.text = assertion_object.note.note
            self._export_dates(assertion_object, note_element)
        return

    def _export_entity_references(self, entity_object, parent_element):
        """Export EntityReference property assertions for entity_object."""
        model_name = 'EntityReference'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, reference__isnull=False)
        if len(assertion_objects):
            references_element = etree.SubElement(parent_element, EATS +
                                                  'entity_reference_assertions')
        for assertion_object in assertion_objects:
            self._log_assertion_object(model_name, assertion_object)
            reference_element = etree.SubElement(references_element, EATS +
                                                 'entity_reference_assertion')
            self._add_ids(assertion_object, reference_element,
                          'reference_assertion')
            self._export_assertion_properties(assertion_object,
                                              reference_element)
            label_element = etree.SubElement(reference_element, EATS + 'label')
            label_element.text = assertion_object.reference.label
            url_element = etree.SubElement(reference_element, EATS + 'url')
            url_element.text = assertion_object.reference.url
            self._export_dates(assertion_object, reference_element)
        return

    def _export_names(self, entity_object, parent_element):
        """Export Name property assertions for entity_object."""
        model_name = 'Name'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, name__isnull=False)
        if len(assertion_objects):
            names_element = etree.SubElement(parent_element,
                                             EATS + 'name_assertions')
        preferred_name = None
        if self._annotated:
            defaults = {'authority': self._user_profile.authority,
                        'language': self._user_profile.language,
                        'script': self._user_profile.script}
            preferred_name = entity_object.get_single_name_object(defaults)
        for assertion_object in assertion_objects:
            self._log_assertion_object(model_name, assertion_object)
            name_element = etree.SubElement(names_element,
                                            EATS + 'name_assertion')
            self._export_assertion_properties(assertion_object, name_element)
            name_object = assertion_object.name
            self._add_ids(assertion_object, name_element, 'name_assertion')
            name_type_id = name_object.name_type_id
            name_element.set('type', 'name_type-%d' % (name_type_id))
            self._object_list['NameType'].add(name_type_id)
            language_id = name_object.language_id
            name_element.set('language', 'language-%d' % (language_id))
            self._object_list['Language'].add(language_id)
            script_id = name_object.script_id
            name_element.set('script', 'script-%d' % (script_id))
            self._object_list['Script'].add(script_id)
            if name_object == preferred_name:
                name_element.set('user_default', self._XML_true)
            display_form_element = etree.SubElement(name_element,
                                                    EATS + 'display_form')
            display_form_element.text = name_object.display_form
            self._export_name_parts(name_object, name_element)
            if self._full_details:
                self._export_name_variants(name_object, name_element)
            self._export_dates(assertion_object, name_element)
            self._export_name_notes(name_object, name_element)
        return

    def _export_name_parts(self, name_object, parent_element):
        """Export NamePart objects for name_object."""
        model_name = 'NamePart'
        self._log_start_objects(model_name)
        part_objects = name_object.name_parts.all()
        if len(part_objects):
            parts_element = etree.SubElement(parent_element,
                                             EATS + 'name_parts')
        for part_object in part_objects:
            self._log_object(model_name, part_object)
            part_element = etree.SubElement(parts_element, EATS + 'name_part')
            type_id = part_object.name_part_type_id
            part_element.set('type', 'name_part_type-%d' % (type_id))
            self._object_list['NamePartType'].add(type_id)
            if part_object.language_id:
                language_id = part_object.language_id
                part_element.set('language', 'language-%d' % (language_id))
                self._object_list['Language'].add(language_id)
            if part_object.script_id:
                script_id = part_object.script_id
                part_element.set('script', 'script-%d' % (script_id))
                self._object_list['Script'].add(script_id)
            part_element.text = part_object.name_part
        assembled_form_element = etree.SubElement(parent_element,
                                                  EATS + 'assembled_form')
        assembled_form_element.text = name_object.get_assembled_form()
        return

    @staticmethod
    def _export_name_variants(name_object, parent_element):
        """Export variant name forms for name_object."""
        variants_element = etree.SubElement(parent_element,
                                            EATS + 'variant_forms')
        variants = eats.names.compile_variants(name_object)
        for variant in variants:
            variant_element = etree.SubElement(variants_element,
                                               EATS + 'variant_form')
            variant_element.text = variant

    def _export_name_notes(self, name_object, parent_element):
        """Export NameNote objects for name_object."""
        model_name = 'NameNote'
        self._log_start_objects(model_name)
        note_objects = name_object.notes.all()
        if len(note_objects):
            notes_element = etree.SubElement(parent_element,
                                             EATS + 'name_notes')
        for note_object in note_objects:
            self._log_object(model_name, note_object)
            note_element = etree.SubElement(notes_element, EATS + 'name_note')
            note_element.set('is_internal',
                             self._get_XML_boolean(note_object.is_internal))
            note_element.text = note_object.note
        return

    def _export_entity_relationships(self, entity_object, parent_element,
                                     is_primary):
        """Export EntityRelationship property assertions for entity_object."""
        model_name = 'EntityRelationship'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, entity_relationship__isnull=False)
        relationships_element = None
        for assertion_object in assertion_objects:
            entity_id = assertion_object.entity_relationship.related_entity_id
            if is_primary or entity_id in self._primary_entity_ids:
                if relationships_element is None:
                    relationships_element = etree.SubElement(
                        parent_element, EATS + 'entity_relationship_assertions')
                self._log_assertion_object(model_name, assertion_object)
                relationship_element = etree.SubElement(
                    relationships_element,
                    EATS + 'entity_relationship_assertion')
                self._add_ids(assertion_object, relationship_element,
                              'entity_relationship_assertion')
                self._export_assertion_properties(assertion_object,
                                                  relationship_element)
                relationship_object = assertion_object.entity_relationship
                type_id = relationship_object.entity_relationship_type_id
                relationship_element.set('type', 'entity_relationship_type-%d'
                                         % (type_id))
                self._object_list['EntityRelationshipType'].add(type_id)
                relationship_element.set('related_entity', 'entity-%d' %
                                         (entity_id))
                self._export_dates(assertion_object, relationship_element)
                self._export_entity_relationship_notes(relationship_object,
                                                       relationship_element)
                # Add the related entity to the list of entities to be
                # exported.
                self._object_list['Entity'].add(entity_id)
        if is_primary:
            # Find all entities that have this entity as a related
            # entity, and add them to the list of entities to be
            # exported.
            for entity in Entity.objects.filter(
                    assertions__entity_relationship__related_entity=entity_object):
                self._object_list['Entity'].add(entity.id)
        return

    def _export_entity_relationship_notes(self, relationship_object,
                                          parent_element):
        """Export EntityRelationshipNote objects for relationship_object."""
        model_name = 'EntityRelationshipNote'
        self._log_start_objects(model_name)
        note_objects = relationship_object.notes.all()
        if len(note_objects):
            notes_element = etree.SubElement(parent_element,
                                             EATS + 'entity_relationship_notes')
        for note_object in note_objects:
            self._log_object(model_name, note_object)
            note_element = etree.SubElement(notes_element, EATS +
                                            'entity_relationship_note')
            note_element.set('is_internal',
                             self._get_XML_boolean(note_object.is_internal))
            note_element.text = note_object.note
        return

    def _export_name_relationships(self, entity_object, parent_element):
        """Export NameRelationship property assertions for entity_object."""
        model_name = 'NameRelationship'
        self._log_start_objects(model_name)
        assertion_objects = PropertyAssertion.objects.filter(
            entity=entity_object, name_relationship__isnull=False)
        if len(assertion_objects):
            relationships_element = etree.SubElement(
                parent_element, EATS + 'name_relationship_assertions')
        for assertion_object in assertion_objects:
            self._log_assertion_object(model_name, assertion_object)
            relationship_element = etree.SubElement(
                relationships_element, EATS + 'name_relationship_assertion')
            self._add_ids(assertion_object, relationship_element,
                          'name_relationship_assertion')
            self._export_assertion_properties(assertion_object,
                                              relationship_element)
            type_id = assertion_object.name_relationship.name_relationship_type_id
            relationship_element.set('type', 'name_relationship_type-%d'
                                     % (type_id))
            self._object_list['NameRelationshipType'].add(type_id)
            name_assertion = assertion_object.name_relationship.name.assertion.get()
            relationship_element.set('name', 'name_assertion-%d' %
                                     (name_assertion.id))
            related_name_assertion = assertion_object.name_relationship.related_name.assertion.get()
            relationship_element.set('related_name', 'name_assertion-%d' %
                                     (related_name_assertion.id))
        return

    def _export_dates(self, assertion_object, parent_element):
        """Export Date objects associated with assertion_object."""
        model_name = 'Date'
        self._log_start_objects(model_name)
        date_objects = assertion_object.dates.all()
        if len(date_objects):
            dates_element = etree.SubElement(parent_element, EATS + 'dates')
            for date_object in date_objects:
                self._log_object(model_name, date_object)
                date_element = etree.SubElement(dates_element, EATS + 'date')
                self._add_ids(date_object, date_element, 'date')
                date_period_id = date_object.date_period_id
                date_element.set('period', 'date_period-%d'
                                 % (date_period_id))
                self._object_list['DatePeriod'].add(date_period_id)
                for date_part in DATE_PARTS:
                    self._export_date_part(
                        date_object, date_part, date_element)
                if date_object.note:
                    note_element = etree.SubElement(
                        date_element, EATS + 'note')
                    note_element.text = date_object.note
                assembled_form_element = etree.SubElement(
                    date_element, EATS + 'assembled_form')
                assembled_form_element.text = str(date_object)
        return

    def _export_date_part(self, date_object, date_part, parent_element):
        """Export the date_part set of fields for date_object."""
        date_part_value = getattr(date_object, date_part)
        if not date_part_value:
            return
        date_element = etree.SubElement(parent_element, EATS + 'date_part')
        date_element.set('type', date_part)
        raw_element = etree.SubElement(date_element, EATS + 'raw')
        raw_element.text = date_part_value
        for suffix in DATE_PART_SUFFIXES:
            self._export_date_part_field(date_object, date_part, suffix,
                                         date_element)
        return

    def _export_date_part_field(self, date_object, date_part, suffix,
                                parent_element):
        """Export the particular field for date_part of date_object."""
        field_name = date_part + suffix
        value = getattr(date_object, field_name)
        if suffix == '_calendar':
            parent_element.set('calendar', 'calendar-%d' % value.id)
            self._object_list['Calendar'].add(value.id)
        elif suffix == '_confident':
            parent_element.set('confident', self._get_XML_boolean(value))
        elif suffix == '_normalised':
            field_element = etree.SubElement(parent_element, EATS +
                                             'normalised')
            field_element.text = value
        elif suffix == '_type':
            parent_element.set('date_type', 'date_type-%d' % value.id)
            self._object_list['DateType'].add(value.id)
        return

    def _export_assertion_properties(self, assertion_object, parent_element):
        """Export the common PropertyAssertion data from assertion_object."""
        parent_element.set('authority_record', 'authority_record-%d'
                           % (assertion_object.authority_record_id))
        parent_element.set('is_preferred',
                           self._get_XML_boolean(assertion_object.is_preferred))
        return

    def _export_infrastructure(self, parent_element):
        """Export those types of objects that serve as 'static' material
        referenced by the entities. Only referenced objects of each type
        are exported."""
        self._export_authorities(parent_element)
        self._export_entity_types_list(parent_element)
        self._export_entity_relationship_types(parent_element)
        self._export_name_types(parent_element)
        name_part_types_element = self._export_name_part_types(parent_element)
        languages_element = self._export_languages(parent_element)
        self._export_system_name_part_types(parent_element)
        # The schema requires that System Name Part Types go before Name
        # Part Types and Languages, so move them.
        if name_part_types_element is not None:
            parent_element.append(name_part_types_element)
        if languages_element is not None:
            parent_element.append(languages_element)
        self._export_scripts(parent_element)
        self._export_name_relationship_types(parent_element)
        self._export_date_periods(parent_element)
        self._export_date_types(parent_element)
        self._export_calendars(parent_element)
        self._export_authority_records(parent_element)
        # The schema requires that Entities go last, so move them there.
        if parent_element[0].tag == EATS + 'entities':
            parent_element.append(parent_element[0])
        return

    def _export_authorities(self, parent_element):
        """Export referenced Authority objects."""
        model_name = 'Authority'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        authority_objects = Authority.objects.filter(pk__in=ids)
        if len(authority_objects):
            authorities_element = etree.SubElement(parent_element,
                                                   EATS + 'authorities')
        for authority_object in authority_objects:
            self._log_object(model_name, authority_object)
            authority_element = etree.SubElement(authorities_element,
                                                 EATS + 'authority')
            self._add_ids(authority_object, authority_element, 'authority')
            self._export_last_modified(authority_object, authority_element)
            self._annotate_with_user_prefs(authority_object, authority_element,
                                           'authority')
            authority_element.set('is_default', self._get_XML_boolean(
                authority_object.is_default))
            authority_element.set('default_calendar', 'calendar-%s' %
                                  authority_object.default_calendar_id)
            self._object_list['Calendar'].add(
                authority_object.default_calendar_id)
            authority_element.set('default_date_period', 'date_period-%s' %
                                  authority_object.default_date_period_id)
            self._object_list['DatePeriod'].add(
                authority_object.default_date_period_id)
            authority_element.set('default_date_type', 'date_type-%s' %
                                  authority_object.default_date_type_id)
            self._object_list['DateType'].add(
                authority_object.default_date_type_id)
            authority_element.set('default_language', 'language-%s' %
                                  authority_object.default_calendar_id)
            self._object_list['Language'].add(
                authority_object.default_calendar_id)
            authority_element.set('default_script', 'script-%s' %
                                  authority_object.default_script_id)
            self._object_list['Script'].add(authority_object.default_script_id)
            name_element = etree.SubElement(authority_element, EATS + 'name')
            name_element.text = authority_object.authority
            abbreviated_name_element = etree.SubElement(
                authority_element, EATS + 'abbreviated_name')
            abbreviated_name_element.text = authority_object.abbreviated_name
            base_id_element = etree.SubElement(authority_element,
                                               EATS + 'base_id')
            base_id_element.text = authority_object.base_id
            base_url_element = etree.SubElement(authority_element,
                                                EATS + 'base_url')
            base_url_element.text = authority_object.base_url
        return

    def _export_entity_types_list(self, parent_element):
        """Export referenced EntityTypeList objects."""
        model_name = 'EntityTypeList'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = EntityTypeList.objects.filter(pk__in=ids)
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'entity_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(
                types_element, EATS + 'entity_type')
            self._add_ids(type_object, type_element, 'entity_type')
            type_element.set('authority', 'authority-%d'
                             % (type_object.authority_id))
            self._export_last_modified(type_object, type_element)
            type_element.text = type_object.entity_type
        return

    def _export_entity_relationship_types(self, parent_element):
        """Export referenced EntityRelationshipType objects."""
        model_name = 'EntityRelationshipType'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = EntityRelationshipType.objects.filter(pk__in=ids)
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'entity_relationship_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(types_element,
                                            EATS + 'entity_relationship_type')
            self._add_ids(type_object, type_element,
                          'entity_relationship_type')
            type_element.set('authority', 'authority-%d'
                             % (type_object.authority_id))
            self._export_last_modified(type_object, type_element)
            type_element.text = type_object.entity_relationship_type
        return

    def _export_name_types(self, parent_element):
        """Export reference NameType objects."""
        model_name = 'NameType'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = NameType.objects.filter(pk__in=ids)
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'name_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(types_element, EATS + 'name_type')
            self._add_ids(type_object, type_element, 'name_type')
            type_element.set('authority', 'authority-%d'
                             % (type_object.authority_id))
            self._export_last_modified(type_object, type_element)
            self._annotate_with_user_prefs(type_object, type_element,
                                           'name_type')
            type_element.set('is_default', self._get_XML_boolean(
                type_object.is_default))
            type_element.text = type_object.name_type
        return

    def _export_name_part_types(self, parent_element):
        """Export referenced NamePartType objects."""
        model_name = 'NamePartType'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = NamePartType.objects.filter(pk__in=ids)
        types_element = None
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'name_part_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(types_element,
                                            EATS + 'name_part_type')
            self._add_ids(type_object, type_element, 'name_part_type')
            type_element.set('authority', 'authority-%d'
                             % (type_object.authority_id))
            type_element.set('system_name_part_type',
                             'system_name_part_type-%d'
                             % (type_object.system_name_part_type_id))
            self._export_last_modified(type_object, type_element)
            type_element.text = type_object.name_part_type
            self._object_list['SystemNamePartType'].add(
                type_object.system_name_part_type_id)
        return types_element

    def _export_languages(self, parent_element):
        """Export referenced Language objects."""
        model_name = 'Language'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        language_objects = Language.objects.filter(pk__in=ids)
        languages_element = None
        if len(language_objects):
            languages_element = etree.SubElement(parent_element,
                                                 EATS + 'languages')
        for language_object in language_objects:
            self._log_object(model_name, language_object)
            language_element = etree.SubElement(languages_element,
                                                EATS + 'language')
            self._add_ids(language_object, language_element, 'language')
            self._export_last_modified(language_object, language_element)
            self._annotate_with_user_prefs(language_object, language_element,
                                           'language')
            name_element = etree.SubElement(language_element, EATS + 'name')
            name_element.text = language_object.language_name
            code_element = etree.SubElement(language_element, EATS + 'code')
            code_element.text = language_object.language_code
            types_element = etree.SubElement(language_element,
                                             EATS + 'system_name_part_types')
            for type_object in language_object.system_name_part_types.all():
                type_element = etree.SubElement(types_element,
                                                EATS + 'system_name_part_type')
                type_element.set('ref', 'system_name_part_type-%d'
                                 % (type_object.id))
                self._object_list['SystemNamePartType'].add(type_object.id)
        return languages_element

    def _export_system_name_part_types(self, parent_element):
        """Export referenced SystemNamePartType objects."""
        model_name = 'SystemNamePartType'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = SystemNamePartType.objects.filter(pk__in=ids)
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'system_name_part_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(types_element,
                                            EATS + 'system_name_part_type')
            self._add_ids(type_object, type_element, 'system_name_part_type')
            name_element = etree.SubElement(type_element, EATS + 'name')
            name_element.text = type_object.name_part_type
            description_element = etree.SubElement(type_element,
                                                   EATS + 'description')
            description_element.text = type_object.description
        return

    def _export_scripts(self, parent_element):
        """Export referenced Script objects."""
        model_name = 'Script'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        script_objects = Script.objects.filter(pk__in=ids)
        if len(script_objects):
            scripts_element = etree.SubElement(
                parent_element, EATS + 'scripts')
        for script_object in script_objects:
            self._log_object(model_name, script_object)
            script_element = etree.SubElement(scripts_element, EATS + 'script')
            self._add_ids(script_object, script_element, 'script')
            self._export_last_modified(script_object, script_element)
            self._annotate_with_user_prefs(script_object, script_element,
                                           'script')
            name_element = etree.SubElement(script_element, EATS + 'name')
            name_element.text = script_object.script_name
            code_element = etree.SubElement(script_element, EATS + 'code')
            code_element.text = script_object.script_code
        return

    def _export_name_relationship_types(self, parent_element):
        """Export referenced NameRelationshipType objects."""
        model_name = 'NameRelationshipType'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = NameRelationshipType.objects.filter(pk__in=ids)
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'name_relationship_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(types_element,
                                            EATS + 'name_relationship_type')
            self._add_ids(type_object, type_element, 'name_relationship_type')
            type_element.set('authority', 'authority-%d'
                             % (type_object.authority_id))
            self._export_last_modified(type_object, type_element)
            type_element.text = type_object.name_relationship_type
        return

    def _export_calendars(self, parent_element):
        """Export referenced Calendar objects."""
        model_name = 'Calendar'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        calendar_objects = Calendar.objects.filter(pk__in=ids)
        if len(calendar_objects):
            calendars_element = etree.SubElement(parent_element,
                                                 EATS + 'calendars')
        for calendar_object in calendar_objects:
            self._log_object(model_name, calendar_object)
            calendar_element = etree.SubElement(calendars_element,
                                                EATS + 'calendar')
            self._add_ids(calendar_object, calendar_element, 'calendar')
            self._export_last_modified(calendar_object, calendar_element)
            self._annotate_with_user_prefs(calendar_object, calendar_element,
                                           'calendar')
            calendar_element.text = calendar_object.calendar
        return

    def _export_date_types(self, parent_element):
        """Export referenced DateType objects."""
        model_name = 'DateType'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        type_objects = DateType.objects.filter(pk__in=ids)
        if len(type_objects):
            types_element = etree.SubElement(parent_element,
                                             EATS + 'date_types')
        for type_object in type_objects:
            self._log_object(model_name, type_object)
            type_element = etree.SubElement(types_element, EATS + 'date_type')
            self._add_ids(type_object, type_element, 'date_type')
            self._export_last_modified(type_object, type_element)
            self._annotate_with_user_prefs(type_object, type_element,
                                           'date_type')
            type_element.text = type_object.date_type
        return

    def _export_date_periods(self, parent_element):
        """Export referenced DatePeriod objects."""
        model_name = 'DatePeriod'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        period_objects = DatePeriod.objects.filter(pk__in=ids)
        if len(period_objects):
            periods_element = etree.SubElement(parent_element,
                                               EATS + 'date_periods')
        for period_object in period_objects:
            self._log_object(model_name, period_object)
            period_element = etree.SubElement(periods_element,
                                              EATS + 'date_period')
            self._add_ids(period_object, period_element, 'date_period')
            self._export_last_modified(period_object, period_element)
            self._annotate_with_user_prefs(period_object, period_element,
                                           'date_period')
            period_element.text = period_object.date_period
        return

    def _export_authority_records(self, parent_element):
        """Export reference AuthorityRecord objects."""
        model_name = 'AuthorityRecord'
        self._log_start_objects(model_name)
        ids = tuple(self._object_list[model_name])
        if ids:
            records_element = etree.SubElement(parent_element, EATS +
                                               'authority_records')
        # There are limits to the number of IDs that can successfully be
        # listed in the SQL query, so export the AuthorityRecords in
        # batches.
        batch_number = 100
        for lower_bound in range(0, len(ids), batch_number):
            upper_bound = lower_bound + batch_number
            batch_ids = ids[lower_bound:upper_bound]
            logging.debug('Exporting AuthorityRecord objects with ids %d to %d'
                          % (lower_bound, upper_bound))
            record_objects = AuthorityRecord.objects.filter(pk__in=batch_ids)
            for record_object in record_objects:
                record_element = etree.SubElement(records_element,
                                                  EATS + 'authority_record')
                self._add_ids(record_object, record_element,
                              'authority_record')
                record_element.set('authority', 'authority-%d'
                                   % (record_object.authority_id))
                self._export_last_modified(record_object, record_element)
                id_element = etree.SubElement(record_element,
                                              EATS + 'authority_system_id')
                id_element.set('is_complete', self._get_XML_boolean(
                    record_object.is_complete_id))
                id_element.text = record_object.authority_system_id
                url_element = etree.SubElement(record_element,
                                               EATS + 'authority_system_url')
                url_element.set('is_complete', self._get_XML_boolean(
                    record_object.is_complete_url))
                url_element.text = record_object.authority_system_url
        return

    ###
    # Helper methods
    ###

    def _add_ids(self, model_object, element, prefix):
        """Add XML and EATS IDs to element."""
        self._add_xml_id(model_object, element, prefix)
        self._add_eats_id(model_object, element)

    def _annotate_with_user_prefs(self, model_object, element, object_type):
        """Check whether model_object is the user's default for this
        object_type; if so, add an attribute to this effect to
        element.

        Arguments:
        model_object -- Model object
        element -- Element object
        object_type -- string name of the preference
                       (models.UserProfile field)

        """
        if self._annotated:
            preferred_object = getattr(self._user_profile, object_type)
            if preferred_object == model_object:
                element.set('user_default', self._XML_true)

    def _log_assertion_object(self, model_name, property_assertion_object):
        """Log the handling of the property_assertion_object for a model_name
        assertion."""
        assertion_name = '%s property assertion' % (model_name)
        self._log_object(assertion_name, property_assertion_object)

    @staticmethod
    def _validate(root):
        """Validate the XML document against the RelaxNG schema."""
        logging.debug('Parsing RelaxNG schema')
        relaxng_doc = etree.parse(RNG_PATH)
        relaxng = etree.RelaxNG(relaxng_doc)
        logging.debug('Validating export file')
        if not relaxng.validate(etree.ElementTree(root)):
            message = 'RelaxNG validation of the export document failed: %s' % \
                (relaxng.error_log.last_error)
            logging.error(message)
            try:
                xml_file = open(INVALID_FILE_PATH, 'w')
                tree = root.getroottree()
                tree.write(xml_file, encoding='utf-8', pretty_print=True,
                           xml_declaration=True)
                xml_file.close()
            except Exception as exception:
                save_message = 'Could not save the invalid document to %s due to the following error: %s' % (
                    INVALID_FILE_PATH, exception)
                logging.error(save_message)
            raise EATSExportError(message)
        logging.debug('Finished validating export file')

    @staticmethod
    def _get_XML_boolean(boolean):
        """Return boolean (a Python boolean) in a format suitable for use in
        an XML document using the XML Schema boolean datatype."""
        return str(boolean).lower()

    @staticmethod
    def _add_xml_id(model_object, element, prefix):
        """Add an XML ID with value taken from model_object to element
        appended to prefix."""
        element.set(XML + 'id', '%s-%d' % (prefix, model_object.id))

    @staticmethod
    def _add_eats_id(model_object, element):
        """Add an eats_id attribute with value taken from model_object to
        element."""
        element.set('eats_id', str(model_object.id))

    @staticmethod
    def _export_last_modified(model_object, parent_element):
        """Export the last_modified field of model_object as an attribute on
        parent_element."""
        parent_element.set('last_modified',
                           model_object.last_modified.isoformat())
        return

    @staticmethod
    def _log_start_objects(model_name):
        """Log the handling of model_name objects."""
        logging.debug('Exporting %s objects' % (model_name))

    @staticmethod
    def _log_object(model_name, model_object):
        """Log the handling of model_name model_object."""
        logging.debug('Exporting %s object with id %d'
                      % (model_name, model_object.id))
