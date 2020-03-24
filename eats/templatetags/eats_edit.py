"""Tag library for pieces of edit functionality."""

from django import template
from django.template import Variable

register = template.Library()


@register.tag(name='eats_get_keyed_forms')
def supply_user_parameters(parser, token):
    """Get a list of forms from a supplied EATS FormSet using the supplied
    key. Set the result as variable in context.

    Format: {% get_keyed_forms form_set key variable %}

    """
    try:
        tag_name, form_set, key, variable = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires exactly three arguments' % token.contents.split()[0])
    return KeyedFormsNode(form_set, key, variable)


class KeyedFormsNode (template.Node):

    def __init__(self, form_set_string, key_name, variable_name):
        self.form_set_string = Variable(form_set_string)
        self.key_name = Variable(key_name)
        self.variable_name = variable_name

    def render(self, context):
        try:
            form_set = self.form_set_string.resolve(context)
            key = self.key_name.resolve(context)
            context[self.variable_name] = form_set.get_forms(key)
            return ''
        except template.VariableDoesNotExist:
            context[self.variable_name] = []
            return ''
