from django.conf import settings


def maintainance_banner(request):
    if settings.PIPELINE_MAINTAINANCE_MESSAGE:
     return {'maintainance_message': settings.PIPELINE_MAINTAINANCE_MESSAGE}

    return {'maintainance_message': None}
