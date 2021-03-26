import os
import logging
import shutil
import numpy as np
import pandas as pd

from glob import glob
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from typing import Dict

from vast_pipeline.models import (
    Run, Source, Measurement, Image, Association, MeasurementPair
)
from vast_pipeline.pipeline.loading import update_sources
from vast_pipeline.pipeline.main import Pipeline
from ..helpers import get_p_run_name


logger = logging.getLogger(__name__)


def yesno(question: str) -> bool:
    """
    Simple Yes/No Function.

    Parameters
    ----------
    question : str
        The question to show to the user for a y/n response.

    Returns
    -------
    bool : bool
        True if user enters 'y', False if 'n'.
    """
    prompt = f'{question} ? (y/n): '
    ans = input(prompt).strip().lower()
    if ans not in ['y', 'n']:
        print(f'{ans} is invalid, please try again...')
        return yesno(question)
    if ans == 'y':
        return True
    return False


def restore_pipe(p_run: Run, bak_files: Dict[str, str], prev_config) -> None:
    """
    Restores the pipeline to the backup files version.
    TODO: Update prev_config type hint.

    Parameters
    ----------
    p_run : Run
        The run model object.
    bak_files : Dict[str, str]
        Dictionary containing the paths to the .bak files.
    prev_config : config
        Module object that represents the back up run configuration.

    Returns
    -------
    None
    """
    # check images match
    img_f_list = getattr(prev_config, 'IMAGE_FILES')
    if isinstance(img_f_list, dict):
        img_f_list = [
            item for sublist in img_f_list.values() for item in sublist
        ]
    img_f_list = [os.path.basename(i) for i in img_f_list]

    prev_images = pd.read_parquet(
        bak_files['images'], columns=['id', 'name', 'measurements_path']
    )

    if sorted(prev_images['name'].tolist()) != sorted(img_f_list):
        raise CommandError(
            'Images in previous config file does not'
            ' match those found in the previous images.parquet.bak.'
            ' Cannot restore pipeline run.'
        )

    # check forced measurements
    monitor = getattr(prev_config, 'MONITOR')
    if monitor:
        forced_parquets = glob(os.path.join(
            p_run.path, 'forced_*.parquet.bak'
        ))

        if not forced_parquets:
            raise CommandError(
                'Monitor is \'True\' in the previous configuration but'
                ' no .bak forced parquet files have been found.'
                ' Cannot restore pipeline run.'
            )
        else:
            # load old associations
            bak_meas_id = pd.read_parquet(
                bak_files['associations'],
                columns = ['meas_id']
            )['meas_id'].unique()

            # load backup forced measurements
            forced_meas = pd.concat(
                [pd.read_parquet(i, columns=['id']) for i in forced_parquets]
            )

            # load image meas
            meas = pd.concat(
                [pd.read_parquet(
                    i, columns=['id']
                ) for i in prev_images['measurements_path']]
            )

            # Get forced ids from the associations
            forced_meas_id = bak_meas_id[
                np.isin(bak_meas_id, meas['id'].to_numpy(), invert=True)
            ]

            if not np.array_equal(
                np.sort(forced_meas_id),
                np.sort(forced_meas['id'].to_numpy())
            ):
                raise CommandError(
                    'The forced measurements .bak files do not match the'
                    ' previous run.'
                    ' Cannot restore pipeline run.'
                )

            del meas

    logger.info("Restoring '%s' from backup parquet files.", p_run.name)

    # Delete any new sources
    bak_sources = pd.read_parquet(bak_files['sources'])

    sources_to_delete = (
        Source.objects
        .filter(run=p_run)
        .exclude(id__in=bak_sources.index.to_numpy())
    )

    if sources_to_delete.exists():
        with transaction.atomic():
            n_del, detail_del = sources_to_delete.delete()
            logger.info(
                ('Deleting new sources and associated objects to restore run'
                 ' Total objects deleted: %i'),
                n_del,
            )
            logger.debug('(type, #deleted): %s', detail_del)

    if monitor:
        current_forced_parquets = glob(os.path.join(
            p_run.path, 'forced_*.parquet'
        ))

        current_forced_meas = pd.concat(
            [pd.read_parquet(
                i, columns=['id']
            ) for i in current_forced_parquets]
        )

        ids_to_delete = current_forced_meas.loc[
            ~current_forced_meas['id'].isin(forced_meas['id'].to_numpy()),
            'id'
        ]

        meas_to_delete = Measurement.objects.filter(id__in=ids_to_delete)

        del ids_to_delete

        if meas_to_delete.exists():
            with transaction.atomic():
                n_del, detail_del = meas_to_delete.delete()
                logger.info(
                    ('Deleting forced measurement and associated'
                     ' objects to restore run. Total objects deleted: %i'),
                    n_del,
                )
                logger.debug('(type, #deleted): %s', detail_del)

    # restore source metrics
    logger.info(f'Restoring metrics for {bak_sources.shape[0]} sources.')
    bak_sources = update_sources(bak_sources)

    # remove images from run
    images_to_remove = (
        Image.objects
        .filter(run=p_run)
        .exclude(id__in=prev_images['id'].to_numpy())
    )
    logger.info(f'Removing {len(images_to_remove)} images from the run.')
    if images_to_remove.exists():
        with transaction.atomic():
            p_run.image_set.remove(*images_to_remove)

    # load image meas
    meas = pd.concat(
        [pd.read_parquet(
            i, columns=['id']
        ) for i in prev_images['measurements_path']]
    )

    association_criteria_1 = Q(source_id__in=bak_sources['id'].to_numpy())
    association_criteria_2 = ~Q(meas_id__in=meas['id'].to_numpy())
    associations_to_delete = Association.objects.filter(
        association_criteria_1 and association_criteria_2
    )

    if associations_to_delete.exists():
        with transaction.atomic():
            n_del, detail_del = associations_to_delete.delete()
            logger.info(
                ('Deleting associations to restore run.'
                 ' Total objects deleted: %i'),
                n_del,
            )
            logger.debug('(type, #deleted): %s', detail_del)

    pair_criteria_1 = Q(source_id__in=bak_sources['id'].to_numpy())
    pair_criteria_2 = ~Q(measurement_a__in=meas['id'].to_numpy())
    pair_criteria_3 = ~Q(measurement_b__in=meas['id'].to_numpy())

    pairs_to_delete = MeasurementPair.objects.filter(
       pair_criteria_1 and (pair_criteria_2 | pair_criteria_3)
    )

    if pairs_to_delete.exists():
        with transaction.atomic():
            n_del, detail_del = pairs_to_delete.delete()
            logger.info(
                ('Deleting measurement pairs to restore run.'
                 ' Total objects deleted: %i'),
                n_del,
            )
            logger.debug('(type, #deleted): %s', detail_del)

    logger.info(f'Restoring run metrics.')
    p_run.n_images = prev_images.shape[0]
    p_run.n_sources = bak_sources.shape[0]
    p_run.n_selavy_measurements = meas.shape[0]
    if monitor:
        p_run.n_forced_measurements = forced_meas.shape[0]

    with transaction.atomic():
        p_run.save()

    # switch files and delete backups
    logger.info(f'Restoring parquet files and removing .bak files.')
    for i in bak_files:
        bak_file = bak_files[i]
        if i == 'config':
            actual_file = bak_file.replace('.py.bak', '_prev.py')
        else:
            actual_file = bak_file.replace('.bak', '')
        shutil.copy(bak_file, actual_file)
        os.remove(bak_file)

    if monitor:
        for i in current_forced_parquets:
            os.remove(i)

        for i in forced_parquets:
            new_file = i.replace('.bak', '')
            shutil.copy(i, new_file)
            os.remove(i)


class Command(BaseCommand):
    """
    This script is used to restore a pipeline run to the previous verion after
    add mode has been used.
    Use --help for usage.
    """

    help = (
        'Restore a pipeline run to the previous person after image add mode'
        ' has been used.'
    )

    def add_arguments(self, parser):
        # positional arguments (required)
        parser.add_argument(
            'piperuns',
            nargs='+',
            type=str,
            default=None,
            help='Name or path of pipeline run(s) to restore.'
        )
        # keyword arguments (optional)
        parser.add_argument(
            '--no-confirm',
            required=False,
            default=False,
            action='store_true',
            help=(
                'Flag to skip the confirmation stage and proceed to restore'
                ' the pipeline run.'
            )
        )

    def handle(self, *args, **options):
        # configure logging
        if options['verbosity'] > 1:
            # set root logger to use the DEBUG level
            root_logger = logging.getLogger('')
            root_logger.setLevel(logging.DEBUG)
            # set the traceback on
            options['traceback'] = True

        piperuns = options['piperuns']

        for piperun in piperuns:
            p_run_name = get_p_run_name(piperun)
            try:
                p_run = Run.objects.get(name=p_run_name)
            except Run.DoesNotExist:
                raise CommandError(f'Pipeline run {p_run_name} does not exist')

            if p_run.status not in ['END', 'ERR']:
                raise CommandError(
                    f"Run {p_run_name} does not have an 'END' or 'ERR' status."
                    " Unable to run restore."
                )

            path = p_run.path
            pipeline = Pipeline(
                name=p_run_name,
                config_path=os.path.join(path, 'config.py')
            )
            try:
                # update pipeline run status to restoring
                prev_status = p_run.status
                pipeline.set_status('RES')

                prev_config_file = os.path.join(p_run.path, 'config.py.bak')

                if os.path.isfile(prev_config_file):
                    shutil.copy(
                        prev_config_file,
                        prev_config_file.replace('.py.bak', '.bak.py')
                    )
                    prev_config_file = prev_config_file.replace(
                        '.py.bak', '.bak.py'
                    )
                    prev_config = Pipeline.load_cfg(prev_config_file)
                    os.remove(prev_config_file)
                else:
                    raise CommandError(
                        f'Previous config file does not exist.'
                        ' Cannot restore pipeline run.'
                    )

                bak_files = {}
                for i in [
                    'associations', 'bands', 'images', 'measurement_pairs',
                    'relations', 'skyregions', 'sources', 'config'
                ]:
                    if i == 'config':
                        f_name = os.path.join(p_run.path, f'{i}.py.bak')
                    else:
                        f_name = os.path.join(p_run.path, f'{i}.parquet.bak')

                    if os.path.isfile(f_name):
                        bak_files[i] = f_name
                    else:
                        raise CommandError(
                            f'File {f_name} does not exist.'
                            ' Cannot restore pipeline run.'
                        )

                logger_msg = "Will restore the run to the following config:"

                keys = settings.PIPE_RUN_CONFIG_DEFAULTS.keys()

                for i in keys:
                    setting_val = getattr(prev_config, i.upper())
                    logger_msg += f"\n{i.upper():.<50s}{setting_val}"

                logger.info(logger_msg)

                user_continue = True if options['no_confirm'] else yesno("Would you like to restore the run")

                if user_continue:
                    restore_pipe(p_run, bak_files, prev_config)
                    pipeline.set_status('END')
                    logger.info('Restore complete.')
                else:
                    pipeline.set_status(prev_status)
                    logger.info('No actions performed.')

            except Exception as e:
                logger.error('Restoring failed!')
                logger.error(e)
                pipeline.set_status('ERR')