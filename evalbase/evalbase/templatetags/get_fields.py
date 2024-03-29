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
