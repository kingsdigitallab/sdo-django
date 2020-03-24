"""Module defining the language rules for English."""


def sort_parts(parts):
    """Return a list of name parts sorted into display order for the
    language."""
    given = family = title = ''
    for part in parts:
        system_name_part_type = str(
            part.name_part_type.system_name_part_type)
        name_part = part.name_part
        if system_name_part_type == 'given':
            given = name_part
        elif system_name_part_type == 'family':
            family = name_part
        elif system_name_part_type == 'terms of address':
            title = name_part
    return (title, given, family)
