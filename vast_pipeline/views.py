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
from astropy.coordinates import SkyCoord, Angle, Longitude, Latitude
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astroquery.simbad import Simbad
from astroquery.ned import Ned

from django.http import FileResponse, Http404, HttpResponseRedirect
from django.db.models import F, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.contrib import messages

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.authentication import (
    SessionAuthentication, BasicAuthentication
)
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.auth.decorators import login_required

from vast_pipeline.models import Image, Measurement, Run, Source, SourceFav
from vast_pipeline.serializers import (
    ImageSerializer, MeasurementSerializer, RunSerializer,
    SourceSerializer, RawImageSelavyListSerializer,
    SourceFavSerializer, SesameResultSerializer, CoordinateValidatorSerializer,
    ExternalSearchSerializer
)
from vast_pipeline.utils.utils import deg2dms, deg2hms, parse_coord, equ2gal
from vast_pipeline.utils.view import generate_colsfields, get_skyregions_collection
from vast_pipeline.management.commands.initpiperun import initialise_run
from vast_pipeline.forms import PipelineRunForm
from vast_pipeline.pipeline.main import Pipeline


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
    bob=False
    check_run_db = Run.objects.exists()
    totals['nr_meas'] = (
        dd.read_parquet(meas_glob, columns='id')
        .shape[0]
        .compute()
    ) if (check_run_db and meas_glob) else 0

    f_meas_glob = glob(os.path.join(
        settings.PIPELINE_WORKING_DIR,
        '*/forced_meas*.parquet',
    ))
    totals['nr_f_meas'] = (
        dd.read_parquet(f_meas_glob, columns='id')
        .shape[0]
        .compute()
    ) if (check_run_db and f_meas_glob) else 0

    context = {
        'totals': totals,
        'd3_celestial_skyregions': get_skyregions_collection(),
        'static_url': settings.STATIC_URL
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
                return redirect('vast_pipeline:run_detail', id=p_run.id)
            except Exception as e:
                messages.error(
                    request,
                    f'Issue in pipeline run initilisation: {e}'
                )
                return redirect('vast_pipeline:run_index')
        else:
            messages.error(
                request,
                f'Form not valid: {form.errors}'
            )
            return redirect('vast_pipeline:run_index')

    fields = [
        'name',
        'time',
        'path',
        'comment',
        'n_images',
        'n_sources',
        'status'
    ]

    colsfields = generate_colsfields(
        fields,
        {'name': reverse('vast_pipeline:run_detail', args=[1])[:-2]}
    )

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
                'api': (
                    reverse('vast_pipeline:api_pipe_runs-list') +
                    '?format=datatables'
                ),
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

    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        qs = Image.objects.filter(run__id=pk).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ImageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ImageSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def measurements(self, request, pk=None):
        qs = Measurement.objects.filter(image__run__in=[pk]).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MeasurementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MeasurementSerializer(qs, many=True)
        return Response(serializer.data)


# Run detail
@login_required
def RunDetail(request, id):
    p_run_model = Run.objects.filter(id=id).prefetch_related('image_set').get()
    p_run = p_run_model.__dict__
    # build config path for POST and later
    p_run['user'] = p_run_model.user.username if p_run_model.user else None
    p_run['status'] = p_run_model.get_status_display()
    if p_run_model.image_set.exists() and p_run_model.status == 'Completed':
        images = list(p_run_model.image_set.values('name', 'datetime'))
        img_paths = list(map(
            lambda x: os.path.join(
                settings.PIPELINE_WORKING_DIR,
                'images',
                x.replace('.','_'),
                'measurements.parquet'
            ),
            p_run_model.image_set.values_list('name', flat=True)
        ))
        p_run['nr_meas'] = (
            dd.read_parquet(img_paths, columns='id')
            .shape[0]
            .compute()
        )
    else:
        p_run['nr_meas'] = 'N.A.'

    forced_path = glob(
        os.path.join(p_run['path'], 'forced_measurements_*.parquet')
    )
    if forced_path and p_run_model.status == 'Completed':
        try:
            p_run['nr_frcd'] = (
                dd.read_parquet(forced_path, columns='id')
                .shape[0]
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

    if p_run_model.status == 'Completed':
        p_run['new_srcs'] = Source.objects.filter(
            run__id=p_run['id'],
            new=True,
        ).count()
    else:
        p_run['new_srcs'] = 'N.A.'

    # read run config
    f_path = os.path.join(p_run['path'], 'config.py')
    if os.path.exists(f_path):
        with open(f_path) as fp:
            p_run['config_txt'] = fp.read()

    # read run log file
    f_path = os.path.join(p_run['path'], 'log.txt')
    if os.path.exists(f_path):
        with open(f_path) as fp:
            p_run['log_txt'] = fp.read()

    image_fields = [
        'name',
        'datetime',
        'frequency',
        'ra',
        'dec',
        'rms_median',
        'rms_min',
        'rms_max',
        'beam_bmaj',
        'beam_bmin',
        'beam_bpa',
    ]

    image_colsfields = generate_colsfields(
        image_fields,
        {'name': reverse('vast_pipeline:image_detail', args=[1])[:-2]},
        not_searchable_col=['frequency']
    )

    image_datatable = {
        'table_id': 'imageTable',
        'api': (
            reverse('vast_pipeline:api_pipe_runs-images', args=[p_run['id']]) +
            '?format=datatables'
        ),
        'colsFields': image_colsfields,
        'colsNames': [
            'Name',
            'Time (UTC)',
            'Frequency (MHz)',
            'RA (deg)',
            'Dec (deg)',
            'Median RMS (mJy)',
            'Min RMS (mJy)',
            'Max RMS (mJy)',
            'Beam Major (arcsec)',
            'Beam Minor (arcsec)',
            'Beam PA (deg)'
        ],
        'search': True,
    }

    meas_fields = [
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
        'frequency',
        'compactness',
        'snr',
        'has_siblings',
        'forced'
    ]

    meas_colsfields = generate_colsfields(
        meas_fields,
        {'name': reverse('vast_pipeline:measurement_detail', args=[1])[:-2]},
        not_searchable_col=['frequency']
    )

    meas_datatable = {
        'table_id': 'measTable',
        'api': (
            reverse('vast_pipeline:api_pipe_runs-measurements', args=[p_run['id']]) +
            '?format=datatables'
        ),
        'colsFields': meas_colsfields,
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
            'Frequency (MHz)',
            'Compactness',
            'SNR',
            'Has siblings',
            'Forced Extraction'
        ],
        'search': True,
    }

    return render(
        request, 'run_detail.html',
        {
            'p_run': p_run,
            'datatables': [image_datatable, meas_datatable],
            'd3_celestial_skyregions': get_skyregions_collection(run_id=id),
            'static_url': settings.STATIC_URL
        }
    )


# Images table
@login_required
def ImageIndex(request):
    fields = [
        'name',
        'datetime',
        'frequency',
        'ra',
        'dec',
        'rms_median',
        'rms_min',
        'rms_max',
        'beam_bmaj',
        'beam_bmin',
        'beam_bpa'
    ]

    colsfields = generate_colsfields(
        fields,
        {'name': reverse('vast_pipeline:image_detail', args=[1])[:-2]},
        not_searchable_col=['frequency']
    )

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
                'api': (
                    reverse('vast_pipeline:api_images-list') +
                    '?format=datatables'
                ),
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'Time (UTC)',
                    'Frequency (MHz)',
                    'RA (deg)',
                    'Dec (deg)',
                    'Median RMS (mJy)',
                    'Min RMS (mJy)',
                    'Max RMS (mJy)',
                    'Beam Major (arcsec)',
                    'Beam Minor (arcsec)',
                    'Beam PA (deg)'
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

    @action(detail=True, methods=['get'])
    def measurements(self, request, pk=None):
        qs = Measurement.objects.filter(image__in=[pk], forced=False).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MeasurementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MeasurementSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def runs(self, request, pk=None):
        image = self.queryset.get(pk=pk)
        qs = image.run.all().order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = RunSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RunSerializer(qs, many=True)
        return Response(serializer.data)


@login_required
def ImageDetail(request, id, action=None):
    # source data
    image = Image.objects.all().order_by('id')
    if action:
        if action == 'next':
            img = image.filter(id__gt=id)
            if img.exists():
                image = img.annotate(
                    frequency=F('band__frequency'),
                    bandwidth=F('band__bandwidth'),
                    n_runs=Count('run')
                ).values().first()
            else:
                image = image.filter(id=id).annotate(
                    frequency=F('band__frequency'),
                    bandwidth=F('band__bandwidth'),
                    n_runs=Count('run')
                ).values().get()
        elif action == 'prev':
            img = image.filter(id__lt=id)
            if img.exists():
                image = img.annotate(
                    frequency=F('band__frequency'),
                    bandwidth=F('band__bandwidth'),
                    n_runs=Count('run')
                ).values().last()
            else:
                image = image.filter(id=id).annotate(
                    frequency=F('band__frequency'),
                    bandwidth=F('band__bandwidth'),
                    n_runs=Count('run')
                ).values().get()
    else:
        image = image.filter(id=id).annotate(
            frequency=F('band__frequency'),
            bandwidth=F('band__bandwidth'),
            n_runs=Count('run')
        ).values().get()

    image['aladin_ra'] = image['ra']
    image['aladin_dec'] = image['dec']
    image['aladin_zoom'] = 17.0
    image['aladin_box_ra'] = image['physical_bmaj']
    image['aladin_box_dec'] = image['physical_bmin']
    image['ra_hms'] = deg2hms(image['ra'], hms_format=True)
    image['dec_dms'] = deg2dms(image['dec'], dms_format=True)
    image['l'], image['b'] = equ2gal(image['ra'], image['dec'])

    image['datetime'] = image['datetime'].isoformat()
    image['n_meas'] = (
        pd.read_parquet(image['measurements_path'], columns=['id'])
        .shape[0]
    )

    meas_fields = [
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
        'frequency',
        'compactness',
        'snr',
        'has_siblings',
        'forced'
    ]

    meas_colsfields = generate_colsfields(
        meas_fields,
        {'name': reverse('vast_pipeline:measurement_detail', args=[1])[:-2]},
        not_searchable_col=['frequency']
    )

    meas_datatable = {
        'table_id': 'measDataTable',
        'api': (
            reverse('vast_pipeline:api_images-measurements', args=[image['id']]) +
            '?format=datatables'
        ),
        'colsFields': meas_colsfields,
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
            'Frequency (MHz)',
            'Compactness',
            'SNR',
            'Has siblings',
            'Forced Extraction'
        ],
        'search': True,
    }

    run_fields = [
        'name',
        'time',
        'path',
        'comment',
        'n_images',
        'n_sources',
        'status'
    ]

    run_colsfields = generate_colsfields(
        run_fields,
        {'name': reverse('vast_pipeline:run_detail', args=[1])[:-2]}
    )

    run_datatable = {
        'table_id': 'runDataTable',
        'api': (
            reverse('vast_pipeline:api_images-runs', args=[image['id']]) +
            '?format=datatables'
        ),
        'colsFields': run_colsfields,
        'colsNames': [
            'Name',
            'Run Datetime',
            'Path',
            'Comment',
            'Nr Images',
            'Nr Sources',
            'Run Status'
        ],
        'search': True,
    }

    context = {'image': image, 'datatables': [meas_datatable, run_datatable]}
    return render(request, 'image_detail.html', context)


# Measurements table
@login_required
def MeasurementIndex(request):
    fields = [
        'name',
        'ra',
        'uncertainty_ew',
        'dec',
        'uncertainty_ns',
        'flux_int',
        'flux_int_err',
        'flux_peak',
        'flux_peak_err',
        'frequency',
        'compactness',
        'snr',
        'has_siblings',
        'forced'
    ]

    colsfields = generate_colsfields(
        fields,
        {'name': reverse('vast_pipeline:measurement_detail', args=[1])[:-2]},
        not_searchable_col=['frequency']
    )

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
                'api': (
                    reverse('vast_pipeline:api_measurements-list') +
                    '?format=datatables'
                ),
                'colsFields': colsfields,
                'colsNames': [
                    'Name',
                    'RA (deg)',
                    'RA Error (arcsec)',
                    'Dec (deg)',
                    'Dec Error (arcsec)',
                    'Int. Flux (mJy)',
                    'Int. Flux Error (mJy)',
                    'Peak Flux (mJy/beam)',
                    'Peak Flux Error (mJy/beam)',
                    'Frequency (MHz)',
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
    queryset = Measurement.objects.all().order_by('id')
    serializer_class = MeasurementSerializer

    def get_queryset(self):
        run_id = self.request.query_params.get('run_id', None)
        return self.queryset.filter(source__id=run_id) if run_id else self.queryset

    @action(detail=True, methods=['get'])
    def siblings(self, request, pk=None):
        measurement = self.queryset.get(pk=pk)
        image_id = measurement.image_id
        island_id = measurement.island_id
        qs = self.queryset.filter(
            image__id=image_id, island_id=island_id
        ).exclude(pk=pk)
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sources(self, request, pk=None):
        measurement = self.queryset.get(pk=pk)
        qs = measurement.source.all()
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SourceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SourceSerializer(qs, many=True)
        return Response(SourceSerializer.data)


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
                    frequency=F('image__band__frequency')
                ).values().first()
            else:
                measurement = measurement.filter(id=id).annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                    source_ids=ArrayAgg('source__id'),
                    source_names=ArrayAgg('source__name'),
                    frequency=F('image__band__frequency')
                ).values().get()
        elif action == 'prev':
            msr = measurement.filter(id__lt=id)
            if msr.exists():
                measurement = msr.annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                    source_ids=ArrayAgg('source__id'),
                    frequency=F('image__band__frequency')
                ).values().last()
            else:
                measurement = measurement.filter(id=id).annotate(
                    datetime=F('image__datetime'),
                    image_name=F('image__name'),
                    source_ids=ArrayAgg('source__id'),
                    frequency=F('image__band__frequency')
                ).values().get()
    else:
        measurement = measurement.filter(id=id).annotate(
            datetime=F('image__datetime'),
            image_name=F('image__name'),
            source_ids=ArrayAgg('source__id'),
            frequency=F('image__band__frequency')
        ).values().get()

    measurement['aladin_ra'] = measurement['ra']
    measurement['aladin_dec'] = measurement['dec']
    measurement['aladin_zoom'] = 0.15
    measurement['ra_hms'] = deg2hms(measurement['ra'], hms_format=True)
    measurement['dec_dms'] = deg2dms(measurement['dec'], dms_format=True)
    measurement['l'], measurement['b'] = equ2gal(measurement['ra'], measurement['dec'])

    measurement['datetime'] = measurement['datetime'].isoformat()

    measurement['nr_sources'] = (
        0 if measurement['source_ids'] == [None] else len(measurement['source_ids'])
    )

    sibling_fields = [
        'name',
        'flux_peak',
        'island_id',
    ]

    sibling_colsfields = generate_colsfields(
        sibling_fields,
        {'name': reverse('vast_pipeline:measurement_detail', args=[1])[:-2]}
    )

    sibling_datatable = {
        'table_id': 'siblingTable',
        'api': (
            reverse('vast_pipeline:api_measurements-siblings', args=[measurement['id']]) +
            '?format=datatables'
        ),
        'colsFields': sibling_colsfields,
        'colsNames': [
            'Name',
            'Peak Flux (mJy/beam)',
            'Island ID'
        ],
        'search': True,
    }

    source_fields = [
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

    source_colsfields = generate_colsfields(
        source_fields,
        {'name': reverse('vast_pipeline:source_detail', args=[1])[:-2]}
    )

    source_datatable = {
        'table_id': 'measSourcesTable',
        'api': (
            reverse('vast_pipeline:api_measurements-sources', args=[measurement['id']]) +
            '?format=datatables'
        ),
        'colsFields': source_colsfields,
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
        'search': True,
    }

    context = {
        'measurement': measurement,
        'datatables': [source_datatable, sibling_datatable]
    }
    # add base url for using in JS9 if assigned
    if settings.BASE_URL and settings.BASE_URL != '':
        context['base_url'] = settings.BASE_URL.strip('/')

    return render(request, 'measurement_detail.html', context)


class SourceViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SourceSerializer

    def get_queryset(self):
        qs = Source.objects.all().filter(run__status='END')

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
        coordsys = self.request.query_params.get('coordsys')
        coord_string = self.request.query_params.get('coord')
        wavg_ra, wavg_dec = None, None
        if coord_string:
            coord = parse_coord(coord_string, coord_frame=coordsys).transform_to("icrs")
            wavg_ra = coord.ra.deg
            wavg_dec = coord.dec.deg

        if wavg_ra and wavg_dec and radius:
            radius = float(radius) / radius_conversions[radiusUnit]
            qs = qs.cone_search(wavg_ra, wavg_dec, radius)

        return qs

    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        qs = Source.objects.filter(related__in=[pk]).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


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

    colsfields = generate_colsfields(
        fields,
        {'name': reverse('vast_pipeline:source_detail', args=[1])[:-2]}
    )

    # get all pipeline run names
    p_runs = list(Run.objects.filter(status='END').values('name').all())

    return render(
        request,
        'sources_query.html',
        {
            'breadcrumb': {'title': 'Sources', 'url': request.path},
            'runs': p_runs,
            'datatable': {
                'api': (
                    reverse('vast_pipeline:api_sources-list') +
                    '?format=datatables'
                ),
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
                source = (
                    src.annotate(run_name=F('run__name'))
                    .values()
                    .first()
                )
            else:
                source = (
                    source.filter(id=id)
                    .annotate(run_name=F('run__name'))
                    .values()
                    .get()
                )
        elif action == 'prev':
            src = source.filter(id__lt=id)
            if src.exists():
                source = (
                    src.annotate(run_name=F('run__name'))
                    .values()
                    .last()
                )
            else:
                source = (
                    source.filter(id=id)
                    .annotate(run_name=F('run__name'))
                    .values()
                    .get()
                )
    else:
        source = (
            source.filter(id=id)
            .annotate(run_name=F('run__name'))
            .values()
            .get()
        )
    source['aladin_ra'] = source['wavg_ra']
    source['aladin_dec'] = source['wavg_dec']
    source['aladin_zoom'] = 0.15
    source['wavg_ra_hms'] = deg2hms(source['wavg_ra'], hms_format=True)
    source['wavg_dec_dms'] = deg2dms(source['wavg_dec'], dms_format=True)
    source['wavg_l'], source['wavg_b'] = equ2gal(source['wavg_ra'], source['wavg_dec'])

    # source data
    cols = [
        'id',
        'name',
        'datetime',
        'image_name',
        'frequency',
        'ra',
        'ra_err',
        'dec',
        'dec_err',
        'flux_int',
        'flux_int_err',
        'flux_peak',
        'flux_peak_err',
        'snr',
        'has_siblings',
        'forced',
        'image_id'
    ]
    measurements = list(
        Measurement.objects.filter(source__id=id).annotate(
            datetime=F('image__datetime'),
            image_name=F('image__name'),
            frequency=F('image__band__frequency'),
        ).order_by('datetime').values(*tuple(cols))
    )
    for one_m in measurements:
        one_m['datetime'] = one_m['datetime'].isoformat()

    # add the data for the datatable api
    measurements = {
        'table': 'source_detail',
        'table_id': 'dataTableMeasurements',
        'dataQuery': measurements,
        'colsFields': cols,
        'search': True,
        'order': [2, 'asc'],
        'colsNames': [
            'ID',
            'Name',
            'Date (UTC)',
            'Image',
            'Frequency (MHz)',
            'RA (deg)',
            'RA Error (arcsec)',
            'Dec (deg)',
            'Dec Error (arcsec)',
            'Int. Flux (mJy)',
            'Int. Flux Error (mJy)',
            'Peak Flux (mJy/beam)',
            'Peak Flux Error (mJy/beam)',
            'SNR',
            'Has siblings',
            'Forced Extraction',
            'Image ID'
        ]
    }

    # generate context for related sources datatable
    related_fields = [
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
    related_colsfields = generate_colsfields(
        related_fields,
        {'name': reverse('vast_pipeline:source_detail', args=[1])[:-2]}
    )
    related_datatables = {
        'table_id': 'dataTableRelated',
        'api': (
            reverse('vast_pipeline:api_sources-related', args=[source['id']]) +
            '?format=datatables'
        ),
        'colsFields': related_colsfields,
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
        'search': True,
    }

    context = {
        'source': source,
        'datatables': [measurements, related_datatables],
        # flag to deactivate starring and render yellow star
        'sourcefav': (
            SourceFav.objects.filter(
                user__id=request.user.id,
                source__id=source['id']
            )
            .exists()
        )
    }
    # add base url for using in JS9 if assigned
    if settings.BASE_URL and settings.BASE_URL != '':
        context['base_url'] = settings.BASE_URL.strip('/')

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
            request: Django HTTPRequest. Supports 4 URL GET parameters:
                - selection_model: either "measurement" or "source" (defaults to "measurement").
                - selection_id: the id for the given `selection_model`.
                - run_id: (optional) only return measurements for sources with the given pipeline
                    run id (defaults to None).
                - no_forced: (optional) If true, exclude forced-photometry measurements (defaults
                    to False).
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
        run_id = request.GET.get("run_id", None)
        no_forced = request.GET.get("forced", False)

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
        if run_id:
            measurements = measurements.filter(source__run__id=run_id)
        if no_forced:
            measurements = measurements.filter(forced=False)
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
                    "link": reverse(f"vast_pipeline:{selection_model}_detail", args=[selection_id]),
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


class RunConfigSet(ViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Run.objects.all()

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        if not pk:
            return Response(
                {
                    'message': {
                        'severity': 'danger',
                        'text': [
                            'Error in config validation:',
                            'Run pk parameter null or not passed'
                        ]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        p_run = get_object_or_404(self.queryset, pk=pk)
        path = os.path.join(p_run.path, 'config.py')

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
            pipeline = Pipeline(name=p_run.name, config_path=path)
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

    @action(detail=True, methods=['post'])
    def write(self, request, pk=None):
        # this post is for writing the config text (modified or not)
        # from the UI to a config.py file
        if not pk:
            messages.error(
                request,
                'Error in config write: Run pk parameter null or not passed'
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        try:
            p_run = get_object_or_404(self.queryset, pk=pk)
        except Exception as e:
            messages.error(request, f'Error in config write: {e}')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        config_text = request.POST.get('config_text', None)
        if config_text:
            f_path = os.path.join(p_run.path, 'config.py')
            try:
                with open(f_path, 'w') as fp:
                    fp.write(config_text)

                messages.success(
                    request,
                    'Pipeline config written successfully'
                )
            except Exception as e:
                messages.error(request, f'Error in config write: {e}')
        else:
            messages.info(request, 'Error in config write: Config text null')

        return HttpResponseRedirect(
            reverse('vast_pipeline:run_detail', args=[p_run.id])
        )


class SourceFavViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SourceFavSerializer

    def get_queryset(self):
        qs = SourceFav.objects.all().order_by('id')
        user = self.request.query_params.get('user')
        if user:
            qs = qs.filter(user__username=user)

        return qs

    def create(self, request):
        # TODO: couldn't get this below to work, so need to re-write using
        # serializer
        # serializer = SourceFavSerializer(data=request.data)
        # if serializer.is_valid():
        #     serializer.save()
        #     return Response(serializer.data, status=status.HTTP_201_CREATED)
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.dict()
        data.pop('csrfmiddlewaretoken')
        data['user_id'] = request.user.id
        try:
            check = (
                SourceFav.objects.filter(
                    user__id=data['user_id'],
                    source__id=data['source_id']
                )
                .exists()
            )
            if check:
                messages.error(request, 'Source already added to favourites!')
            else:
                fav = SourceFav(**data)
                fav.save()
                messages.info(request, 'Added to favourites successfully')
        except Exception as e:
            messages.error(
                request,
                f'Errors in adding source to favourites: \n{e}'
            )

        return HttpResponseRedirect(reverse('vast_pipeline:source_detail', args=[data['source_id']]))

    def destroy(self, request, pk=None):
        try:
            qs = SourceFav.objects.filter(id=pk)
            if qs.exists():
                qs.delete()
                messages.success(
                    request,
                    'Favourite source deleted successfully'
                )
                return Response({'message': 'ok'}, status=status.HTTP_200_OK)
            else:
                messages.info(request, 'Not found')
                return Response(
                    {'message': 'not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            messages.error(request, 'Error in deleting the favourite source')
            return Response(
                {'message': 'error in request'},
                status=status.HTTP_400_BAD_REQUEST
            )


@login_required
def UserSourceFavsList(request):
    fields = ['source.name', 'comment', 'source.run.name', 'deletefield']

    api_col_dict = {
        'source.name': reverse('vast_pipeline:source_detail', args=[1])[:-2],
        'source.run.name': reverse('vast_pipeline:run_detail', args=[1])[:-2]
    }
    colsfields = generate_colsfields(fields, api_col_dict, ['deletefield'])

    return render(
        request,
        'generic_table.html',
        {
            'text': {
                'title': 'Favourite Sources',
                'description': 'List of favourite (starred) sources',
                'breadcrumb': {'title': 'Favourite Sources', 'url': request.path},
            },
            'datatable': {
                'api': (
                    reverse('vast_pipeline:api_sources_favs-list') +
                    f'?format=datatables&user={request.user.username}'
                ),
                'colsFields': colsfields,
                'colsNames': ['Source', 'Comment', 'Pipeline Run', 'Delete'],
                'search': True,
            }
        }
    )


class UtilitiesSet(ViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    @action(methods=['get'], detail=False)
    def sesame_search(self, request: Request) -> Response:
        """Query the Sesame name resolver service and return a coordinate.

        Args:
            request (Request): Django REST framework Request object with GET parameters:
                - object_name (str): Object name to query.
                - service (str, optional): Sesame service to query (all, simbad, ned, vizier).
                    Defaults to "all".

        Returns:
            Response: a Django REST framework Response. Will return JSON with status code:
                - 400 if the query params fail validation (i.e. if an invalid Sesame service
                    or no object name is provided) or if the name resolution fails. Error
                    messages are returned as an array of strings under the relevant query
                    parameter key. e.g. {"object_name": ["This field may not be blank."]}.
                - 200 if successful. Response data contains the passed in query parameters and
                    the resolved coordinate as a sexagesimal string with units hourangle, deg
                    under the key `coord`.
        """
        object_name = request.query_params.get("object_name", "")
        service = request.query_params.get("service", "all")

        serializer = SesameResultSerializer(data=dict(object_name=object_name, service=service))
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def coordinate_validator(self, request: Request) -> Response:
        """Validate a coordinate string.

        Args:
            request (Request): Django REST framework Request object with GET parameters:
                - coord (str): the coordinate string to validate.
                - frame (str): the frame for the given coordinate string e.g. icrs, galactic.

        Returns:
            Response: a Django REST framework Response. Will return JSON with status code:
                - 400 if the query params fail validation, i.e. if a frame unknown to Astropy
                    is given, or the coordinate string fails to parse. Error messages are
                    returned as an array of strings under the relevant query parameter key.
                    e.g. {"coord": ["This field may not be blank."]}.
                - 200 if the coordinate string successfully validates. No other data is returned.
        """
        coord_string = request.query_params.get("coord", "")
        frame = request.query_params.get("frame", "")

        serializer = CoordinateValidatorSerializer(data=dict(coord=coord_string, frame=frame))
        serializer.is_valid(raise_exception=True)
        return Response()

    @action(methods=["get"], detail=False)
    def simbad_ned_search(self, request: Request) -> Response:
        """Perform a cone search with SIMBAD and NED and return the combined results.

        Args:
            request (Request): Django REST Framework Request object get GET parameters:
                - coord (str): the coordinate string to validate. Interpreted by
                    `astropy.coordiantes.SkyCoord`.
                - radius (str): the cone search radius with unit, e.g. "1arcmin".
                    Interpreted by `astropy.coordinates.Angle`

        Raises:
            serializers.ValidationError: if either the coordinate or radius parameters
                cannot be interpreted by `astropy.coordiantes.SkyCoord` or
                `astropy.coordinates.Angle`, respectively.

        Returns:
            Response: a Django REST framework Response containing result records as a list
                under the data object key. Each record contains the properties:
                    - object_name: the name of the astronomical object.
                    - database: the source of the result, e.g. SIMBAD or NED.
                    - separation_arcsec: separation to the query coordinate in arcsec.
                    - otype: object type.
                    - otype_long: long form of the object type (only available for SIMBAD).
                    - ra_hms: RA coordinate string in <HH>h<MM>m<SS.SSS>s format.
                    - dec_dms: Dec coordinate string in ±<DD>d<MM>m<SS.SSS>s format.
        """
        coord_string = request.query_params.get("coord", "")
        radius_string = request.query_params.get("radius", "1arcmin")

        # validate inputs
        try:
            coord = parse_coord(coord_string)
        except ValueError as e:
            raise serializers.ValidationError({"coord": str(e.args[0])})

        try:
            radius = Angle(radius_string)
        except ValueError as e:
            raise serializers.ValidationError({"radius": str(e.args[0])})

        # SIMBAD cone search
        CustomSimbad = Simbad()
        CustomSimbad.add_votable_fields(
            "distance_result", "otype(S)", "otype(V)", "otypes",
        )
        simbad_result_table = CustomSimbad.query_region(coord, radius=radius)
        if simbad_result_table is None:
            simbad_results_dict_list = []
        else:
            simbad_results_df = simbad_result_table[
                ["MAIN_ID", "DISTANCE_RESULT", "OTYPE_S", "OTYPE_V", "RA", "DEC"]
            ].to_pandas()
            bytestring_fields = ["MAIN_ID", "OTYPE_S", "OTYPE_V"]
            simbad_results_df[bytestring_fields] = simbad_results_df[
                bytestring_fields
            ].apply(lambda col: col.str.decode("utf-8"))
            simbad_results_df = simbad_results_df.rename(
                columns={
                    "MAIN_ID": "object_name",
                    "DISTANCE_RESULT": "separation_arcsec",
                    "OTYPE_S": "otype",
                    "OTYPE_V": "otype_long",
                    "RA": "ra_hms",
                    "DEC": "dec_dms",
                }
            )
            simbad_results_df["database"] = "SIMBAD"
            # convert coordinates to RA (hms) Dec (dms) strings
            simbad_results_df["ra_hms"] = Longitude(
                simbad_results_df["ra_hms"], unit="hourangle"
            ).to_string(unit="hourangle")
            simbad_results_df["dec_dms"] = Latitude(
                simbad_results_df["dec_dms"], unit="deg"
            ).to_string(unit="deg")
            simbad_results_dict_list = simbad_results_df.to_dict(orient="records")

        # NED cone search
        ned_result_table = Ned.query_region(coord, radius=radius)
        if ned_result_table is None or len(ned_result_table) == 0:
            ned_results_dict_list = []
        else:
            ned_results_df = ned_result_table[
                ["Object Name", "Separation", "Type", "RA", "DEC"]
            ].to_pandas()
            bytestring_fields = ["Object Name", "Type"]
            ned_results_df[bytestring_fields] = ned_results_df[bytestring_fields].apply(
                lambda col: col.str.decode("utf-8")
            )
            ned_results_df = ned_results_df.rename(
                columns={
                    "Object Name": "object_name",
                    "Separation": "separation_arcsec",
                    "Type": "otype",
                    "RA": "ra_hms",
                    "DEC": "dec_dms",
                }
            )
            ned_results_df["otype_long"] = ""  # NED does not supply verbose object types
            # convert NED result separation (arcmin) to arcsec
            ned_results_df["separation_arcsec"] = (
                ned_results_df["separation_arcsec"] * 60
            )
            # convert coordinates to RA (hms) Dec (dms) strings
            ned_results_df["ra_hms"] = Longitude(
                ned_results_df["ra_hms"], unit="deg"
            ).to_string(unit="hourangle")
            ned_results_df["dec_dms"] = Latitude(
                ned_results_df["dec_dms"], unit="deg"
            ).to_string(unit="deg")
            ned_results_df["database"] = "NED"
            # convert dataframe to dict and replace float NaNs with None for JSON encoding
            ned_results_dict_list = ned_results_df.sort_values(
                "separation_arcsec"
            ).to_dict(orient="records")

        results_dict_list = simbad_results_dict_list + ned_results_dict_list
        serializer = ExternalSearchSerializer(data=results_dict_list, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
