import io
import os
import json
import logging
import traceback
import dask.dataframe as dd
import dask.bag as db
import pandas as pd

from typing import Dict, Any, Tuple
from glob import glob
from itertools import tee

from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle, Longitude, Latitude
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from astroquery.simbad import Simbad
from astroquery.ned import Ned

from bokeh.embed import json_item

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F, Count, QuerySet
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.safestring import mark_safe

from django_q.tasks import async_task

from rest_framework import status
import rest_framework.decorators
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

from vast_pipeline.plots import plot_lightcurve
from vast_pipeline.models import (
    Comment, CommentableModel, Image, Measurement, Run, Source, SourceFav,
)
from vast_pipeline.serializers import (
    ImageSerializer, MeasurementSerializer, RunSerializer,
    SourceSerializer, RawImageSelavyListSerializer,
    SourceFavSerializer, SesameResultSerializer, CoordinateValidatorSerializer,
    ExternalSearchSerializer
)
from vast_pipeline.utils.utils import deg2dms, deg2hms, parse_coord, equ2gal
from vast_pipeline.utils.view import generate_colsfields, get_skyregions_collection
from vast_pipeline.management.commands.initpiperun import initialise_run
from vast_pipeline.forms import PipelineRunForm, CommentForm, TagWithCommentsForm
from vast_pipeline.pipeline.main import Pipeline
from vast_pipeline.pipeline.utils import get_create_p_run


logger = logging.getLogger(__name__)


def _process_comment_form_get_comments(
    request, instance: CommentableModel
) -> Tuple[CommentForm, "QuerySet[Comment]"]:
    """Process the comment form and return the form and comment objects. If the `request`
    method was POST, create a `Comment` object attached to `instance`.

    Args:
        request: Django HTTP request object.
        instance (CommentableModel): Django object that is a subclass of `CommentableModel`.
            This is the object the comment will be attached to.

    Returns:
        Tuple[CommentForm, QuerySet[Comment]]: a new, unbound `CommentForm` instance; and
            the `QuerySet` of `Comment` objects attached to `instance`.
    """
    if request.method == "POST":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.author = request.user
            comment.content_object = instance
            comment.save()
    comment_form = CommentForm()

    comment_target_type = ContentType.objects.get_for_model(instance)
    comments = Comment.objects.filter(
        content_type__pk=comment_target_type.id, object_id=instance.id,
    ).order_by("datetime")

    return comment_form, comments


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
    totals['nr_meas'] = Measurement.objects.count()

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
                    mark_safe(
                        f'Pipeline run <b>{p_run.name}</b> '
                        'initilialised successfully!'
                    )
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
                    'Name', 'Run Datetime', 'Path', 'Nr Images',
                    'Nr Sources', 'Run Status'
                ],
                'search': True,
            },
            'runconfig' : settings.PIPE_RUN_CONFIG_DEFAULTS,
            'max_piperun_images': settings.MAX_PIPERUN_IMAGES
        }
    )


class RunViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Run.objects.all()
    serializer_class = RunSerializer

    @rest_framework.decorators.action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        qs = Image.objects.filter(run__id=pk).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ImageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ImageSerializer(qs, many=True)
        return Response(serializer.data)

    @rest_framework.decorators.action(detail=True, methods=['get'])
    def measurements(self, request, pk=None):
        qs = Measurement.objects.filter(image__run__in=[pk]).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MeasurementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MeasurementSerializer(qs, many=True)
        return Response(serializer.data)

    @rest_framework.decorators.action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """
        Launches a pipeline run using a Django Q cluster. Includes a check
        on ownership or admin stataus of the user to make sure processing
        is allowed.

        Args:
            request (Request): Django REST Framework request object.
            pk (int, optional): Run object primary key. Defaults to None.

        Raises:
            Http404: if a Source with the given `pk` cannot be found.

        Returns:
            Response: Returns to the orignal request page (the pipeline run
            detail).
        """
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

        # make sure that only the run creator or an admin can request the run
        # to be processed.
        if (
            p_run.user != request.user.get_username()
            and not request.user.is_staff
        ):
            msg = (
                'You do not have permission to process this pipeline run!'
            )
            messages.error(
                request,
                msg
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        # check that it's not already running or queued
        if p_run.status in ["RUN", "QUE"]:
            msg = (
                f'{p_run.name} is already running or is queued.'
                ' Please wait for the run to complete before trying to'
                ' submit again.'
            )
            messages.error(
                request,
                msg
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        if Run.objects.check_max_runs(settings.MAX_PIPELINE_RUNS):
            msg = (
                'The maximum number of simultaneous pipeline runs has been'
                f' reached ({settings.MAX_PIPELINE_RUNS})! Please try again'
                ' when other jobs have finished.'
            )
            messages.error(
                request,
                msg
            )
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        try:
            with transaction.atomic():
                p_run.status = 'QUE'
                p_run.save()
            debug_flag = request.POST.get('debug', 'debugOff')
            debug_flag = True if debug_flag == 'debugOn' else False
            async_task(
                'vast_pipeline.management.commands.runpipeline.run_pipe',
                p_run.name, p_run.path, p_run, False, debug_flag,
                task_name=p_run.name, ack_failure=True, user=request.user
            )
            msg = mark_safe(
                f'<b>{p_run.name}</b> successfully sent to the queue!<br><br>Refresh the'
                ' page to check the status.'
            )
            messages.success(
                request,
                msg
            )
        except Exception as e:
            with transaction.atomic():
                p_run.status = 'ERR'
                p_run.save()
            messages.error(request, f'Error in running pipeline: {e}')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        return HttpResponseRedirect(
            reverse('vast_pipeline:run_detail', args=[p_run.id])
        )


# Run detail
@login_required
def RunDetail(request, id):
    p_run_model = Run.objects.filter(id=id).prefetch_related('image_set').get()
    p_run = p_run_model.__dict__
    # build config path for POST and later
    p_run['user'] = p_run_model.user.username if p_run_model.user else None
    p_run['status'] = p_run_model.get_status_display()
    # Change measurement count to N.A. if run is not complete.
    if p_run_model.image_set.exists() and p_run_model.status == 'Completed':
        p_run['nr_meas'] = p_run['n_selavy_measurements']
        p_run['nr_frcd'] = p_run['n_forced_measurements']
        p_run['nr_srcs'] = p_run['n_sources']
    else:
        p_run['nr_meas'] = 'N/A'
        p_run['nr_frcd'] = 'N/A'
        p_run['nr_srcs'] = 'N/A'

    if p_run_model.status == 'Completed':
        p_run['new_srcs'] = Source.objects.filter(
            run__id=p_run['id'],
            new=True,
        ).count()
    else:
        p_run['new_srcs'] = 'N/A'

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
        'order': [1, 'asc']
    }

    meas_fields = [
        'name',
        'ra',
        'ra_err',
        'uncertainty_ew',
        'dec',
        'dec_err',
        'uncertainty_ns',
        'flux_peak',
        'flux_peak_err',
        'flux_peak_isl_ratio',
        'flux_int',
        'flux_int_err',
        'flux_int_isl_ratio',
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
            'Peak Flux (mJy/beam)',
            'Peak Flux Error (mJy/beam)',
            'Peak Flux Isl. Ratio',
            'Int. Flux (mJy)',
            'Int. Flux Error (mJy)',
            'Int. Flux Isl. Ratio',
            'Frequency (MHz)',
            'Compactness',
            'SNR',
            'Has siblings',
            'Forced Extraction'
        ],
        'search': True,
    }

    context = {
        "p_run": p_run,
        "datatables": [image_datatable, meas_datatable],
        "d3_celestial_skyregions": get_skyregions_collection(run_id=id),
        "static_url": settings.STATIC_URL,
    }

    context["comment_form"], context["comments"] = _process_comment_form_get_comments(
        request,
        p_run_model
    )

    return render(request, 'run_detail.html', context)


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

    @rest_framework.decorators.action(detail=True, methods=['get'])
    def measurements(self, request, pk=None):
        qs = Measurement.objects.filter(image__in=[pk], forced=False).order_by('id')
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = MeasurementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MeasurementSerializer(qs, many=True)
        return Response(serializer.data)

    @rest_framework.decorators.action(detail=True, methods=['get'])
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
        'flux_peak',
        'flux_peak_err',
        'flux_peak_isl_ratio',
        'flux_int',
        'flux_int_err',
        'flux_int_isl_ratio',
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
            'Peak Flux (mJy/beam)',
            'Peak Flux Error (mJy/beam)',
            'Peak Flux Isl. Ratio',
            'Int. Flux (mJy)',
            'Int. Flux Error (mJy)',
            'Int. Flux Isl. Ratio',
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
            'Nr Images',
            'Nr Sources',
            'Run Status'
        ],
        'search': True,
    }

    context = {'image': image, 'datatables': [meas_datatable, run_datatable]}

    context["comment_form"], context["comments"] = _process_comment_form_get_comments(
        request,
        Image.objects.get(id=image["id"])
    )

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
        'flux_peak',
        'flux_peak_err',
        'flux_peak_isl_ratio',
        'flux_int',
        'flux_int_err',
        'flux_int_isl_ratio',
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
                    'Peak Flux (mJy/beam)',
                    'Peak Flux Error (mJy/beam)',
                    'Peak Flux Isl. Ratio',
                    'Int. Flux (mJy)',
                    'Int. Flux Error (mJy)',
                    'Int. Flux Isl. Ratio',
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

    @rest_framework.decorators.action(detail=True, methods=['get'])
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

    @rest_framework.decorators.action(detail=True, methods=['get'])
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
        'flux_peak_isl_ratio',
        'flux_int',
        'flux_int_isl_ratio',
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
            'Peak Flux Isl. Ratio',
            'Int. Flux (mJy/beam)',
            'Int. Flux Isl. Ratio',
            'Island ID'
        ],
        'search': True,
    }

    source_fields = [
        'name',
        'run.name',
        'wavg_ra',
        'wavg_dec',
        'avg_flux_peak',
        'min_flux_peak',
        'max_flux_peak',
        'min_flux_peak_isl_ratio',
        'avg_flux_int',
        'min_flux_int',
        'max_flux_int',
        'min_flux_int_isl_ratio',
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
        'vs_abs_significant_max_int',
        'vs_abs_significant_max_peak',
        'm_abs_significant_max_int',
        'm_abs_significant_max_peak',
        'n_sibl',
        'new',
        'new_high_sigma'
    ]

    api_col_dict = {
        'name': reverse('vast_pipeline:source_detail', args=[1])[:-2],
        'run.name': reverse('vast_pipeline:run_detail', args=[1])[:-2]
    }

    source_colsfields = generate_colsfields(
        source_fields,
        api_col_dict
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
            'Run',
            'W. Avg. RA',
            'W. Avg. Dec',
            'Avg. Peak Flux (mJy/beam)',
            'Min Peak Flux (mJy/beam)',
            'Max Peak Flux (mJy/beam)',
            'Min Peak Flux Isl. Ratio',
            'Avg. Int. Flux (mJy)',
            'Min Int. Flux (mJy)',
            'Max Int. Flux (mJy)',
            'Min Int. Flux Isl. Ratio',
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
            'Max |Vs| int',
            'Max |Vs| peak',
            'Max |m| int',
            'Max |m| peak',
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

    context["comment_form"], context["comments"] = _process_comment_form_get_comments(
        request,
        Measurement.objects.get(id=measurement["id"])
    )

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
            'min_flux_peak',
            'max_flux_peak',
            'min_flux_int',
            'max_flux_int',
            'min_flux_peak_isl_ratio',
            'min_flux_int_isl_ratio',
            'v_int',
            'v_peak',
            'eta_int',
            'eta_peak',
            'vs_abs_significant_max_int',
            'vs_abs_significant_max_peak',
            'm_abs_significant_max_int',
            'm_abs_significant_max_peak',
            'n_meas',
            'n_meas_sel',
            'n_meas_forced',
            'n_rel',
            'new_high_sigma',
            'avg_compactness',
            'min_snr',
            'max_snr',
            'n_neighbour_dist',
            'source_selection',
            'source_selection_type'
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

        if 'source_selection' in self.request.query_params:
            selection_type = self.request.query_params['source_selection_type']
            selection = (
                self.request.query_params['source_selection']
                .replace(" ", "")
                .split(",")
            )
            if selection_type == 'name':
                qry_dict['name__in'] = selection
            else:
                try:
                    selection = [int(i) for i in selection]
                    qry_dict['id__in'] = selection
                except:
                    # this avoids an error on the check if the user has
                    # accidentally entered names with a 'id' selection type.
                    qry_dict['id'] = -1

        if 'newsrc' in self.request.query_params:
            qry_dict['new'] = True

        if 'no_siblings' in self.request.query_params:
            qry_dict['n_sibl'] = 0

        if 'tags_include' in self.request.query_params:
            qry_dict['tags'] = self.request.query_params['tags_include']

        if 'tags_exclude' in self.request.query_params:
            qs = qs.exclude(tags=self.request.query_params['tags_exclude'])

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

    def list(self, request, *args, **kwargs):
        """Override the DRF ModelViewSet.list function to store the source ID order in the
        user session to retain the source order for source detail view next and previous
        button links. Then, call the original list function.
        """
        queryset = self.filter_queryset(self.get_queryset())
        self.request.session["source_query_result_ids"] = list(
            queryset.values_list("id", flat=True)
        )
        return super().list(request, *args, **kwargs)

    @rest_framework.decorators.action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        qs = Source.objects.filter(related__id=pk).order_by('id')
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
        'run.name',
        'wavg_ra',
        'wavg_dec',
        'avg_flux_peak',
        'min_flux_peak',
        'max_flux_peak',
        'min_flux_peak_isl_ratio',
        'avg_flux_int',
        'min_flux_int',
        'max_flux_int',
        'min_flux_int_isl_ratio',
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
        'vs_abs_significant_max_int',
        'vs_abs_significant_max_peak',
        'm_abs_significant_max_int',
        'm_abs_significant_max_peak',
        'n_sibl',
        'new',
        'new_high_sigma'
    ]

    api_col_dict = {
        'name': reverse('vast_pipeline:source_detail', args=[1])[:-2],
        'run.name': reverse('vast_pipeline:run_detail', args=[1])[:-2]
    }

    colsfields = generate_colsfields(
        fields,
        api_col_dict
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
                    'Run',
                    'W. Avg. RA',
                    'W. Avg. Dec',
                    'Avg. Peak Flux (mJy/beam)',
                    'Min Peak Flux (mJy/beam)',
                    'Max Peak Flux (mJy/beam)',
                    'Min Peak Flux Isl. Ratio',
                    'Avg. Int. Flux (mJy)',
                    'Min Int. Flux (mJy)',
                    'Max Int. Flux (mJy)',
                    'Min Int. Flux Isl. Ratio',
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
                    'Max |Vs| int',
                    'Max |Vs| peak',
                    'Max |m| int',
                    'Max |m| peak',
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
def SourceDetail(request, pk):
    # source data
    source = Source.objects.filter(id=pk).annotate(run_name=F('run__name')).values().get()
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
        'flux_peak',
        'flux_peak_err',
        'flux_peak_isl_ratio',
        'flux_int',
        'flux_int_err',
        'flux_int_isl_ratio',
        'local_rms',
        'snr',
        'has_siblings',
        'forced',
        'image_id'
    ]
    measurements = list(
        Measurement.objects.filter(source__id=pk).annotate(
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
            'Peak Flux (mJy/beam)',
            'Peak Flux Error (mJy/beam)',
            'Peak Flux Isl. Ratio',
            'Int. Flux (mJy)',
            'Int. Flux Error (mJy)',
            'Int. Flux Isl. Ratio',
            'Local RMS (mJy)',
            'SNR',
            'Has siblings',
            'Forced Extraction',
            'Image ID'
        ]
    }

    # generate context for related sources datatable
    related_fields = [
        'name',
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

    # find next and previous sources
    source_query_result_id_list = request.session.get("source_query_result_ids", [])
    source_next_id, source_previous_id = None, None
    for i, source_id in enumerate(source_query_result_id_list):
        if source_id == source['id']:
            if i + 1 < len(source_query_result_id_list):
                source_next_id = source_query_result_id_list[i + 1]
            if i - 1 >= 0:
                source_previous_id = source_query_result_id_list[i - 1]
            break

    context = {
        'source': source,
        'source_next_id': source_next_id,
        'source_previous_id': source_previous_id,
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

    # process comments and tags
    source_obj = Source.objects.get(id=source["id"])
    if request.method == "POST":
        tag_comment_form = TagWithCommentsForm(request.POST)
        if tag_comment_form.is_valid():
            comment_text = tag_comment_form.cleaned_data["comment"]

            # process tags
            tag_set = set(tag_comment_form.cleaned_data["tags"])
            current_tag_set = set(source_obj.tags.get_tag_list())
            new_tags = tag_set - current_tag_set
            removed_tags = current_tag_set - tag_set
            # create messages to be appended to any comments to record tag changes
            new_tags_message = (
                f"[Added {', '.join(new_tags)} tag{'s' if len(new_tags) > 1 else ''}]"
                if new_tags
                else ""
            )
            removed_tags_message = (
                f"[Removed {', '.join(removed_tags)} tag{'s' if len(removed_tags) > 1 else ''}]"
                if removed_tags
                else ""
            )
            tags_message = " ".join([new_tags_message, removed_tags_message]).strip()
            comment_text = f"{comment_text} {tags_message}".strip()

            # create the Comment only if a comment was made or if tags were changed
            if comment_text:
                comment_obj = Comment(
                    author=request.user, comment=comment_text, content_object=source_obj,
                )
                comment_obj.save()
                source_obj.tags.set_tag_list(tag_set)
                source_obj.save()

    tag_comment_form = TagWithCommentsForm(
        initial={"tags": source_obj.tags.get_tag_string()}
    )
    comment_target_type = ContentType.objects.get_for_model(source_obj)
    comments = Comment.objects.filter(
        content_type__pk=comment_target_type.id, object_id=source_obj.id,
    ).order_by("datetime")

    context["comment_form"] = tag_comment_form
    context["comments"] = comments

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
        # add home directory user data for user and jupyter-user (user = github name)
        req_user = request.user.username
        for user in [f'~{req_user}', f'~jupyter-{req_user}']:
            user_home_data = os.path.join(os.path.expanduser(user), settings.HOME_DATA_DIR)
            if settings.HOME_DATA_DIR and os.path.exists(user_home_data):
                img_regex_list.append(os.path.join(user_home_data, '**' + os.sep + '*.fits'))
                selavy_regex_list.append(os.path.join(user_home_data, '**' + os.sep + '*.txt'))

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

    @rest_framework.decorators.action(detail=True, methods=['get'])
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
            pipeline.validate_cfg(user=request.user)
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

    @rest_framework.decorators.action(detail=True, methods=['post'])
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
                messages.success(request, 'Added to favourites successfully')
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
                    'Favourite source deleted successfully.'
                )
                return Response({'message': 'ok'}, status=status.HTTP_200_OK)
            else:
                messages.error(request, 'Not found')
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

    @rest_framework.decorators.action(methods=['get'], detail=False)
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

    @rest_framework.decorators.action(methods=['get'], detail=False)
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

    @rest_framework.decorators.action(methods=["get"], detail=False)
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


class SourcePlotsSet(ViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    @rest_framework.decorators.action(methods=['get'], detail=True)
    def lightcurve(self, request: Request, pk: int = None) -> Response:
        """Create lightcurve and 2-epoch metric graph plots for a source.

        Args:
            request (Request): Django REST Framework request object.
            pk (int, optional): Source object primary key. Defaults to None.

        Raises:
            Http404: if a Source with the given `pk` cannot be found.

        Returns:
            Response: Django REST Framework response object containing the Bokeh plot in
                JSON format to be embedded in the HTML template.
        """
        try:
            source = Source.objects.get(pk=pk)
        except Source.DoesNotExist:
            raise Http404
        # TODO raster plots version for Slack posts
        use_peak_flux = request.query_params.get("peak_flux", "true").lower() == "true"
        plot_document = plot_lightcurve(source, use_peak_flux=use_peak_flux)
        return Response(json_item(plot_document))
