"""Tag library for customising the model data to be retrieved by the
user profile."""

from django import template
from django.template import Variable

register = template.Library()


@register.tag(name='eats_user_wrap')
def supply_user_parameters(parser, token):
    """Call a method on object with parameters taken from the user
    preferences and set the result as variable in context.

    Format: {% user_wrap object method variable %}

    """
    try:
        tag_name, object, method, variable = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            '%r tag requires exactly three arguments' % token.contents.split()[0])
    return UserCustomisedNode(object, method, variable)


class UserCustomisedNode (template.Node):
    def __init__(self, object_string, method_name, variable_name):
        self.object_string = Variable(object_string)
        self.method_name = method_name
        self.variable_name = variable_name

    def render(self, context):
        try:
            object = self.object_string.resolve(context)
            method = getattr(object, self.method_name)
            context[self.variable_name] = method(context['user_preferences'])
            return ''
        except template.VariableDoesNotExist:
            context[self.variable_name] = None
            return ''
        except AttributeError:
            context[self.variable_name] = None
            return ''
