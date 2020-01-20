from django.db.models import Count
from django.shortcuts import render
from rest_framework import viewsets

from .models import Dataset, Image, Source
from .serializers import DatasetSerializer, ImageSerializer, SourceSerializer


# Datasets table
def dataset_index(request):
    colsfields = []
    for col in ['time', 'name', 'path', 'comment', 'images', 'catalogs']:
        if col == 'name':
            colsfields.append({
                'data': col, 'render': {
                    'prefix': '/datasets/', 'col':'name'
                }
            })
        else:
            colsfields.append({'data': col})
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
                'colsFields': colsfields,
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


# Dataset detail
def dataset_detail(request, pk):
    dataset = Dataset.objects.filter(pk=pk).annotate(
        nr_imgs=Count('image', distinct=True),
        nr_cats=Count('catalog', distinct=True),
        nr_srcs=Count('image__source', distinct=True)
    ).values().get()
    return render(request, 'dataset_detail.html', {'dataset': dataset})


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
