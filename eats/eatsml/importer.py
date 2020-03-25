"""This module implements the importing of an EATSML XML document into EATS."""

import copy
import logging
from os.path import abspath, dirname, join
from eats.models import UserProfile

from lxml import etree

from eats.models import Authority, AuthorityRecord, Calendar, Date, \
    DatePeriod, DateType, Entity, EntityNote, EntityReference, \
    EntityRelationship, EntityRelationshipType, EntityRelationshipNote, \
    EntityType, EntityTypeList, Existence, Language, Name, NamePart, \
    NameType, NamePartType, NameRelationship, NameRelationshipType, \
    PropertyAssertion, Script, SystemNamePartType, \
    get_new_authority_record_details

# Full path to this directory.
PATH = abspath(dirname(__file__))

# RelaxNG schema.
RNG_FILENAME = 'eatsml.rng'
RNG_PATH = join(PATH, RNG_FILENAME)

# Logging constants.
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
FILE_LOG = join(PATH, 'import.log')
FILE_MODE = 'w'

# Namespace constants.
XML_NAMESPACE = 'http://www.w3.org/XML/1998/namespace'
XML = '{%s}' % (XML_NAMESPACE)
EATS_NAMESPACE = 'http://hdl.handle.net/10063/234'
EATS = '{%s}' % (EATS_NAMESPACE)
NSMAP = {'e': EATS_NAMESPACE}


class EATSImportError (Exception):

    """Class for identified errors in the import."""
    pass


class Importer (object):

    """Class implementing an import of an EATSML XML document into EATS."""

    def __init__(self, user):
        try:
            logging.basicConfig(level=LOG_LEVEL,
                                filename=FILE_LOG,
                                filemode=FILE_MODE,
                                format=LOG_FORMAT)
        except IOError as e:
            raise EATSImportError('Failed to set up logging: %s' % e)
        self._xml_object_map = {
            'authority': {},
            'authority record': {},
            'calendar': {},
            'date period': {},
            'date type': {},
            'entity': {},
            'entity relationship type': {},
            'entity type': {},
            'language': {},
            'name': {},
            'name part type': {},
            'name relationship type': {},
            'name type': {},
            'script': {},
            'system name part type': {},
        }
        self._user = None
        self._has_add_infrastructure_permission = False
        self._user_authority_ids = []
        self._set_user(user)

    def _set_user(self, user):
        """Set the user for this import.

        Arguments:
        user -- User object

        """
        self._user = user
        if not self._user.is_superuser:
            user_profile = UserProfile.objects.get(user=user)
            authorities = user_profile.editable_authorities.all()
            self._user_authority_ids = [authority.id for authority in
                                        authorities]
        self._has_add_infrastructure_permission = self._user.is_superuser

    def import_file(self, eatsml):
        """Import XML data from eatsml into EATS, returning the
        the parsed XML document and that same document annotated with
        the EATS IDs for the elements imported (both lxml "root"
        objects).

        Arguments:
        eatsml -- open file or filename (anything suitable for the
                  etree parse method)

        """
        logging.debug('Starting import')
        parser = etree.XMLParser(remove_blank_text=True)
        raw_tree = etree.parse(eatsml, parser)
        logging.debug('Parsed import file')
        self._validate(raw_tree)
        processed_tree = copy.deepcopy(raw_tree)
        self._import_infrastructure(processed_tree)
        self._import_entities(processed_tree)
        self._import_entity_relationships(processed_tree)
        return raw_tree.getroot(), processed_tree.getroot()

    def _import_infrastructure(self, tree):
        """Import the non-entity information from XML tree."""
        self._import_system_name_part_types(tree)
        self._import_calendars(tree)
        self._import_date_periods(tree)
        self._import_date_types(tree)
        self._import_languages(tree)
        self._import_scripts(tree)
        self._import_authorities(tree)
        self._import_entity_types_list(tree)
        self._import_entity_relationship_types(tree)
        self._import_name_types(tree)
        self._import_name_part_types(tree)
        self._import_name_relationship_types(tree)
        self._import_authority_records(tree)

    def _import_authorities(self, tree):
        """Import the authority records from XML tree."""
        item_name = 'authority'
        model = Authority
        self._log_start_items(item_name)
        authority_elements = tree.xpath(
            '/e:collection/e:authorities/e:authority', namespaces=NSMAP)
        for authority_element in authority_elements:
            self._log_xml(item_name, authority_element)
            xml_id = self._get_element_id(authority_element)
            eats_id = self._get_element_eats_id(authority_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                name = self._get_text_from_XML(authority_element, 'e:name')
                abbreviated_name = self._get_text_from_XML(authority_element,
                                                           'e:abbreviated_name')
                base_id = self._get_text_from_XML(authority_element,
                                                  'e:base_id')
                base_url = self._get_text_from_XML(authority_element,
                                                   'e:base_url')
                is_default = self._get_boolean(authority_element, 'is_default')
                default_calendar_id = self._get_referenced_eats_id(
                    authority_element, 'default_calendar', 'calendar')
                default_date_period_id = self._get_referenced_eats_id(
                    authority_element, 'default_date_period', 'date period')
                default_date_type_id = self._get_referenced_eats_id(
                    authority_element, 'default_date_type', 'date type')
                default_language_id = self._get_referenced_eats_id(
                    authority_element, 'default_language', 'language')
                default_script_id = self._get_referenced_eats_id(
                    authority_element, 'default_script', 'script')
                authority_object = model(
                    authority=name, abbreviated_name=abbreviated_name,
                    base_id=base_id, base_url=base_url, is_default=is_default,
                    default_calendar_id=default_calendar_id,
                    default_date_period_id=default_date_period_id,
                    default_date_type_id=default_date_type_id,
                    default_language_id=default_language_id,
                    default_script_id=default_script_id)
                authority_object.save()
                eats_id = authority_object.id
                self._add_eats_id(authority_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_entity_types_list(self, tree):
        """Import entity types list from XML tree."""
        item_name = 'entity type'
        model = EntityTypeList
        self._log_start_items(item_name)
        type_elements = tree.xpath('/e:collection/e:entity_types/e:entity_type',
                                   namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                authority_id = self._get_referenced_eats_id(type_element,
                                                            'authority')
                entity_type = type_element.text
                type_object = model(entity_type=entity_type,
                                    authority_id=authority_id)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_entity_relationship_types(self, tree):
        """Import entity relationship types from XML tree."""
        item_name = 'entity relationship type'
        model = EntityRelationshipType
        self._log_start_items(item_name)
        type_elements = tree.xpath(
            '/e:collection/e:entity_relationship_types/e:entity_relationship_type',
            namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                authority_id = self._get_referenced_eats_id(type_element,
                                                            'authority')
                entity_relationship_type = type_element.text
                type_object = model(
                    entity_relationship_type=entity_relationship_type,
                    authority_id=authority_id)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_name_types(self, tree):
        """Import name types from XML tree."""
        item_name = 'name type'
        model = NameType
        self._log_start_items(item_name)
        type_elements = tree.xpath('/e:collection/e:name_types/e:name_type',
                                   namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                authority_id = self._get_referenced_eats_id(
                    type_element, 'authority')
                is_default = self._get_boolean(type_element, 'is_default')
                name_type = type_element.text
                type_object = NameType(name_type=name_type,
                                       is_default=is_default,
                                       authority_id=authority_id)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_system_name_part_types(self, tree):
        """Import system name part types from XML tree."""
        item_name = 'system name part type'
        model = SystemNamePartType
        self._log_start_items(item_name)
        type_elements = tree.xpath(
            '/e:collection/e:system_name_part_types/e:system_name_part_type',
            namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                name_part_type = self._get_text_from_XML(
                    type_element, 'e:name')
                description = self._get_text_from_XML(type_element,
                                                      'e:description')
                type_object = model(name_part_type=name_part_type,
                                    description=description)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_name_part_types(self, tree):
        """Import name part types from XML tree."""
        item_name = 'name part type'
        model = NamePartType
        self._log_start_items(item_name)
        type_elements = tree.xpath(
            '/e:collection/e:name_part_types/e:name_part_type',
            namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                authority_id = self._get_referenced_eats_id(type_element,
                                                            'authority')
                system_name_part_type_id = self._get_referenced_eats_id(
                    type_element, 'system_name_part_type')
                name_part_type = type_element.text
                type_object = model(
                    name_part_type=name_part_type, authority_id=authority_id,
                    system_name_part_type_id=system_name_part_type_id)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_languages(self, tree):
        """Import languages from XML tree."""
        item_name = 'language'
        model = Language
        self._log_start_items(item_name)
        language_elements = tree.xpath('/e:collection/e:languages/e:language',
                                       namespaces=NSMAP)
        for language_element in language_elements:
            self._log_xml(item_name, language_element)
            xml_id = self._get_element_id(language_element)
            eats_id = self._get_element_eats_id(language_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                name = self._get_text_from_XML(language_element, 'e:name')
                code = self._get_text_from_XML(language_element, 'e:code')
                language_object = model(language_code=code,
                                        language_name=name)
                language_object.save()
                eats_id = language_object.id
                self._add_eats_id(language_element, eats_id)
                type_elements = language_element.xpath(
                    'e:system_name_part_types/e:system_name_part_type',
                    namespaces=NSMAP)
                for type_element in type_elements:
                    logging.debug('Importing language to name_part_type relationship from XML: %s'
                                  % (etree.tostring(type_element)))
                    system_name_part_type_id = self._get_referenced_eats_id(
                        type_element, 'ref', 'system name part type')
                    logging.debug(system_name_part_type_id)
                    type_object = SystemNamePartType.objects.get(
                        pk=system_name_part_type_id)
                    # There is no need to check whether this relationship
                    # already exists, as adding the same item does not
                    # result in a duplicate.
                    language_object.system_name_part_types.add(type_object)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_scripts(self, tree):
        """Import scripts from XML tree."""
        item_name = 'script'
        model = Script
        self._log_start_items(item_name)
        script_elements = tree.xpath('/e:collection/e:scripts/e:script',
                                     namespaces=NSMAP)
        for script_element in script_elements:
            self._log_xml(item_name, script_element)
            xml_id = self._get_element_id(script_element)
            eats_id = self._get_element_eats_id(script_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                name = self._get_text_from_XML(script_element, 'e:name')
                code = self._get_text_from_XML(script_element, 'e:code')
                script_object = model(script_code=code, script_name=name)
                script_object.save()
                eats_id = script_object.id
                self._add_eats_id(script_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_name_relationship_types(self, tree):
        """Import name relationship types from XML tree."""
        item_name = 'name relationship type'
        model = NameRelationshipType
        self._log_start_items(item_name)
        type_elements = tree.xpath(
            '/e:collection/e:name_relationship_types/e:name_relationship_type',
            namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                authority_id = self._get_referenced_eats_id(type_element,
                                                            'authority')
                name_relationship_type = type_element.text
                type_object = model(
                    name_relationship_type=name_relationship_type,
                    authority_id=authority_id)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_date_periods(self, tree):
        """Import date periods from XML tree."""
        item_name = 'date period'
        model = DatePeriod
        self._log_start_items(item_name)
        period_elements = tree.xpath(
            '/e:collection/e:date_periods/e:date_period',
            namespaces=NSMAP)
        for period_element in period_elements:
            self._log_xml(item_name, period_element)
            xml_id = self._get_element_id(period_element)
            eats_id = self._get_element_eats_id(period_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                date_period = period_element.text
                period_object = model(date_period=date_period)
                period_object.save()
                eats_id = period_object.id
                self._add_eats_id(period_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_date_types(self, tree):
        """Import date types from XML tree."""
        item_name = 'date type'
        model = DateType
        self._log_start_items(item_name)
        type_elements = tree.xpath('/e:collection/e:date_types/e:date_type',
                                   namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                date_type = type_element.text
                type_object = model(date_type=date_type)
                type_object.save()
                eats_id = type_object.id
                self._add_eats_id(type_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_calendars(self, tree):
        """Import calendars from XML tree."""
        item_name = 'calendar'
        model = Calendar
        self._log_start_items(item_name)
        calendar_elements = tree.xpath('/e:collection/e:calendars/e:calendar',
                                       namespaces=NSMAP)
        for calendar_element in calendar_elements:
            self._log_xml(item_name, calendar_element)
            xml_id = self._get_element_id(calendar_element)
            eats_id = self._get_element_eats_id(calendar_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                self._check_add_infrastructure_permission()
                calendar = calendar_element.text
                calendar_object = model(calendar=calendar)
                calendar_object.save()
                eats_id = calendar_object.id
                self._add_eats_id(calendar_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_authority_records(self, tree):
        """Import authority records from XML tree."""
        item_name = 'authority record'
        model = AuthorityRecord
        self._log_start_items(item_name)
        record_elements = tree.xpath(
            '/e:collection/e:authority_records/e:authority_record',
            namespaces=NSMAP)
        for record_element in record_elements:
            self._log_xml(item_name, record_element)
            xml_id = self._get_element_id(record_element)
            eats_id = self._get_element_eats_id(record_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                authority_id = self._get_referenced_eats_id(record_element,
                                                            'authority')
                self._check_add_permission(authority=authority_id)
                if record_element.get('auto_create_data'):
                    authority = Authority.objects.get(pk=authority_id)
                    record_data = get_new_authority_record_details(authority)
                    system_id = record_data['id']
                    is_complete_id = record_data['is_complete_id']
                    system_url = record_data['url']
                    is_complete_url = record_data['is_complete_url']
                    # Add the created data to the XML.
                    id_element = etree.SubElement(record_element,
                                                  EATS + 'authority_system_id')
                    id_element.set('is_complete',
                                   self._get_XML_boolean(is_complete_id))
                    id_element.text = system_id
                    url_element = etree.SubElement(
                        record_element, EATS + 'authority_system_url')
                    url_element.set('is_complete',
                                    self._get_XML_boolean(is_complete_url))
                    url_element.text = system_url
                else:
                    system_id_element = record_element.xpath(
                        'e:authority_system_id', namespaces=NSMAP)[0]
                    system_id = self._get_text_from_XML(system_id_element, '.')
                    is_complete_id = self._get_boolean(system_id_element,
                                                       'is_complete')
                    system_url_element = record_element.xpath(
                        'e:authority_system_url', namespaces=NSMAP)[0]
                    system_url = self._get_text_from_XML(system_url_element,
                                                         '.')
                    is_complete_url = self._get_boolean(system_url_element,
                                                        'is_complete')
                record_object = AuthorityRecord(
                    authority_id=authority_id, authority_system_id=system_id,
                    is_complete_id=is_complete_id,
                    authority_system_url=system_url,
                    is_complete_url=is_complete_url)
                record_object.save()
                eats_id = record_object.id
                self._add_eats_id(record_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_entities(self, tree):
        """Import entities from XML tree."""
        item_name = 'entity'
        model = Entity
        self._log_start_items(item_name)
        entity_elements = tree.xpath('/e:collection/e:entities/e:entity',
                                     namespaces=NSMAP)
        for entity_element in entity_elements:
            self._log_xml(item_name, entity_element)
            xml_id = self._get_element_id(entity_element)
            eats_id = self._get_element_eats_id(entity_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                entity_object = model()
                entity_object.save(create_existence=False)
                eats_id = entity_object.id
                self._add_eats_id(entity_element, eats_id)
            # Import all property assertions.
            self._import_existences(entity_element, eats_id)
            self._import_entity_types(entity_element, eats_id)
            self._import_entity_notes(entity_element, eats_id)
            self._import_entity_references(entity_element, eats_id)
            self._import_names(entity_element, eats_id)
            self._import_name_relationships(entity_element, eats_id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_existences(self, entity_element, entity_id):
        """Import existences for entity from XML element."""
        item_name = 'existence'
        model = PropertyAssertion
        existence_elements = entity_element.xpath(
            'e:existence_assertions/e:existence_assertion', namespaces=NSMAP)
        for existence_element in existence_elements:
            self._log_xml(item_name, existence_element)
            xml_id = self._get_element_id(existence_element)
            eats_id = self._get_element_eats_id(existence_element)
            if eats_id:
                assertion_object = self._check_object_exists(
                    model, eats_id, xml_id, entity_id, 'existence')
            else:
                existence_object = Existence()
                existence_object.save()
                existence_id = existence_object.id
                is_preferred = self._get_boolean(existence_element,
                                                 'is_preferred')
                authority_record_id = self._get_referenced_eats_id(
                    existence_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    existence_id=existence_id, is_preferred=is_preferred)
                assertion_object.save()
                self._add_eats_id(existence_element, assertion_object.id)
            self._import_dates(existence_element, assertion_object.id)

    def _import_entity_types(self, entity_element, entity_id):
        """Import entity types for entity from XML element."""
        item_name = 'entity type'
        model = PropertyAssertion
        type_elements = entity_element.xpath(
            'e:entity_type_assertions/e:entity_type_assertion',
            namespaces=NSMAP)
        for type_element in type_elements:
            self._log_xml(item_name, type_element)
            xml_id = self._get_element_id(type_element)
            eats_id = self._get_element_eats_id(type_element)
            if eats_id:
                assertion_object = self._check_object_exists(
                    model, eats_id, xml_id, entity_id, 'entity_type')
            else:
                authority_record_id = self._get_referenced_eats_id(
                    type_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                entity_type_id = self._get_referenced_eats_id(type_element,
                                                              'entity_type')
                self._check_type_authority(entity_type_id, EntityTypeList,
                                           authority_record_id, xml_id)
                type_object = EntityType(entity_type_id=entity_type_id)
                type_object.save()
                is_preferred = self._get_boolean(type_element, 'is_preferred')
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    entity_type_id=type_object.id, is_preferred=is_preferred)
                try:
                    assertion_object.save()
                except Exception:
                    raise EATSImportError(
                        'Could not save entity type assertion %s' % xml_id)
                self._add_eats_id(type_element, assertion_object.id)
            self._import_dates(type_element, assertion_object.id)

    def _import_entity_notes(self, entity_element, entity_id):
        """Import entity notes for entity from XML element."""
        item_name = 'entity note'
        model = PropertyAssertion
        note_elements = entity_element.xpath(
            'e:entity_note_assertions/e:entity_note_assertion',
            namespaces=NSMAP)
        for note_element in note_elements:
            self._log_xml(item_name, note_element)
            xml_id = self._get_element_id(note_element)
            eats_id = self._get_element_eats_id(note_element)
            if eats_id:
                assertion_object = self._check_object_exists(
                    model, eats_id, xml_id, entity_id, 'note')
            else:
                is_preferred = self._get_boolean(note_element, 'is_preferred')
                authority_record_id = self._get_referenced_eats_id(
                    note_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                is_internal = self._get_boolean(note_element, 'is_internal')
                note = self._get_text_from_XML(note_element, 'e:note')
                note_object = EntityNote(note=note, is_internal=is_internal)
                note_object.save()
                note_id = note_object.id
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    note_id=note_id, is_preferred=is_preferred)
                try:
                    assertion_object.save()
                except Exception:
                    raise EATSImportError(
                        'Could not save entity note assertion %s' % xml_id)
                self._add_eats_id(note_element, assertion_object.id)
            self._import_dates(note_element, assertion_object.id)

    def _import_entity_references(self, entity_element, entity_id):
        """Import entity references for entity from XML element."""
        item_name = 'entity reference'
        model = PropertyAssertion
        self._log_start_items(item_name)
        reference_elements = entity_element.xpath(
            'e:entity_reference_assertions/e:entity_reference_assertion',
            namespaces=NSMAP)
        for reference_element in reference_elements:
            self._log_xml(item_name, reference_element)
            xml_id = self._get_element_id(reference_element)
            eats_id = self._get_element_eats_id(reference_element)
            if eats_id:
                assertion_object = self._check_object_exists(
                    model, eats_id, xml_id, entity_id, 'reference')
            else:
                authority_record_id = self._get_referenced_eats_id(
                    reference_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                is_preferred = self._get_boolean(reference_element,
                                                 'is_preferred')
                label = self._get_text_from_XML(reference_element, 'e:label')
                url = self._get_text_from_XML(reference_element, 'e:url')
                reference_object = EntityReference(url=url, label=label)
                reference_object.save()
                reference_id = reference_object.id
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    reference_id=reference_id, is_preferred=is_preferred)
                try:
                    assertion_object.save()
                except Exception:
                    raise EATSImportError(
                        'Could not save entity reference assertion %s' % xml_id)
                self._add_eats_id(reference_element, assertion_object.id)
            self._import_dates(reference_element, assertion_object.id)

    def _import_names(self, entity_element, entity_id):
        """Import names for entity from XML element."""
        item_name = 'name'
        model = PropertyAssertion
        name_elements = entity_element.xpath(
            'e:name_assertions/e:name_assertion', namespaces=NSMAP)
        for name_element in name_elements:
            self._log_xml(item_name, name_element)
            xml_id = self._get_element_id(name_element)
            eats_id = self._get_element_eats_id(name_element)
            if eats_id:
                assertion_object = self._check_object_exists(
                    model, eats_id, xml_id, entity_id, 'name')
            else:
                authority_record_id = self._get_referenced_eats_id(
                    name_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                is_preferred = self._get_boolean(name_element, 'is_preferred')
                language_id = self._get_referenced_eats_id(name_element,
                                                           'language')
                script_id = self._get_referenced_eats_id(
                    name_element, 'script')
                name_type_id = self._get_referenced_eats_id(
                    name_element, 'type', 'name type')
                self._check_type_authority(name_type_id, NameType,
                                           authority_record_id, xml_id)
                display_form = self._get_text_from_XML(name_element,
                                                       'e:display_form')
                name_object = Name(name_type_id=name_type_id,
                                   language_id=language_id, script_id=script_id,
                                   display_form=display_form)
                name_object.save()
                name_id = name_object.id
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    name_id=name_id, is_preferred=is_preferred)
                try:
                    assertion_object.save()
                except Exception:
                    raise EATSImportError(
                        'Could not save name assertion %s' % xml_id)
                # Save the name again to generate the search names.
                name_object.save()
                eats_id = assertion_object.id
                self._add_eats_id(name_element, eats_id)
                self._import_name_parts(name_element, name_id,
                                        authority_record_id)
            self._import_dates(name_element, assertion_object.id)
            self._create_mapping(item_name, xml_id, eats_id)

    def _import_name_parts(self, name_element, name_id, authority_record_id):
        """Import name parts for entity from XML element."""
        item_name = 'name part'
        part_elements = name_element.xpath('e:name_parts/e:name_part',
                                           namespaces=NSMAP)
        for part_element in part_elements:
            self._log_xml(item_name, part_element)
            type_id = self._get_referenced_eats_id(part_element, 'type',
                                                   'name part type')
            self._check_type_authority(type_id, NamePartType,
                                       authority_record_id, '')
            language_id = self._get_referenced_eats_id(
                part_element, 'language')
            script_id = self._get_referenced_eats_id(part_element, 'script')
            name_part = self._get_text_from_XML(part_element, '.')
            part_object = NamePart(
                name_id=name_id, name_part_type_id=type_id,
                language_id=language_id, script_id=script_id,
                name_part=name_part)
            part_object.save()

    def _import_entity_relationships(self, tree):
        """Import entity relationships from XML tree."""
        item_name = 'entity relationship'
        model = PropertyAssertion
        relationship_elements = tree.xpath(
            '/e:collection/e:entities/e:entity/e:entity_relationship_assertions/e:entity_relationship_assertion',
            namespaces=NSMAP)
        for relationship_element in relationship_elements:
            self._log_xml(item_name, relationship_element)
            xml_id = self._get_element_id(relationship_element)
            eats_id = self._get_element_eats_id(relationship_element)
            if eats_id:
                assertion_object = self._check_object_exists(model, eats_id,
                                                             xml_id)
            else:
                entity_element = relationship_element.getparent().getparent()
                entity_id = self._get_referenced_eats_id(
                    entity_element, XML + 'id', 'entity')
                authority_record_id = self._get_referenced_eats_id(
                    relationship_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                related_entity_id = self._get_referenced_eats_id(
                    relationship_element, 'related_entity', 'entity')
                relationship_type_id = self._get_referenced_eats_id(
                    relationship_element, 'type', 'entity relationship type')
                self._check_type_authority(relationship_type_id,
                                           EntityRelationshipType,
                                           authority_record_id, xml_id)
                is_preferred = self._get_boolean(relationship_element,
                                                 'is_preferred')
                relationship_object = EntityRelationship(
                    related_entity_id=related_entity_id,
                    entity_relationship_type_id=relationship_type_id)
                relationship_object.save()
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    entity_relationship_id=relationship_object.id,
                    is_preferred=is_preferred)
                try:
                    assertion_object.save()
                except Exception:
                    raise EATSImportError(
                        'Could not save entity relationship assertion %s' % xml_id)
                self._add_eats_id(relationship_element, assertion_object.id)
                self._import_entity_relationship_notes(relationship_element,
                                                       relationship_object.id)
            self._import_dates(relationship_element, assertion_object.id)

    def _import_entity_relationship_notes(self, relationship_element,
                                          relationship_id):
        """Import entity relationship notes for relationship from XML
        element."""
        item_name = 'entity relationship note'
        note_elements = relationship_element.xpath(
            'e:entity_relationship_notes/e:entity_relationship_note',
            namespaces=NSMAP)
        for note_element in note_elements:
            self._log_xml(item_name, note_element)
            note_data = {'is_internal': self._get_boolean(note_element, 'is_internal'),
                         'note': note_element.text,
                         'entity_relationship_id': relationship_id}
            note_object = EntityRelationshipNote(**note_data)
            note_object.save()

    def _import_name_relationships(self, entity_element, entity_id):
        """Import name relationships for entity from XML element."""
        item_name = 'name relationship'
        model = PropertyAssertion
        relationship_elements = entity_element.xpath(
            'e:name_relationship_assertions/e:name_relationship_assertion',
            namespaces=NSMAP)
        for relationship_element in relationship_elements:
            self._log_xml(item_name, relationship_element)
            xml_id = self._get_element_id(relationship_element)
            eats_id = self._get_element_eats_id(relationship_element)
            if eats_id:
                assertion_object = self._check_object_exists(
                    model, eats_id, xml_id, entity_id, 'name_relationship')
            else:
                authority_record_id = self._get_referenced_eats_id(
                    relationship_element, 'authority_record')
                self._check_add_permission(record=authority_record_id)
                is_preferred = self._get_boolean(relationship_element,
                                                 'is_preferred')
                relationship_type_id = self._get_referenced_eats_id(
                    relationship_element, 'type', 'name relationship type')
                self._check_type_authority(relationship_type_id,
                                           NameRelationshipType,
                                           authority_record_id, xml_id)
                name_assertion_id = self._get_referenced_eats_id(
                    relationship_element, 'name')
                name_id = self._get_name_id_from_assertion_id(
                    name_assertion_id)
                related_name_assertion_id = self._get_referenced_eats_id(
                    relationship_element, 'related_name', 'name')
                related_name_id = self._get_name_id_from_assertion_id(
                    related_name_assertion_id)
                relationship_object = NameRelationship(
                    name_id=name_id, related_name_id=related_name_id,
                    name_relationship_type_id=relationship_type_id)
                relationship_object.save()
                assertion_object = PropertyAssertion(
                    entity_id=entity_id,
                    authority_record_id=authority_record_id,
                    name_relationship_id=relationship_object.id,
                    is_preferred=is_preferred)
                try:
                    assertion_object.save()
                except Exception:
                    raise EATSImportError(
                        'Could not save name relationship assertion %s' % xml_id)
                self._add_eats_id(relationship_element, assertion_object.id)
            self._import_dates(relationship_element, assertion_object.id)

    def _import_dates(self, assertion_element, assertion_id):
        """Import dates for assertion from XML element."""
        item_name = 'date'
        model = Date
        date_elements = assertion_element.xpath('e:dates/e:date',
                                                namespaces=NSMAP)
        for date_element in date_elements:
            self._log_xml(item_name, date_element)
            xml_id = self._get_element_id(date_element)
            eats_id = self._get_element_eats_id(date_element)
            if eats_id:
                self._check_object_exists(model, eats_id, xml_id)
            else:
                date_data = {'assertion_id': assertion_id}
                date_data['date_period_id'] = self._get_referenced_eats_id(
                    date_element, 'period', 'date period')
                for child in date_element:
                    if child.tag == EATS + 'assembled_form':
                        continue
                    date_type = child.get('type')
                    date_data[date_type] = child.xpath(
                        'e:raw', namespaces=NSMAP)[0].text
                    date_data[date_type + '_normalised'] = child.xpath(
                        'e:normalised', namespaces=NSMAP)[0].text
                    date_data[date_type + '_calendar_id'] = self._get_referenced_eats_id(
                        child, 'calendar')
                    date_data[date_type + '_type_id'] = self._get_referenced_eats_id(
                        child, 'date_type')
                    date_data[date_type + '_confident'] = self._get_boolean(
                        child, 'confident')
                date_object = Date(**date_data)
                date_object.save()
                self._add_eats_id(date_element, date_object.id)

    def _get_referenced_eats_id(self, element, attribute_name, map_key=None):
        """Return the EATS ID for the object referenced in
        attribute_name on element."""
        # Due to the mapping, we are assured that the reference is to the
        # correct type of object.
        import_id = element.get(attribute_name)
        if not import_id:
            return None
        if not map_key:
            map_key = attribute_name.replace('_', ' ')
        eats_id = self._xml_object_map[map_key].get(import_id)
        return eats_id

    def _create_mapping(self, map_name, xml_id, object_id):
        """Add a mapping in map_name between xml_id and
        object_id. This allows for resolving references within the
        import file which are done via XML IDs."""
        self._xml_object_map[map_name][xml_id] = object_id
        logging.debug('Mapped %s XML ID %s to database ID %d'
                      % (map_name, xml_id, object_id))

    def _check_add_infrastructure_permission(self):
        """Raise an exception if the user does not have permission to
        add a new infrastructure object."""
        if not self._has_add_infrastructure_permission:
            message = 'The user performing the import does not have permission to add infrastructural data, as the import file demands'
            raise EATSImportError(message)

    def _check_add_permission(self, authority=None, record=None):
        """Raise an exception if the user does not have permission to
        add a new object associated with a particular authority.

        Arguments:
        authority -- ID of Authority object in database
        record -- ID of AuthorityRecord object in database

        """
        if not self._user.is_superuser:
            authority_id = authority or \
                AuthorityRecord.objects.get(pk=record).authority_id
            if authority_id not in self._user_authority_ids:
                authority = Authority.objects.get(pk=authority_id)
                message = 'The user performing the import does not have permission to add data associated with %s, as the import file demands' \
                    % (str(authority))
                raise EATSImportError(message)

    @staticmethod
    def _validate(tree):
        """Validate the XML document against the RelaxNG schema."""
        logging.debug('Parsing RelaxNG schema')
        relaxng_doc = etree.parse(RNG_PATH)
        relaxng = etree.RelaxNG(relaxng_doc)
        logging.debug('Validating import file')
        if not relaxng.validate(tree):
            message = 'RelaxNG validation of the import document failed: %s' % \
                (relaxng.error_log.last_error)
            logging.error(message)
            raise EATSImportError(message)

    @staticmethod
    def _get_element_id(element):
        """Return the string ID of element."""
        return element.get(XML + 'id')

    @staticmethod
    def _get_element_eats_id(element):
        """Return the integer EATS ID of element."""
        eats_id = element.get('eats_id')
        if eats_id:
            eats_id = int(eats_id)
        return eats_id

    @staticmethod
    def _check_object_exists(model, eats_id, xml_id, entity_id=None,
                             relating_field=None):
        """Return object with eats_id in model. Raises an exception if
        that object does not exist. If entity_id and property_model
        are supplied, checks also that the object links to both.

        Arguments:
        model -- Model class that object is an instance of
        eats_id -- ID of object in the database
        xml_id -- ID of element in the import XML
        entity_id -- ID of Entity object in the database to which the
                     object being checked must related
        relating_field -- string name of field used to relate to the
                          property Model object that a
                          PropertyAssertion object must relate to

        """
        logging.debug('Checking that %s object with EATS id %s and XML id %s exists'
                      % (model._meta.object_name, eats_id, xml_id))
        try:
            model_object = model.objects.get(pk=eats_id)
        except model.DoesNotExist:
            message = '%s object with EATS ID %d, XML ID %s does not exist in EATS.' \
                % (model._meta.object_name, eats_id, xml_id)
            raise EATSImportError(message)
        if entity_id and model_object.entity_id != entity_id:
            message = '%s object with EATS ID %d, XML ID %s is not associated with the specified entity with EATS ID %s.' \
                % (model._meta.object_name, eats_id, xml_id, entity_id)
            raise EATSImportError(message)
        if relating_field and getattr(model_object, relating_field) is None:
            message = '%s object with EATS ID %d, XML ID %s is not asserting a %s property as it ought to be.' \
                % (model._meta.object_name, eats_id, xml_id, relating_field)
            raise EATSImportError(message)
        return model_object

    @staticmethod
    def _get_text_from_XML(element, xpath):
        """Return the string value of the result of performing xpath query on
        element."""
        container = element.xpath(xpath + '/text()', namespaces=NSMAP)
        if container:
            text = str(container[0]).strip()
        else:
            text = ''
        return text

    @staticmethod
    def _check_type_authority(object_id, model, authority_record_id, xml_id):
        """Raise an error if the ID of the Authority object associated
        with model object with object_id does not match the authority
        referenced by the AuthorityRecord object with authority_id."""
        type_object = model.objects.get(pk=object_id)
        authority_record = AuthorityRecord.objects.get(pk=authority_record_id)
        if type_object.authority_id != authority_record.authority_id:
            message = 'Mismatched authorities: element with XML ID %s references authority with EATS ID %d in its authority record, but a %s type associated with authority with EATS ID %d' \
                % (xml_id, authority_record.authority_id,
                   model._meta.object_name, type_object.authority_id)
            raise EATSImportError(message)
        return

    @staticmethod
    def _get_boolean(element, attribute=None):
        """Return Python boolean for text value of element's attribute, or
        element's text content is attribute is None."""
        if attribute:
            value = element.get(attribute)
        else:
            value = element.text
        if value in ('true', '1'):
            return True
        return False

    @staticmethod
    def _get_XML_boolean(boolean):
        """Return boolean (a Python boolean) in a format suitable for use in
        an XML document using the XML Schema boolean datatype."""
        return str(boolean).lower()

    @staticmethod
    def _get_name_id_from_assertion_id(assertion_id):
        """Return the ID of the Name object associated with the
        PropertyAssertion with id assertion_id)."""
        assertion = PropertyAssertion.objects.get(pk=assertion_id)
        return assertion.name_id

    @staticmethod
    def _add_eats_id(element, eats_id):
        """Add an eats_id attribute with value eats_id to element."""
        element.set('eats_id', str(eats_id))

    @staticmethod
    def _log_start_items(item_name):
        """Log the start of importing item_name items."""
        logging.debug('Importing %s items' % (item_name))

    @staticmethod
    def _log_xml(item_name, element):
        """Log the importing of item_name XML from element."""
        logging.debug('Importing %s from XML: %s'
                      % (item_name, etree.tostring(element)))
