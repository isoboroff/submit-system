from django import template

register = template.Library()

@register.filter
def get_fields(obj):
    return obj._meta.get_fields()

@register.filter
def get_field_value(obj, k):
    try:
        return k.value_from_object(obj)
    except Exception:
        return None

@register.filter(name='get')
def get(o, index):
    try:
        return o[index]
    except:
        return settings.TEMPLATE_STRING_IF_INVALID


@register.filter(name='getattr')
def getattrfilter(o, attr):
    try:
        return getattr(o, attr)
    except:
        return settings.TEMPLATE_STRING_IF_INVALID
