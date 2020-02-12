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
def datasetDetail(request, id):
    dataset = Dataset.objects.filter(id=id).values().get()
    dataset['nr_imgs'] = Image.objects.filter(dataset__id=dataset['id']).count()
    dataset['nr_cats'] = Catalog.objects.filter(dataset__id=dataset['id']).count()
    dataset['nr_srcs'] = Source.objects.filter(image__dataset__id=dataset['id']).count()
    dataset['new_srcs'] = Catalog.objects.filter(
        dataset__id=dataset['id'],
        new=True,
    ).count()
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
    fields = [
        'name',
        'comment',
        'ave_ra',
        'ave_dec',
        'ave_flux_int',
        'ave_flux_peak',
        'max_flux_peak',
        'sources',
        'v_int',
        'v_peak',
        'eta_int',
        'eta_peak',
        'new'
    ]
    colsfields = []
    for col in fields:
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
                'description': 'List of all catalogs below',
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
                    'Average Int Flux',
                    'Average Peak Flux',
                    'Max Peak Flux',
                    'Datapoints',
                    'V int flux',
                    'V peak flux',
                    'Eta int flux',
                    'Eta peak flux',
                    'New Source',
                ],
                'search': False,
            }
        }
    )


class CatalogViewSet(ModelViewSet):
    queryset = Catalog.objects.all()
    serializer_class = CatalogSerializer


# Catalogs Query
def catalogQuery(request):
    fields = [
        'name',
        'comment',
        'ave_ra',
        'ave_dec',
        'ave_flux_int',
        'ave_flux_peak',
        'max_flux_peak',
        'sources',
        'v_int',
        'v_peak',
        'eta_int',
        'eta_peak',
        'new'
    ]
    colsfields = []
    for col in fields:
        if col == 'name':
            colsfields.append({
                'data': col, 'render': {
                    'prefix': '/catalogs/', 'col':'name'
                }
            })
        else:
            colsfields.append({'data': col})

    # get all datasets names
    ds =  list(Dataset.objects.values('name').all())

    return render(
        request,
        'catalogs_query.html',
        {
            'breadcrumb': {'title': 'Catalogs', 'url': request.path},
            # 'text': {
            #     'title': 'Catalogs',
            #     'description': 'List of all catalogs below',
            # },
            'datasets': ds,
            'datatable': {
                'api': '/api/catalogs/?format=datatables',
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'Comment',
                    'Average RA',
                    'Average DEC',
                    'Average Int Flux',
                    'Average Peak Flux',
                    'Max Peak Flux',
                    'Datapoints',
                    'V int flux',
                    'V peak flux',
                    'Eta int flux',
                    'Eta peak flux',
                    'New Source',
                ],
                'search': False,
            }
        }
    )


# Catalog detail
def catalogDetail(request, id, action=None):
    # catalog data
    catalog = Catalog.objects.all()
    if action:
        if action == 'next':
            cat = catalog.filter(id__gt=id)
            if cat.exists():
                catalog = cat.annotate(
                    dsname=F('dataset__name')
                ).values().first()
            else:
                catalog = catalog.filter(id=id).annotate(
                    dsname=F('dataset__name')
                ).values().get()
        elif action == 'prev':
            cat = catalog.filter(id__lt=id)
            if cat.exists():
                catalog = cat.annotate(
                    dsname=F('dataset__name')
                ).values().last()
            else:
                catalog = catalog.filter(id=id).annotate(
                    dsname=F('dataset__name')
                ).values().get()
    else:
        catalog = catalog.filter(id=id).annotate(
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
    sources = list(Source.objects.filter(catalog__id=id).annotate(
        datetime=F('image__time'),
        image_name=F('image__name'),
    ).order_by('datetime').values(*tuple(cols)))
    for src in sources:
        src['datetime'] = src['datetime'].strftime('%Y %b %d %H:%M:%S')
        # for key in ['flux_int', 'flux_int_err', 'flux_peak', 'flux_peak_err']:
        #     src[key] = src[key] * 1.e3

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
