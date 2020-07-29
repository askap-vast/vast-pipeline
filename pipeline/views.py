import io
import os
import json
import logging
import dask.dataframe as dd
from dask import compute
from typing import Dict, Any

from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

from django.http import FileResponse, Http404
from django.db.models import Count, F, Q, Case, When, Value, BooleanField
from django.shortcuts import render
from django.urls import reverse
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.authentication import (
    SessionAuthentication, BasicAuthentication
)
from rest_framework.permissions import IsAuthenticated
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.auth.decorators import login_required


from .models import Image, Measurement, Run, Source
from .serializers import (
    ImageSerializer, MeasurementSerializer, RunSerializer,
    SourceSerializer
)
from .utils.utils import (
    deg2dms, deg2hms, gal2equ, ned_search, simbad_search
)
from .utils.view import generate_colsfields, get_skyregions_collection


logger = logging.getLogger(__name__)


def Login(request):
    context = {
        'particlejs_conf_f': os.path.join(
            settings.STATIC_URL, 'js', 'particlesjs-config.json'
        )
    }
    return render(request, 'login.html', context)


@login_required
def Home(request):
    totals = {}
    totals['nr_pruns'] = Run.objects.count()
    totals['nr_imgs'] = Image.objects.count()
    totals['nr_srcs'] = Source.objects.count()
    totals['nr_meas'] = (
        dd.read_parquet(
            os.path.join(
                settings.PIPELINE_WORKING_DIR,
                'images/**/measurements.parquet',
            ),
            columns='id'
        )
        .count()
        .compute()
    )
    context = {
        'totals': totals,
        'd3_celestial_skyregions': get_skyregions_collection()
    }
    return render(request, 'index.html', context)


# Runs table
@login_required
def RunIndex(request):
    fields = [
        'name',
        'time',
        'path',
        'comment',
        'n_images',
        'n_sources',
        'status'
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
                    'Name', 'Run Datetime', 'Path', 'Comment', 'Nr Images',
                    'Nr Sources', 'Run Status'
                ],
                'search': True,
            }
        }
    )


class RunViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Run.objects.annotate(
        n_images=Count("image", distinct=True),
        n_sources=Count("source", distinct=True),
    )
    serializer_class = RunSerializer


# Run detail
@login_required
def RunDetail(request, id):
    p_run_model = Run.objects.filter(id=id).prefetch_related('image_set').get()
    p_run = p_run_model.__dict__
    p_run['status'] = p_run_model.get_status_display()
    images = list(p_run_model.image_set.values('name', 'datetime'))
    img_paths = list(map(
        lambda x: os.path.join(
            settings.PIPELINE_WORKING_DIR,
            'images',
            '_'.join([
                x['name'].replace('.','_'),
                x['datetime'].strftime('%Y-%m-%dT%H_%M_%S%z')
            ]),
            'measurements.parquet'
        ),
        p_run_model.image_set.values('name', 'datetime')
    ))
    p_run['nr_imgs'] = len(img_paths)
    p_run['nr_srcs'] = Source.objects.filter(run__id=p_run['id']).count()
    p_run['nr_meas'] = (
        dd.read_parquet(
            img_paths,
            columns='id'
        )
        .count()
        .compute()
    )
    p_run['nr_frcd'] = (
        dd.read_parquet(
            os.path.join(p_run['path'], 'forced_measurements_*.parquet'),
            columns='id'
        )
        .count()
        .compute()
    )
    p_run['new_srcs'] = Source.objects.filter(
        run__id=p_run['id'],
        new=True,
    ).count()
    return render(request, 'run_detail.html', {'p_run': p_run})


# Images table
@login_required
def ImageIndex(request):
    fields = [
        'name',
        'datetime',
        'ra',
        'dec',
        'rms_median',
        'rms_min',
        'rms_max'
    ]

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
                'colsNames': [
                    'Name',
                    'Time (UTC)',
                    'RA (deg)',
                    'Dec (deg)',
                    'Median RMS (mJy)',
                    'Min RMS (mJy)',
                    'Max RMS (mJy)',
                ],
                'search': True,
                'order': [1, 'asc']
            }
        }
    )


class ImageViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Image.objects.all()
    serializer_class = ImageSerializer


@login_required
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
@login_required
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
        'flux_int_err',
        'flux_peak',
        'flux_peak_err',
        'compactness',
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
                    'Int. Flux Error (mJy)',
                    'Peak Flux (mJy/beam)',
                    'Peak Flux Error (mJy/beam)',
                    'Compactness',
                    'Has siblings',
                    'Forced Extraction'
                ],
                'search': True,
            }
        }
    )


class MeasurementViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer

    def get_queryset(self):
        run_id = self.request.query_params.get('run_id', None)
        return self.queryset.filter(source__id=run_id) if run_id else self.queryset


@login_required
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
                    source_ids=ArrayAgg('source__id'),
                    source_names=ArrayAgg('source__name'),
                ).values().first()
            else:
                measurement = measurement.filter(id=id).annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                    source_ids=ArrayAgg('source__id'),
                    source_names=ArrayAgg('source__name'),
                ).values().get()
        elif action == 'prev':
            msr = measurement.filter(id__lt=id)
            if msr.exists():
                measurement = msr.annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                    source_ids=ArrayAgg('source__id'),
                    source_names=ArrayAgg('source__name'),
                ).values().last()
            else:
                measurement = measurement.filter(id=id).annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                    source_ids=ArrayAgg('source__id'),
                    source_names=ArrayAgg('source__name'),
                ).values().get()
    else:
        measurement = measurement.filter(id=id).annotate(
            datetime=F('image__datetime'),
            image_name=F('image__name'),
            source_ids=ArrayAgg('source__id'),
            source_names=ArrayAgg('source__name'),
        ).values().get()

    measurement['aladin_ra'] = measurement['ra']
    measurement['aladin_dec'] = measurement['dec']
    measurement['aladin_zoom'] = 0.36
    measurement['ra'] = deg2hms(measurement['ra'], hms_format=True)
    measurement['dec'] = deg2dms(measurement['dec'], dms_format=True)

    measurement['datetime'] = measurement['datetime'].isoformat()

    if not measurement['source_ids'] == [None]:
        # this enables easy presenting in the template
        measurement['sources_info'] = list(zip(
            measurement['source_ids'],
            measurement['source_names']
        ))

    context = {'measurement': measurement}
    return render(request, 'measurement_detail.html', context)


# Sources table
@login_required
def SourceIndex(request):
    fields = [
        'name',
        'comment',
        'wavg_ra',
        'wavg_dec',
        'avg_flux_int',
        'avg_flux_peak',
        'max_flux_peak',
        'avg_compactness',
        'measurements',
        'selavy_measurements',
        'forced_measurements',
        'n_neighbour_dist',
        'relations',
        'v_int',
        'eta_int',
        'v_peak',
        'eta_peak',
        'contains_siblings',
        'new',
        'new_high_sigma'
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
                    'Avg. Compactness',
                    'Total Datapoints',
                    'Selavy Datapoints',
                    'Forced Datapoints',
                    'Nearest Neighbour Dist. (arcmin)',
                    'Relations',
                    'V int flux',
                    '\u03B7 int flux',
                    'V peak flux',
                    '\u03B7 peak flux',
                    'Contains siblings',
                    'New Source',
                    'New High Sigma'
                ],
                'search': False,
            }
        }
    )


class SourceViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SourceSerializer

    def get_queryset(self):
        qs = Source.objects.annotate(
            measurements=Count('measurement', distinct=True),
            selavy_measurements=Count(
                'measurement',
                filter=Q(measurement__forced=False),
                distinct=True
            ),
            forced_measurements=Count(
                'measurement',
                filter=Q(measurement__forced=True),
                distinct=True
            ),
            relations=Count('related', distinct=True),
            siblings_count=Count(
                'measurement',
                filter=Q(measurement__has_siblings=True),
                distinct=True
            ),
            contains_siblings=Case(
                When(siblings_count__gt=0, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )

        radius_conversions = {
            "arcsec": 3600.,
            "arcmin": 60.,
            "deg": 1.
        }

        qry_dict = {}
        p_run = self.request.query_params.get('run')
        if p_run:
            qry_dict['run__name'] = p_run

        flux_qry_flds = [
            'avg_flux_int',
            'avg_flux_peak',
            'v_int',
            'v_peak',
            'eta_int',
            'eta_peak',
            'measurements',
            'selavy_measurements',
            'forced_measurements',
            'relations',
            'contains_siblings',
            'new_high_sigma',
            'avg_compactness',
            'n_neighbour_dist'
        ]

        neighbour_unit = self.request.query_params.get('NeighbourUnit')

        for fld in flux_qry_flds:
            for limit in ['max', 'min']:
                val = self.request.query_params.get(limit + '_' + fld)
                if val:
                    ky = fld + '__lte' if limit == 'max' else fld + '__gte'
                    if fld == 'n_neighbour_dist':
                        val = float(val) / radius_conversions[neighbour_unit]
                    qry_dict[ky] = val

        measurements = self.request.query_params.get('meas')
        if measurements:
            qry_dict['measurements'] = measurements

        if 'newsrc' in self.request.query_params:
            qry_dict['new'] = True

        if 'no_siblings' in self.request.query_params:
            qry_dict['contains_siblings'] = False

        if qry_dict:
            qs = qs.filter(**qry_dict)

        radius = self.request.query_params.get('radius')
        radiusUnit = self.request.query_params.get('radiusunit')
        objectname = self.request.query_params.get('objectname')
        objectservice = self.request.query_params.get('objectservice')
        coordsys = self.request.query_params.get('coordsys')
        if objectname is not None:
            if objectservice == 'simbad':
                wavg_ra, wavg_dec = simbad_search(objectname)
            elif objectservice == 'ned':
                wavg_ra, wavg_dec = ned_search(objectname)
        else:
            wavg_ra = self.request.query_params.get('ra')
            wavg_dec = self.request.query_params.get('dec')
            # galactic coordinates won't be entered if the user
            # has entered an object query
            if coordsys == 'galactic':
                wavg_ra, wavg_dec = gal2equ(wavg_ra, wavg_dec)

        if wavg_ra and wavg_dec and radius:
            radius = float(radius) / radius_conversions[radiusUnit]
            qs = qs.cone_search(wavg_ra, wavg_dec, radius)

        return qs


# Sources Query
@login_required
def SourceQuery(request):
    fields = [
        'name',
        'comment',
        'wavg_ra',
        'wavg_dec',
        'avg_flux_int',
        'avg_flux_peak',
        'max_flux_peak',
        'avg_compactness',
        'measurements',
        'selavy_measurements',
        'forced_measurements',
        'n_neighbour_dist',
        'relations',
        'v_int',
        'eta_int',
        'v_peak',
        'eta_peak',
        'contains_siblings',
        'new',
        'new_high_sigma'
    ]

    colsfields = generate_colsfields(fields, '/sources/')

    # get all pipeline run names
    p_runs = list(Run.objects.values('name').all())

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
                    'Avg. Compactness',
                    'Total Datapoints',
                    'Selavy Datapoints',
                    'Forced Datapoints',
                    'Nearest Neighbour Dist. (arcmin)',
                    'Relations',
                    'V int flux',
                    '\u03B7 int flux',
                    'V peak flux',
                    '\u03B7 peak flux',
                    'Contains siblings',
                    'New Source',
                    'New High Sigma'
                ],
                'search': False,
            }
        }
    )


# Source detail
@login_required
def SourceDetail(request, id, action=None):
    # source data
    source = Source.objects.all()
    if action:
        if action == 'next':
            src = source.filter(id__gt=id)
            if src.exists():
                source = src.annotate(
                    run_name=F('run__name'),
                    relations_ids=ArrayAgg('related__id'),
                    relations_names=ArrayAgg('related__name')
                ).values().first()
            else:
                source = source.filter(id=id).annotate(
                    run_name=F('run__name'),
                    relations_ids=ArrayAgg('related__id'),
                    relations_names=ArrayAgg('related__name')
                ).values().get()
        elif action == 'prev':
            src = source.filter(id__lt=id)
            if src.exists():
                source = src.annotate(
                    run_name=F('run__name'),
                    relations_ids=ArrayAgg('related__id'),
                    relations_names=ArrayAgg('related__name')
                ).values().last()
            else:
                source = source.filter(id=id).annotate(
                    run_name=F('run__name'),
                    relations_ids=ArrayAgg('related__id'),
                    relations_names=ArrayAgg('related__name')
                ).values().get()
    else:
        source = source.filter(id=id).annotate(
            run_name=F('run__name'),
            relations_ids=ArrayAgg('related__id'),
            relations_names=ArrayAgg('related__name')
        ).values().get()
    source['aladin_ra'] = source['wavg_ra']
    source['aladin_dec'] = source['wavg_dec']
    source['aladin_zoom'] = 0.36
    if not source['relations_ids'] == [None]:
        # this enables easy presenting in the template
        source['relations_info'] = list(zip(
            source['relations_ids'],
            source['relations_names']
        ))
    source['wavg_ra'] = deg2hms(source['wavg_ra'], hms_format=True)
    source['wavg_dec'] = deg2dms(source['wavg_dec'], dms_format=True)
    source['datatable'] = {'colsNames': [
        'ID',
        'Name',
        'Date (UTC)',
        'Image',
        'RA (deg)',
        'RA Error (arcsec)',
        'Dec (deg)',
        'Dec Error (arcsec)',
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
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, measurement_name, size="normal"):
        measurement = Measurement.objects.get(name=measurement_name)
        image_hdu: fits.PrimaryHDU = fits.open(measurement.image.path)[0]
        coord = SkyCoord(ra=measurement.ra, dec=measurement.dec, unit="deg")
        sizes = {
            "xlarge": "40arcmin",
            "large": "20arcmin",
            "normal": "2arcmin",
        }

        filenames = {
            "xlarge": f"{measurement.name}_cutout_xlarge.fits",
            "large": f"{measurement.name}_cutout_large.fits",
            "normal": f"{measurement.name}_cutout.fits",
        }

        try:
            data = image_hdu.data[0, 0, :, :]
        except Exception as e:
            data = image_hdu.data

        cutout = Cutout2D(
            data, coord, Angle(sizes[size]), wcs=WCS(image_hdu.header, naxis=2),
            mode='partial'
        )

        # add beam properties to the cutout header and fix cdelts as JS9 does not deal
        # with PCi_j properly
        cdelt1, cdelt2 = proj_plane_pixel_scales(cutout.wcs)
        cutout_header = cutout.wcs.to_header()
        cutout_header.remove("PC1_1", ignore_missing=True)
        cutout_header.remove("PC2_2", ignore_missing=True)
        cutout_header.update(
            CDELT1=-cdelt1,
            CDELT2=cdelt2,
            BMAJ=image_hdu.header["BMAJ"],
            BMIN=image_hdu.header["BMIN"],
            BPA=image_hdu.header["BPA"]
        )

        cutout_hdu = fits.PrimaryHDU(data=cutout.data, header=cutout_header)
        cutout_file = io.BytesIO()
        cutout_hdu.writeto(cutout_file)
        cutout_file.seek(0)
        response = FileResponse(
            cutout_file,
            as_attachment=True,
            filename=filenames[size]
        )
        return response


class MeasurementQuery(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(
        self,
        request,
        ra_deg: float,
        dec_deg: float,
        image_id: int,
        radius_deg: float,
    ) -> FileResponse:
        """Return a DS9/JS9 region file for all Measurement objects for a given cone search
        on an Image. Optionally highlight sources based on a Measurement or Source ID.

        Args:
            request: Django HTTPRequest. Supports two URL GET parameters:
                selection_model: either "measurement" or "source" (defaults to "measurement"); and
                selection_id: the id for the given `selection_model`.
                Measurement objects that match the given selection criterion will be
                highlighted. e.g. ?selection_model=measurement&selection_id=100 will highlight
                the Measurement object with id=100. ?selection_model=source&selection_id=5
                will highlight all Measurement objects associated with the Source object with
                id=5.
            ra_deg: Cone search RA in decimal degrees.
            dec_deg: Cone search Dec in decimal degrees.
            image_id: Primary key (id) of the Image object to search.
            radius_deg: Cone search radius in decimal degrees.

        Returns:
            FileResponse: Django FileReponse containing a DS9/JS9 region file.
        """
        columns = ["id", "name", "ra", "dec", "bmaj", "bmin", "pa", "forced", "source", "source__name"]
        selection_model = request.GET.get("selection_model", "measurement")
        selection_id = request.GET.get("selection_id", None)

        # validate selection query params
        if selection_id is not None:
            if selection_model not in ("measurement", "source"):
                raise Http404("GET param selection_model must be either 'measurement' or 'source'.")
            if selection_model == "measurement":
                selection_attr = "id"
                selection_name = "name"
            else:
                selection_attr = selection_model
                selection_name = "source__name"
            try:
                selection_id = int(selection_id)
            except ValueError:
                raise Http404("GET param selection_id must be an integer.")

        measurements = (
            Measurement.objects.filter(image=image_id)
            .cone_search(ra_deg, dec_deg, radius_deg)
            .values(*columns, __name=F(selection_name))
        )
        measurement_region_file = io.StringIO()
        for meas in measurements:
            if selection_id is not None:
                color = "#FF0000" if meas[selection_attr] == selection_id else "#0000FF"
            shape = (
                f"ellipse({meas['ra']}d, {meas['dec']}d, {meas['bmaj']}\", {meas['bmin']}\", "
                f"{meas['pa']+90+180}d)"
            )
            properties: Dict[str, Any] = {
                "color": color,
                "data": {
                    "text": f"{selection_model} ID: {meas[selection_attr]}",
                    "link": reverse(f"pipeline:{selection_model}_detail", args=[selection_id]),
                }
            }
            if meas["forced"]:
                properties.update(strokeDashArray=[3, 2])
            region = f"{shape} {json.dumps(properties)}\n"
            measurement_region_file.write(region)
        measurement_region_file.seek(0)
        f = io.BytesIO(bytes(measurement_region_file.read(), encoding="utf8"))
        response = FileResponse(
            f,
            as_attachment=False,
            filename=f"image-{image_id}_{ra_deg:.5f}_{dec_deg:+.5f}_radius-{radius_deg:.3f}.reg",
        )
        return response
