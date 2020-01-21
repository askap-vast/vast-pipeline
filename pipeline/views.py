from django.db.models import Count, F
from django.shortcuts import render
from rest_framework import viewsets

from .models import Catalog, Dataset, Image, Source
from .serializers import (
    CatalogSerializer, DatasetSerializer, ImageSerializer, SourceSerializer
)
from .utils.utils import deg2dms, deg2hms


# Datasets table
def datasetIndex(request):
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
                'breadcrumb': {'title': 'Datasets', 'url': request.path},
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
def datasetDetail(request, pk):
    #TODO: improve the query (maybe multiple querysets?)
    dataset = Dataset.objects.filter(pk=pk).annotate(
        nr_imgs=Count('image', distinct=True),
        nr_cats=Count('catalog', distinct=True),
        nr_srcs=Count('image__source', distinct=True)
    ).values().get()
    return render(request, 'dataset_detail.html', {'dataset': dataset})


# Images table
def imageIndex(request):
    cols = ['time', 'name', 'ra', 'dec']
    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Images',
                'description': 'List of images below',
                'breadcrumb': {'title': 'Images', 'url': request.path},
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
def sourceIndex(request):
    cols = ['name', 'ra', 'dec', 'flux_int', 'flux_peak']
    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Source',
                'description': 'List of sources below',
                'breadcrumb': {'title': 'Sources', 'url': request.path},
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


# Catalogs table
def catalogIndex(request):
    colsfields = []
    for col in ['name', 'comment', 'ave_ra', 'ave_dec', 'sources', 'new']:
        if col == 'name':
            colsfields.append({
                'data': col, 'render': {
                    'prefix': '/catalogs/', 'col':'name'
                }
            })
        else:
            colsfields.append({'data': col})

    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Catalogs',
                'description': 'List of catalogs below',
                'breadcrumb': {'title': 'Catalogs', 'url': request.path},
            },
            'datatable': {
                'api': '/api/catalogs/?format=datatables',
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'Comment',
                    'Ave RA',
                    'Ave DEC',
                    'Datapoints',
                    'New Source',
                ],
                'search': False,
            }
        }
    )


class CatalogViewSet(viewsets.ModelViewSet):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer


# Catalog detail
def catalogDetail(request, pk):
    catalog = Catalog.objects.filter(pk=pk).annotate(
        sources=Count('source'),
        dsname=F('dataset__name')
    ).values().get()
    catalog['ave_ra'] = deg2hms(catalog['ave_ra'])
    catalog['ave_dec'] = deg2dms(catalog['ave_dec'])
    return render(request, 'catalog_detail.html', {'catalog': catalog})
