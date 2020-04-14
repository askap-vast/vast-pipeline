from django import template


register = template.Library()

@register.filter
def deg_to_arcsec(angle):
    """
    convert jansky to millijansky
    """
    return float(angle) * 3600.