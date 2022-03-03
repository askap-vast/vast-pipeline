from typing import Dict, Optional
from django.conf import settings
from django.http import HttpRequest
from vast_pipeline import __version__


def maintainance_banner(request: HttpRequest) -> Dict[str, Optional[str]]:
    """
    Generates the maintainance banner for the web server if a message has been
    set in the Django settings.

    Args:
        request (HttpRequest): The web server request.

    Returns:
        Dictionary representing the JSON object with the maintainance message.
    """
    if settings.PIPELINE_MAINTAINANCE_MESSAGE:
        return {"maintainance_message": settings.PIPELINE_MAINTAINANCE_MESSAGE}

    return {"maintainance_message": None}


def pipeline_version(request: HttpRequest) -> Dict[str, Optional[str]]:
    """Adds the pipeline version to the template context.

    Args:
        request (HttpRequest): The web server request.

    Returns:
        Key-value pairs to add to the template context.
    """
    url: Optional[str] = None
    if not __version__.endswith("dev"):
        url = f"https://github.com/askap-vast/vast-pipeline/releases/tag/v{__version__}"

    return {
        "pipeline_version": __version__,
        "pipeline_version_url": url,
    }
