from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """
    Splits the string by the given argument.
    Usage: {{ "a,b,c"|split:"," }}
    """
    if value:
        return value.split(arg)
    return []
