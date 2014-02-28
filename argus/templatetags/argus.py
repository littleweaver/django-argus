from __future__ import absolute_import

from django import template


register = template.Library()


@register.filter(name='abs')
def absolute_value(value):
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return ''
