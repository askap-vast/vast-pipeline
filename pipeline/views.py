import io
import os
import json
import logging
import traceback
import dask.dataframe as dd
import dask.bag as db
import pandas as pd

from typing import Dict, Any
from glob import glob
from itertools import tee

from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

from django.http import FileResponse, Http404
from django.db.models import Count, F, Q, Case, When, Value, BooleanField
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.authentication import (
    SessionAuthentication, BasicAuthentication
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.auth.decorators import login_required


from .models import Image, Measurement, Run, Source
from .serializers import (
    ImageSerializer, MeasurementSerializer, RunSerializer,
    SourceSerializer, RawImageSelavyListSerializer
)
from .utils.utils import (
    deg2dms, deg2hms, gal2equ, ned_search, simbad_search
)
from .utils.view import generate_colsfields, get_skyregions_collection
from .management.commands.initpiperun import initialise_run
from .forms import PipelineRunForm
from .pipeline.main import Pipeline


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
    meas_glob = glob(os.path.join(
        settings.PIPELINE_WORKING_DIR,
        'images/**/measurements.parquet',
    ))
    check_run_db = Run.objects.exists()
    totals['nr_meas'] = (
        dd.read_parquet(meas_glob, columns='id')
        .count()
        .compute()
    ) if (check_run_db and meas_glob) else 0
    context = {
        'totals': totals,
        'd3_celestial_skyregions': get_skyregions_collection()
    }
    return render(request, 'index.html', context)


# Runs table
@login_required
def RunIndex(request):
    if request.method == 'POST':
        # this POST section is for initialise a pipeline run
        form = PipelineRunForm(request.POST)
        if form.is_valid():
            # TODO: re-write files lists into the form, couldn't get it to work
            cfg_data = form.cleaned_data

            # get the user data
            run_dict = {
                key: val for key, val in cfg_data.items() if 'run' in key
            }

            # remove user data from run config data
            for key in run_dict.keys():
                cfg_data.pop(key)

            run_dict['user'] = request.user

            f_list = [
                'image_files', 'selavy_files', 'background_files',
                'noise_files'
            ]
            for files in f_list:
                cfg_data[files] = request.POST.getlist(files)

            try:
                p_run = initialise_run(
                    **run_dict,
                    config=cfg_data
                )
                messages.success(
                    request,
                    f'Pipeline run {p_run.name} initilialised successfully!'
                )
                return redirect('pipeline:run_detail', id=p_run.id)
            except Exception as e:
                messages.error(
                    request,
                    f'Issue in pipeline run initilisation: {e}'
                )
                return redirect('pipeline:run_index')
        else:
            messages.error(
                request,
                f'Form not valid: {form.errors}'
            )
            return redirect('pipeline:run_index')

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
            },
            'runconfig' : settings.PIPE_RUN_CONFIG_DEFAULTS
        }
    )


class RunViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Run.objects.all()
    serializer_class = RunSerializer


# Run detail
@login_required
def RunDetail(request, id):
    p_run_model = Run.objects.filter(id=id).prefetch_related('image_set').get()
    p_run = p_run_model.__dict__
    # build config path for POST and later
    f_path = os.path.join(p_run['path'], 'config.py')
    if request.method == 'POST':
        # this post is for writing the config text (modified or not) from the
        #  UI to a config.py file
        config_text = request.POST.get('config_text', None)
        if config_text:
            try:
                with open(f_path, 'w') as fp:
                    fp.write(config_text)

                messages.success(
                    request,
                    'Pipeline config written successfully'
                )
            except Exception as e:
                messages.error(request, f'Error in writing config: {e}')
        else:
            messages.info(request, 'Config text null')

    p_run['user'] = p_run_model.user.username if p_run_model.user else None
    p_run['status'] = p_run_model.get_status_display()
    if p_run_model.image_set.exists():
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
        p_run['nr_meas'] = (
            dd.read_parquet(img_paths, columns='id')
            .count()
            .compute()
        )
    else:
        p_run['nr_meas'] = 'N.A.'

    forced_path = glob(
        os.path.join(p_run['path'], 'forced_measurements_*.parquet')
    )
    if forced_path:
        try:
            p_run['nr_frcd'] = (
                dd.read_parquet(forced_path, columns='id')
                .count()
                .compute()
            )
        except Exception as e:
            messages.error(
                request,
                (
                    'Issues in reading forced measurements parquet:\n'
                    f'{e.args[0][:500]}'
                )
            )
            pass
    else:
        p_run['nr_frcd'] = 'N.A.'

    p_run['new_srcs'] = Source.objects.filter(
        run__id=p_run['id'],
        new=True,
    ).count()

    # read run config
    if os.path.exists(f_path):
        with open(f_path) as fp:
            p_run['config_txt'] = fp.read()

    # read run log file
    f_path = os.path.join(p_run['path'], 'log.txt')
    if os.path.exists(f_path):
        with open(f_path) as fp:
            p_run['log_txt'] = fp.read()

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
        'snr',
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
                    'SNR',
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


class SourceViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SourceSerializer

    def get_queryset(self):
        qs = Source.objects.all()

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
            'n_meas',
            'n_meas_sel',
            'n_meas_forced',
            'n_rel',
            'new_high_sigma',
            'avg_compactness',
            'min_snr',
            'max_snr',
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
            qry_dict['n_sibl'] = 0

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
        'min_snr',
        'max_snr',
        'avg_compactness',
        'n_meas',
        'n_meas_sel',
        'n_meas_forced',
        'n_neighbour_dist',
        'n_rel',
        'v_int',
        'eta_int',
        'v_peak',
        'eta_peak',
        'n_sibl',
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
                    'Min SNR',
                    'Max SNR',
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


class RawImageListSet(ViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    @staticmethod
    def gen_title_data_tokens(list_of_paths):
        '''
        generate a dataframe with extra columns for HTML tags title
        and data-tokens to generate something like:
        <option title={{title}} data-tokens={{datatokens}}>{{path}}</option>
        this assume a path like this:
        EPOCH06x/COMBINED/STOKESI_SELAVY/VAST_2118-06A.EPOCH06x.I.selavy.components.txt
        For the following dataframe columns
                                                     path
        EPOCH06x/COMBINED/STOKESI_SELAVY/VAST_2118-06A...
                                                 title
        VAST_2118-06A.EPOCH06x.I.selavy.components.txt
                                               datatokens
        EPOCH06x VAST_2118-06A.EPOCH06x.I.selavy.compo...
        '''
        df = pd.DataFrame(list_of_paths, columns=['path'])
        df = df.sort_values('path')
        df['title'] = df['path'].str.split(pat=os.sep).str.get(-1)
        df['datatokens'] = (
            df['path'].str.split(pat=os.sep).str.get(0)
            .str.cat(df['title'], sep=' ')
        )

        return df.to_dict(orient='records')

    def list(self, request):
        # generate the folders path regex, e.g. /path/to/images/**/*.fits
        # first generate the list of main subfolders, e.g. [EPOCH01, ... ]
        img_root = settings.RAW_IMAGE_DIR
        if not os.path.exists(img_root):
            msg = 'Raw image folder does not exists'
            messages.error(request, msg)
            raise Http404(msg)

        img_subfolders_gen = filter(
            lambda x: os.path.isdir(os.path.join(img_root, x)),
            os.listdir(img_root)
        )
        img_subfolders1, img_subfolders2 = tee(img_subfolders_gen)
        img_regex_list = list(map(
            lambda x: os.path.join(img_root, x, '**' + os.sep + '*.fits'),
            img_subfolders1
        ))
        selavy_regex_list = list(map(
            lambda x: os.path.join(img_root, x, '**' + os.sep + '*.txt'),
            img_subfolders2
        ))
        # add home directory for user and jupyter-user (user = github name)
        req_user = request.user.username
        for user in [f'~{req_user}', f'~jupyter-{req_user}']:
            print(user)
            user_home = os.path.expanduser(user)
            if os.path.exists(user_home):
                img_regex_list.append(os.path.join(user_home, '**' + os.sep + '*.fits'))
                selavy_regex_list.append(os.path.join(user_home, '**' + os.sep + '*.txt'))

        # generate raw image list in parallel
        dask_list = db.from_sequence(img_regex_list)
        fits_files = (
            dask_list.map(lambda x: glob(x, recursive=True))
            .flatten()
            .compute()
        )
        if not fits_files:
            messages.info(request, 'no fits files found')

        # generate raw image list in parallel
        dask_list = db.from_sequence(selavy_regex_list)
        selavy_files = (
            dask_list.map(lambda x: glob(x, recursive=True))
            .flatten()
            .compute()
        )
        if not fits_files:
            messages.info(request, 'no selavy files found')

        # generate response datastructure
        data = {
            'fits': self.gen_title_data_tokens(fits_files),
            'selavy': self.gen_title_data_tokens(selavy_files)
        }
        serializer = RawImageSelavyListSerializer(data)

        return Response(serializer.data)


class ValidateRunConfigSet(ViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_value_regex = '[-\w]+'
    lookup_field = 'runname'

    def retrieve(self, request, runname=None):
        if not runname:
            return Response(
                {
                    'message': {
                        'severity': 'danger',
                        'text': [
                            'Error in config validation:',
                            'Run name parameter null or not passed'
                        ]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        path = os.path.join(
            settings.PIPELINE_WORKING_DIR,
            runname,
            'config.py'
        )

        if not os.path.exists(path):
            return Response(
                {
                    'message': {
                        'severity': 'danger',
                        'text': [
                            'Error in config validation:',
                            f'Path {path} not existent'
                        ]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            pipeline = Pipeline(name=runname, config_path=path)
            pipeline.validate_cfg()
        except Exception as e:
            trace = traceback.format_exc().splitlines()
            trace = '\n'.join(trace[-4:])
            msg = {
                'message': {
                'severity': 'danger',
                'text': (
                    f'Error in config validation:\n{e}\n{trace}'
                ).split('\n')
                }
            }
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        msg = {
            'message': {
            'severity': 'success',
            'text': ['Configuration is valid.']
            }
        }

        return Response(msg, status=status.HTTP_202_ACCEPTED)
