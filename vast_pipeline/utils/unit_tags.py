from django import template


register = template.Library()


@register.filter
def deg_to_arcsec(angle):
    """
    convert degrees to arcseconds
    """
    return float(angle) * 3600.


@register.filter
def deg_to_arcmin(angle):
    """
    convert degrees to arcmins
    """
    return float(angle) * 60.
