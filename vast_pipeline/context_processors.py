from typing import Dict
from django.conf import settings
from django.http import HttpRequest


def maintainance_banner(request: HttpRequest) -> Dict[str, str]:
    """
    Generates the maintainance banner for the web server if a message has been
    set in the Django settings.

    Args:
        request (HttpRequest): The web server request.

    Returns:
        Dictionary representing the JSON object with the maintainance message.
    """
    if settings.PIPELINE_MAINTAINANCE_MESSAGE:
        return {'maintainance_message': settings.PIPELINE_MAINTAINANCE_MESSAGE}

    return {'maintainance_message': None}
