import io
import logging

from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from django.http import FileResponse
from django.db.models import Count, F, Q
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Image, Measurement, Run, Source, SkyRegion
from .serializers import (
    ImageSerializer, MeasurementSerializer, RunSerializer,
    SourceSerializer
)
from .utils.utils import deg2dms, deg2hms


logger = logging.getLogger(__name__)

# Defines the float format and scaling for all
# parameters presented in DATATABLES via AJAX call
FLOAT_FIELDS = {
    'ra': {
        'precision': 4,
        'scale': 1,
    },
    'ra_err': {
        'precision': 4,
        'scale': 3600.,
    },
    'uncertainty_ew': {
        'precision': 4,
        'scale': 3600.,
    },
    'dec': {
        'precision': 4,
        'scale': 1,
    },
    'dec_err': {
        'precision': 4,
        'scale': 3600,
    },
    'uncertainty_ns': {
        'precision': 4,
        'scale': 3600.,
    },
    'flux_int': {
        'precision': 3,
        'scale': 1,
    },
    'flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'v_int': {
        'precision': 2,
        'scale': 1,
    },
    'eta_int': {
        'precision': 2,
        'scale': 1,
    },
    'v_peak': {
        'precision': 2,
        'scale': 1,
    },
    'eta_peak': {
        'precision': 2,
        'scale': 1,
    },
    'avg_flux_int': {
        'precision': 3,
        'scale': 1,
    },
    'avg_flux_peak': {
        'precision': 3,
        'scale': 1,
    },
    'max_flux_peak': {
        'precision': 3,
        'scale': 1,
    },
}


def generate_colsfields(fields, url_prefix):
    colsfields = []

    for col in fields:
        if col == 'name':
            colsfields.append({
                'data': col, 'render': {
                    'url': {
                        'prefix': url_prefix,
                        'col': 'name'
                    }
                }
            })
        elif col in FLOAT_FIELDS:
            colsfields.append({
                'data': col,
                'render': {
                    'float': {
                        'col': col,
                        'precision': FLOAT_FIELDS[col]['precision'],
                        'scale': FLOAT_FIELDS[col]['scale'],
                    }
                }
            })
        else:
            colsfields.append({'data': col})

    return colsfields


def get_skyregions_collection():
    """
    Produce Sky region geometry shapes for d3-celestial.
    """
    skyregions = SkyRegion.objects.all()

    features = []

    for skr in skyregions:
        ra = skr.centre_ra - 180.
        dec = skr.centre_dec
        width_ra = skr.width_ra / 2.
        width_dec = skr.width_dec / 2.
        id = skr.id
        features.append(
            {
                "type": "Feature",
                "id": f"SkyRegion{id}",
                "properties": {
                    "n": f"{id:02d}",
                    "loc": [ra, dec]
                },
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [[
                        [ra+width_ra, dec+width_dec],
                        [ra+width_ra, dec-width_dec],
                        [ra-width_ra, dec-width_dec],
                        [ra-width_ra, dec+width_dec],
                        [ra+width_ra, dec+width_dec]
                    ]]
                }
            }
        )

    skyregions_collection = {
        "type": "FeatureCollection",
        "features" : features
    }

    return skyregions_collection

def Home(request):
    totals = {}
    totals['nr_pruns'] = Run.objects.count()
    totals['nr_imgs'] = Image.objects.count()
    totals['nr_srcs'] = Source.objects.count()
    totals['nr_meas'] = Measurement.objects.count()
    context = {
        'totals': totals,
        'd3_celestial_skyregions': get_skyregions_collection()
    }
    return render(request, 'index.html', context)


# Runs table
def RunIndex(request):
    fields = [
        'name',
        'time',
        'path',
        'comment',
        'n_images',
        'n_sources'
    ]

    colsfields = generate_colsfields(fields, "/piperuns/")

    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Pipeline Runs',
                'description': 'List of pipeline runs below',
                'breadcrumb': {'title': 'Pipeline Runs', 'url': request.path},
            },
            'datatable': {
                'api': '/api/piperuns/?format=datatables',
                'colsFields': colsfields,
                'colsNames': [
                    'Name','Run Datetime','Path','Comment','Nr Images',
                    'Nr Sources'
                ],
                'search': True,
            }
        }
    )


class RunViewSet(ModelViewSet):
    queryset = Run.objects.annotate(
        n_images=Count("image", distinct=True),
        n_sources=Count("source", distinct=True),
    )
    serializer_class = RunSerializer


# Run detail
def RunDetail(request, id):
    p_run = Run.objects.filter(id=id).values().get()
    p_run['nr_imgs'] = Image.objects.filter(run__id=p_run['id']).count()
    p_run['nr_srcs'] = Source.objects.filter(run__id=p_run['id']).count()
    p_run['nr_meas'] = Measurement.objects.filter(image__run__id=p_run['id']).count()
    p_run['nr_frcd'] = Measurement.objects.filter(
        image__run=p_run, forced=True).count()
    p_run['new_srcs'] = Source.objects.filter(
        run__id=p_run['id'],
        new=True,
    ).count()
    return render(request, 'run_detail.html', {'p_run': p_run})


# Images table
def ImageIndex(request):
    fields = ['name', 'datetime', 'ra', 'dec']

    colsfields = generate_colsfields(fields, '/images/')

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
                'colsFields': colsfields,
                'colsNames': ['Name','Time','RA','DEC'],
                'search': True,
            }
        }
    )


class ImageViewSet(ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer


def ImageDetail(request, id, action=None):
    # source data
    image = Image.objects.all().order_by('id')
    if action:
        if action == 'next':
            img = image.filter(id__gt=id)
            if img.exists():
                image = img.values().first()
            else:
                image = image.filter(id=id).values().get()
        elif action == 'prev':
            img = image.filter(id__lt=id)
            if img.exists():
                image = img.values().last()
            else:
                image = image.filter(id=id).values().get()
    else:
        image = image.filter(id=id).values().get()

    image['aladin_ra'] = image['ra']
    image['aladin_dec'] = image['dec']
    image['aladin_zoom'] = 15.0
    image['aladin_box_ra'] = image['physical_bmaj']
    image['aladin_box_dec'] = image['physical_bmin']
    image['ra'] = deg2hms(image['ra'], hms_format=True)
    image['dec'] = deg2dms(image['dec'], dms_format=True)

    image['datetime'] = image['datetime'].isoformat()

    context = {'image': image}
    return render(request, 'image_detail.html', context)


# Measurements table
def MeasurementIndex(request):
    fields = [
        'name',
        'ra',
        'ra_err',
        'uncertainty_ew',
        'dec',
        'dec_err',
        'uncertainty_ns',
        'flux_int',
        'flux_peak',
        'has_siblings',
        'forced'
    ]

    colsfields = generate_colsfields(fields, '/measurements/')

    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Image Data Measurements',
                'description': 'List of source measurements below',
                'breadcrumb': {'title': 'Measurements', 'url': request.path},
            },
            'datatable': {
                'api': '/api/measurements/?format=datatables',
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'RA (deg)',
                    'RA Error (arcsec)',
                    'Uncertainty EW (arcsec)',
                    'Dec (deg)',
                    'Dec Error (arcsec)',
                    'Uncertainty NS (arcsec)',
                    'Int. Flux (mJy)',
                    'Peak Flux (mJy/beam)',
                    'Has siblings',
                    'Forced Extraction'
                ],
                'search': True,
            }
        }
    )


class MeasurementViewSet(ModelViewSet):
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer

    def get_queryset(self):
        run_id = self.request.query_params.get('run_id', None)
        return self.queryset.filter(source__id=run_id) if run_id else self.queryset


def MeasurementDetail(request, id, action=None):
    # source data
    measurement = Measurement.objects.all().order_by('id')
    if action:
        if action == 'next':
            msr = measurement.filter(id__gt=id)
            if msr.exists():
                measurement = msr.annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                ).values().first()
            else:
                measurement = measurement.filter(id=id).annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                ).values().get()
        elif action == 'prev':
            msr = measurement.filter(id__lt=id)
            if msr.exists():
                measurement = msr.annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                ).values().last()
            else:
                measurement = measurement.filter(id=id).annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                ).values().get()
    else:
        measurement = measurement.filter(id=id).annotate(
            datetime=F('image__datetime'),
            image_name=F('image__name'),
        ).values().get()

    measurement['aladin_ra'] = measurement['ra']
    measurement['aladin_dec'] = measurement['dec']
    measurement['aladin_zoom'] = 0.36
    measurement['ra'] = deg2hms(measurement['ra'], hms_format=True)
    measurement['dec'] = deg2dms(measurement['dec'], dms_format=True)

    measurement['datetime'] = measurement['datetime'].isoformat()

    context = {'measurement': measurement}
    return render(request, 'measurement_detail.html', context)


# Sources table
def SourceIndex(request):
    fields = [
        'name',
        'comment',
        'wavg_ra',
        'wavg_dec',
        'avg_flux_int',
        'avg_flux_peak',
        'max_flux_peak',
        'measurements',
        'forced_measurements',
        'v_int',
        'eta_int',
        'v_peak',
        'eta_peak',
        'new'
    ]

    colsfields = generate_colsfields(fields, '/sources/')

    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Sources',
                'description': 'List of all sources below',
                'breadcrumb': {'title': 'Sources', 'url': request.path},
            },
            'datatable': {
                'api': '/api/sources/?format=datatables',
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'Comment',
                    'W. Avg. RA',
                    'W. Avg. Dec',
                    'Avg. Int. Flux (mJy)',
                    'Avg. Peak Flux (mJy/beam)',
                    'Max Peak Flux (mJy/beam)',
                    'Total Datapoints',
                    'Forced Datapoints',
                    'V int flux',
                    '\u03B7 int flux',
                    'V peak flux',
                    '\u03B7 peak flux',
                    'New Source',
                ],
                'search': False,
            }
        }
    )


class SourceViewSet(ModelViewSet):
    serializer_class = SourceSerializer

    def get_queryset(self):
        qs = Source.objects.annotate(
            measurements=Count('measurement'),
            forced_measurements=Count(
                'measurement', filter=Q(measurement__forced=True)
            )
        )

        qry_dict = {}
        p_run = self.request.query_params.get('run')
        if p_run:
            qry_dict['run__name'] = p_run

        flux_qry_flds = ['avg_flux_int', 'avg_flux_peak', 'v_int', 'v_peak']
        for fld in flux_qry_flds:
            for limit in ['max', 'min']:
                val = self.request.query_params.get(limit + '_' + fld)
                if val:
                    ky = fld + '__lte' if limit == 'max' else fld + '__gte'
                    qry_dict[ky] = val

        measurements = self.request.query_params.get('meas')
        if measurements:
            qry_dict['measurements'] = measurements

        if 'newsrc' in self.request.query_params:
            qry_dict['new'] = True

        if qry_dict:
            qs = qs.filter(**qry_dict)

        radius = self.request.query_params.get('radius')
        wavg_ra = self.request.query_params.get('ra')
        wavg_dec = self.request.query_params.get('dec')
        if wavg_ra and wavg_dec and radius:
            qs = qs.cone_search(wavg_ra, wavg_dec, radius)

        return qs


# Sources Query
def SourceQuery(request):
    fields = [
        'name',
        'comment',
        'wavg_ra',
        'wavg_dec',
        'avg_flux_int',
        'avg_flux_peak',
        'max_flux_peak',
        'measurements',
        'forced_measurements',
        'v_int',
        'eta_int',
        'v_peak',
        'eta_peak',
        'new'
    ]

    colsfields = generate_colsfields(fields, '/sources/')

    # get all pipeline run names
    p_runs =  list(Run.objects.values('name').all())

    return render(
        request,
        'sources_query.html',
        {
            'breadcrumb': {'title': 'Sources', 'url': request.path},
            # 'text': {
            #     'title': 'Sources',
            #     'description': 'List of all sources below',
            # },
            'runs': p_runs,
            'datatable': {
                'api': '/api/sources/?format=datatables',
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'Comment',
                    'W. Avg. RA',
                    'W. Avg. Dec',
                    'Avg. Int. Flux (mJy)',
                    'Avg. Peak Flux (mJy/beam)',
                    'Max Peak Flux (mJy/beam)',
                    'Total Datapoints',
                    'Forced Datapoints',
                    'V int flux',
                    '\u03B7 int flux',
                    'V peak flux',
                    '\u03B7 peak flux',
                    'New Source',
                ],
                'search': False,
            }
        }
    )


# Source detail
def SourceDetail(request, id, action=None):
    # source data
    source = Source.objects.all()
    if action:
        if action == 'next':
            src = source.filter(id__gt=id)
            if src.exists():
                source = src.annotate(
                    run_name=F('run__name')
                ).values().first()
            else:
                source = source.filter(id=id).annotate(
                    run_name=F('run__name')
                ).values().get()
        elif action == 'prev':
            src = source.filter(id__lt=id)
            if src.exists():
                source = src.annotate(
                    run_name=F('run__name')
                ).values().last()
            else:
                source = source.filter(id=id).annotate(
                    run_name=F('run__name')
                ).values().get()
    else:
        source = source.filter(id=id).annotate(
            run_name=F('run__name')
        ).values().get()
    source['aladin_ra'] = source['wavg_ra']
    source['aladin_dec'] = source['wavg_dec']
    source['aladin_zoom'] = 0.36
    source['wavg_ra'] = deg2hms(source['wavg_ra'], hms_format=True)
    source['wavg_dec'] = deg2dms(source['wavg_dec'], dms_format=True)
    source['datatable'] = {'colsNames': [
        'ID',
        'Name',
        'Date',
        'Image',
        'RA',
        'RA Error',
        'Dec',
        'Dec Error',
        'Int. Flux (mJy)',
        'Int. Flux Error (mJy)',
        'Peak Flux (mJy/beam)',
        'Peak Flux Error (mJy/beam)',
        'Has siblings',
        'Forced Extraction',
        'Image ID'
    ]}

    # source data
    cols = [
        'id',
        'name',
        'ra',
        'ra_err',
        'dec',
        'dec_err',
        'flux_int',
        'flux_int_err',
        'flux_peak',
        'flux_peak_err',
        'has_siblings',
        'forced',
        'datetime',
        'image_name',
        'image_id'
    ]
    measurements = list(
        Measurement.objects.filter(source__id=id).annotate(
            datetime=F('image__datetime'),
            image_name=F('image__name'),
        ).order_by('datetime').values(*tuple(cols))
    )
    for one_m in measurements:
        one_m['datetime'] = one_m['datetime'].isoformat()

    # add source count
    source['measurements'] = len(measurements)
    # add the data for the datatable api
    measurements = {
        'table': 'source_detail',
        'dataQuery': measurements,
        'colsFields': [
            'id',
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
            'has_siblings',
            'forced',
            'image_id'
        ],
        'search': True,
        'order': [2, 'asc']
    }

    context = {'source': source, 'measurements': measurements}
    return render(request, 'source_detail.html', context)


class ImageCutout(APIView):
    def get(self, request, measurement_name):
        measurement = Measurement.objects.get(name=measurement_name)
        image_hdu: fits.PrimaryHDU = fits.open(measurement.image.path)[0]
        coord = SkyCoord(ra=measurement.ra, dec=measurement.dec, unit="deg")
        cutout = Cutout2D(image_hdu.data, coord, Angle("3arcmin"), wcs=WCS(image_hdu.header))

        cutout_hdu = fits.PrimaryHDU(data=cutout.data, header=cutout.wcs.to_header())
        cutout_file = io.BytesIO()
        cutout_hdu.writeto(cutout_file)
        cutout_file.seek(0)
        response = FileResponse(
            cutout_file,
            as_attachment=True,
            filename=f"{measurement.name}_cutout.fits"
        )
        return response
