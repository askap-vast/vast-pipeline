from django.shortcuts import render
from rest_framework import viewsets

from .models import Dataset, Image, Source
from .serializers import DatasetSerializer, ImageSerializer, SourceSerializer


# Datasets table
def dataset_index(request):
    cols = ['time', 'name', 'path', 'comment', 'images', 'catalogs']
    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Datasets',
                'description': 'List of Datasets below',
            },
            'datatable': {
                'api': '/api/datasets/?format=datatables',
                'colsFields': [{'data': x} for x in cols],
                'colsNames': [
                    'Run Datetime','Name','Path','Comment','Nr Images',
                    'Nr Catalogs'
                ],
                'search': True,
            }
        }
    )


class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer


# Images table
def image_index(request):
    cols = ['time', 'name', 'ra', 'dec']
    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Images',
                'description': 'List of images below',
            },
            'datatable': {
                'api': '/api/images/?format=datatables',
                'colsFields': [{'data': x} for x in cols],
                'colsNames': ['Time','Name','RA','DEC'],
                'search': True,
            }
        }
    )


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer


# Sources table
def source_index(request):
    cols = ['name', 'ra', 'dec', 'flux_int', 'flux_peak']
    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Source',
                'description': 'List of sources below',
            },
            'datatable': {
                'api': '/api/sources/?format=datatables',
                'colsFields': [{'data': x} for x in cols],
                'colsNames': ['Name','RA','DEC', 'Flux', 'Peak Flux'],
                'search': True,
            }
        }
    )


class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
