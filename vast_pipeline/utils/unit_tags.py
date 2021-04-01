from django import template


register = template.Library()


@register.filter
def deg_to_arcsec(angle: float) -> float:
    """
    Convert degrees to arcseconds.

    Args:
        angle: Angle in units of degrees.

    Returns:
        angle: Angle in units of arcseconds.
    """
    return float(angle) * 3600.


@register.filter
def deg_to_arcmin(angle: float) -> float:
    """
    Convert degrees to arcminutes.

    Args:
        angle: Angle in units of degrees.

    Returns:
        Angle in units of arcminutes.
    """
    return float(angle) * 60.
