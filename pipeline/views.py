import logging

from django.db.models import Count, F
from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from .models import Catalog, Dataset, Image, Source
from .serializers import (
    CatalogSerializer, DatasetSerializer, ImageSerializer, SourceSerializer
)
from .utils.utils import deg2dms, deg2hms


logger = logging.getLogger(__name__)


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


class DatasetViewSet(ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer


# Dataset detail
def datasetDetail(request, pk):
    dataset = Dataset.objects.filter(pk=pk).values().get()
    dataset['nr_imgs'] = Image.objects.filter(dataset__id=dataset['id']).count()
    dataset['nr_cats'] = Catalog.objects.filter(dataset__id=dataset['id']).count()
    dataset['nr_srcs'] = Source.objects.filter(image__dataset__id=dataset['id']).count()
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


class ImageViewSet(ModelViewSet):
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


class SourceViewSet(ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer

    def get_queryset(self):
        ds_id = self.request.query_params.get('dataset_id', None)
        return self.queryset.filter(catalog__id=ds_id) if ds_id else self.queryset


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
                    'Average RA',
                    'Average DEC',
                    'Datapoints',
                    'New Source',
                ],
                'search': False,
            }
        }
    )


class CatalogViewSet(ModelViewSet):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer


# Catalog detail
def catalogDetail(request, pk):
    # catalog data
    catalog = Catalog.objects.filter(pk=pk).annotate(
        dsname=F('dataset__name')
    ).values().get()
    catalog['aladin_ra'] = catalog['ave_ra']
    catalog['aladin_dec'] = catalog['ave_dec']
    catalog['ave_ra'] = deg2hms(catalog['ave_ra'], hms_format=True)
    catalog['ave_dec'] = deg2dms(catalog['ave_dec'], dms_format=True)
    catalog['datatable'] = {'colsNames': [
        'Name',
        'Date',
        'Image',
        'RA',
        'RA Error',
        'DEC',
        'DEC Error',
        'Flux (mJy)',
        'Error Flux (mJy)',
        'Peak Flux (mJy)',
        'Error Peak Flux (mJy)',
    ]}

    # source data
    cols = [
        'name',
        'ra',
        'ra_err',
        'dec',
        'dec_err',
        'flux_int',
        'flux_int_err',
        'flux_peak',
        'flux_peak_err',
        'datetime',
        'image_name',
    ]
    sources = list(Source.objects.filter(catalog__pk=pk).annotate(
        datetime=F('image__time'),
        image_name=F('image__name'),
    ).order_by('datetime').values(*tuple(cols)))
    for src in sources:
        src['datetime'] = src['datetime'].strftime('%Y %b %d %H:%M:%S')
        for key in ['flux_int', 'flux_int_err', 'flux_peak', 'flux_peak_err']:
            src[key] = src[key] * 1.e3

    # add source count
    catalog['sources'] = len(sources)
    # add the data for the datatable api
    sources = {
        'dataQuery': sources,
        'colsFields': [
            'name',
            'datetime',
            'image_name',
            'ra',
            'ra_err',
            'dec',
            'dec_err',
            'flux_int',
            'flux_int_err',
            'flux_peak',
            'flux_peak_err',
        ],
        'search': True,
    }
    context = {'catalog': catalog, 'sources': sources}
    return render(request, 'catalog_detail.html', context)
