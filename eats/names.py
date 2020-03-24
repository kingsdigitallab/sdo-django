# -*- coding: utf-8 -*-
"""Module for handling names."""

import re
import unicodedata

preceding_char = r'[\w,;.?!)}\]]'
right_apos_pattern = re.compile("(%s)'" % preceding_char, re.UNICODE)
right_quote_pattern = re.compile('(%s)"' % preceding_char, re.UNICODE)
macron_pattern = re.compile('([aeiou])\N{COMBINING MACRON}', re.UNICODE)


def clean_name(name):
    """Return name cleaned up.

    Change ASCII apostrophes and quotation marks into Unicode
    versions. This is not necessarily going to be correct, but it
    should get it right most of the time, and it's always possible to
    manually fix a mistake made here (assuming that the ASCII
    characters should never be used in the clean form).

    Further, put the name into a normalised Unicode form (NFC).

    """
    name = right_apos_pattern.sub(r'\1' + '\N{RIGHT SINGLE QUOTATION MARK}',
                                  name)
    name = name.replace("'", '\N{LEFT SINGLE QUOTATION MARK}')
    name = right_quote_pattern.sub(r'\1' + '\N{RIGHT DOUBLE QUOTATION MARK}',
                                   name)
    name = name.replace('"', '\N{LEFT DOUBLE QUOTATION MARK}')
    name = unicodedata.normalize('NFC', name)
    return name


def create_search_forms(name, language_code, script_code):
    """Return a list of names suitable for searching.

    Arguments:
    name -- string name
    language_code -- string code of language
    script_code -- string code of script

    """
    # QAZ: It would be useful if something could be done here (or
    # wherever is most appropriate) to handle the case where names are
    # assembled without spaces between the parts (eg, Chinese), since
    # this means that whatever part(s) come after the first will not
    # be found in a search.
    name = str(name)
    search_forms = [name]
    if script_code == 'Latn':
        ascii_form = asciify_name(name)
        if ascii_form and ascii_form != name:
            search_forms.append(ascii_form)
        macron_as_double_form = demacronise_name(name)
        if macron_as_double_form != name:
            search_forms.append(macron_as_double_form)
    abbreviated_form = abbreviate_name(name, language_code, script_code)
    if abbreviated_form != name:
        search_forms.append(abbreviated_form)
    unpunctuated_form = unpunctuate_name(name)
    if unpunctuated_form != name:
        search_forms.append(unpunctuated_form)
    return search_forms


def asciify_name(name):
    """Return name converted to ASCII.

    Arguments:
    name -- unicode string

    """
    substituted_form = substitute_ascii(name)
    normalised_form = unicodedata.normalize('NFD', substituted_form)
    ascii_form = str(normalised_form.encode('ascii', 'ignore'))
    return ascii_form


def substitute_ascii(name):
    """Return name with various non-ASCII characters replaced with ASCII
    equivalents."""
    substitutions = [('Æ', 'AE'), ('æ', 'ae'), ('Œ', 'OE'),
                     ('œ', 'oe'), ('ß', 'ss'), ('ſ', 's'),
                     ('‘', "'")]
    for original, substitute in substitutions:
        name = name.replace(original, substitute)
    return name


def demacronise_name(name):
    """Return name with macronised vowels changed into double vowels."""
    substituted_form = substitute_ascii(name)
    normalised_form = unicodedata.normalize('NFD', substituted_form)
    demacronised_form = macron_pattern.sub(r'\1\1', normalised_form)
    return demacronised_form


def abbreviate_name(name, language_code, script_code):
    """Return name with full elements abbreviated."""
    if language_code == 'en':
        name = name.replace(' and ', ' & ')
    return name


def unpunctuate_name(name):
    """Return name with punctuation removed."""
    # QAZ: This does not work well in some cases, such as "On Self
    # Misery.—An Epigram", where "An" ends up joined to "Misery".
    char_array = []
    for character in name:
        category = unicodedata.category(character)
        # Punctuation categories start with 'P'.
        if category[0] != 'P':
            char_array.append(character)
    return ''.join(char_array)


def compile_variants(name_obj):
    """Return a list of variant names derived from name.

    Arguments:
    name -- Name object

    """
    # If there is a display name, then just use that. display_name is
    # used when there are no name parts, or when it is not possible to
    # automatically compile the name parts into a sensible/correct
    # whole, which is precisely what we're trying to do here.
    display_form = name_obj.display_form
    if display_form:
        return [display_form]
    main_form = assemble_name(name_obj)
    if not main_form:
        return []
    names = set()
    names.add(main_form)
    # This is a horrible hack in all ways! A few of its problems are:
    #
    #  * it only operates on names in Latin script, caring not at all
    #    about language (and not caring about other scripts)
    #  * it doesn't handle abbreviations beyond initialisms
    #  * it doesn't care about name parts other than terms of address,
    #    given and family, and this only if you use the exact terms
    #    the NZETC uses for these
    if name_obj.script.script_code == 'Latn':
        name_parts = name_obj.name_parts.all()
        given = family = toa = ''
        for name_part in name_parts:
            name_part_type = name_part.name_part_type.name_part_type
            if name_part_type == 'given':
                given = name_part.name_part
            elif name_part_type == 'family':
                family = name_part.name_part
            elif name_part_type == 'terms of address':
                toa = name_part.name_part
        if toa:
            toa = '%s ' % (toa)
        given_components = [(given_name, '%s.' % (given_name[0]))
                            for given_name in given.split()]
        if given_components:
            given_forms = assemble_given_components(given_components, 0)
            for given_form in given_forms:
                name = '%s%s %s' % (toa, given_form, family)
                names.add(name.strip())
                if family:
                    name = '%s, %s%s' % (family, toa, given_form)
                    names.add(name.strip())
        else:
            names.add('%s%s' % (toa, family))
    return list(names)


def assemble_given_components(components, index):
    forms = []
    later_forms = []
    if len(components) - 1 > index:
        later_forms = assemble_given_components(components, index + 1)
    for component in components[index]:
        forms.append(component)
        for part in later_forms:
            forms.append('%s %s' % (component, part))
    return forms


def assemble_name(name_obj):
    """Return a name assembled from its parts.

    Arguments:
    name_obj -- Name object

    """
    name_parts = name_obj.name_parts.all()
    if not name_parts:
        return ''
    language = my_import('eats.languages.%s' % name_obj.language.language_code)
    script = my_import('eats.scripts.%s' % name_obj.script.script_code)
    # Order parts based on language of name.
    name_parts = language.sort_parts(name_parts)
    # Remove empty name parts.
    name_parts = [name_part for name_part in name_parts if name_part]
    # Add punctuation between parts based on script of name.
    return script.separator.join(name_parts) or ''


def my_import(name):
    module = __import__(name)
    components = name.split('.')
    for component in components[1:]:
        module = getattr(module, component)
    return module
