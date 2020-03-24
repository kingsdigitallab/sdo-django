# -*- coding: utf-8 -*-
import unittest
import eats.names


def suite():
    suite = unittest.TestSuite()
    suite.addTest(SearchNameTestCase('test_clean_name'))
    suite.addTest(SearchNameTestCase('test_asciify_name'))
    suite.addTest(SearchNameTestCase('test_unpunctuate_name'))
    return suite


class SearchNameTestCase (unittest.TestCase):

    def test_clean_name(self):
        """Test that a name is properly cleaned."""
        names = (
            ('Alan Smith', 'Alan Smith'),
            ('alan Smith', 'alan Smith'),
            ('War\'s End', 'War\N{RIGHT SINGLE QUOTATION MARK}s End'),
            ('\'A flight of swans\': a lesson in aerodynamics',
             '\N{LEFT SINGLE QUOTATION MARK}A flight of swans\N{RIGHT SINGLE QUOTATION MARK}: a lesson in aerodynamics'),
            ('"A flight of swans": a lesson in aerodynamics',
             '\N{LEFT DOUBLE QUOTATION MARK}A flight of swans\N{RIGHT DOUBLE QUOTATION MARK}: a lesson in aerodynamics'),
            ('"\'A flight of swans\': a lesson in aerodynamics"',
             '\N{LEFT DOUBLE QUOTATION MARK}\N{LEFT SINGLE QUOTATION MARK}A flight of swans\N{RIGHT SINGLE QUOTATION MARK}: a lesson in aerodynamics\N{RIGHT DOUBLE QUOTATION MARK}'),
            ('\'Good-bye dear,\' shouted loudly',
             '\N{LEFT SINGLE QUOTATION MARK}Good-bye dear,\N{RIGHT SINGLE QUOTATION MARK} shouted loudly'),
            ('M\N{LATIN SMALL LETTER A WITH MACRON}ori',
             'M\N{LATIN SMALL LETTER A WITH MACRON}ori'),
            ('Ma\N{COMBINING MACRON}ori',
             'M\N{LATIN SMALL LETTER A WITH MACRON}ori'),
        )
        for name in names:
            test_name = name[1]
            cleaned_name = eats.names.clean_name(name[0])
            self.assertEqual(cleaned_name, test_name)

    def test_asciify_name(self):
        """Test that a name is properly converted to ASCII."""
        names = (
            ('Alan Smith', 'en', 'Latn', 'Alan Smith'),
            ('François', 'fr', 'Latn', 'Francois'),
            ('Ægypt', 'en', 'Latn', 'AEgypt'),
        )
        for name in names:
            test_name = name[3]
            asciified_name = eats.names.asciify_name(name[0])
            self.assertEqual(asciified_name, test_name)

    def test_unpunctuate_name(self):
        """Test that punctuation is correctly removed from a name."""
        names = (
            ('Alan Smith', 'Alan Smith'),
            ('François', 'François'),
            ('Smith, Alan', 'Smith Alan'),
            ('War\'s End', 'Wars End'),
            ('"A flight of swans": a lesson in aerodynamics',
             'A flight of swans a lesson in aerodynamics'),
            ('Never say never (again)', 'Never say never again')
        )
        for name in names:
            test_name = name[1]
            unpunctuated_name = eats.names.unpunctuate_name(name[0])
            self.assertEqual(unpunctuated_name, test_name)
