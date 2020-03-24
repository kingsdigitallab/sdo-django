# -*- coding: utf-8 -*-
from os.path import abspath, dirname, join
import io
import unittest

from lxml import etree
from django.core.management import call_command

from eats.models import Entity, User
import eats.eatsml.importer as importer
import eats.eatsml.exporter as exporter

# Full path to this directory.
PATH = abspath(dirname(__file__))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(KnownValuesTestCase('test_import_export'))
    suite.addTest(KnownValuesTestCase('test_import_results'))
    suite.addTest(BadInputTestCase('test_missing_existence'))
    return suite


class KnownValuesTestCase (unittest.TestCase):

    def setUp(self):
        # It is not sufficient just to delete the data in the test
        # database, as the sequences for the IDs will be modified, and
        # they need to be reset. Therefore flush the test database.
        call_command('flush', verbosity=0, interactive=False)
        user = User(username='superuser', first_name='super', last_name='user',
                    email='superuser@example.org', password='', is_staff=True,
                    is_active=True, is_superuser=True)
        user.save()
        self._importer = importer.Importer(user)
        self._exporter = exporter.Exporter()

    @staticmethod
    def get_c14n_string(tree):
        f = io.StringIO()
        tree.write_c14n(f)
        return f.getvalue()

    def test_import_export(self):
        # Import base data into empty database.
        self._importer.import_file(join(PATH, 'import1.xml'))
        # Import data (both new and modifications to existing objects).
        self._importer.import_file(join(PATH, 'import2.xml'))
        result_root = self._exporter.export_entities(Entity.objects.all())
        result_tree = etree.ElementTree(result_root)
        # We need to remove last_modified attributes from the export.
        xslt_doc = etree.parse(join(PATH, 'remove_last_modified.xsl'))
        transform = etree.XSLT(xslt_doc)
        xslt_result_tree = transform(result_tree)
        result = self.get_c14n_string(xslt_result_tree)
        base_tree = etree.parse(join(PATH, 'export.xml'))
        expected_result = self.get_c14n_string(base_tree)
        self.assertEqual(expected_result, result)

    def test_import_results(self):
        import_filepath = join(PATH, 'import1.xml')
        import_result_filepath = join(PATH, 'import-result.xml')
        result_raw_root, result_processed_root = self._importer.import_file(
            import_filepath)
        result_raw_tree = etree.ElementTree(result_raw_root)
        result_raw = self.get_c14n_string(result_raw_tree)
        result_processed_tree = etree.ElementTree(result_processed_root)
        result_processed = self.get_c14n_string(result_processed_tree)
        parser = etree.XMLParser(ns_clean=True, remove_blank_text=True)
        base_raw_tree = etree.parse(import_filepath, parser)
        base_raw = self.get_c14n_string(base_raw_tree)
        base_processed_tree = etree.parse(import_result_filepath, parser)
        base_processed = self.get_c14n_string(base_processed_tree)
        self.assertEqual((result_raw, result_processed),
                         (base_raw, base_processed))


class BadInputTestCase (unittest.TestCase):

    def setUp(self):
        # It is not sufficient just to delete the data in the test
        # database, as the sequences for the IDs will be modified, and
        # they need to be reset. Therefore flush the test database.
        call_command('flush', verbosity=0, interactive=False)
        user = User(username='superuser', first_name='super', last_name='user',
                    email='superuser@example.org', password='', is_staff=True,
                    is_active=True, is_superuser=True)
        user.save()
        self._importer = importer.Importer(user)

    def test_missing_existence(self):
        import_filepath = join(PATH, 'import-missing-existence.xml')
        self.assertRaises(importer.EATSImportError, self._importer.import_file,
                          import_filepath)
