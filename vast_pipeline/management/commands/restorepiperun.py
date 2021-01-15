import os
import logging
import shutil

from glob import glob
from django.core.management.base import BaseCommand, CommandError

from vast_pipeline.models import Run
from vast_pipeline.pipeline.main import Pipeline
from ..helpers import get_p_run_name


logger = logging.getLogger(__name__)


def yesno(question):
    """Simple Yes/No Function."""
    prompt = f'{question} ? (y/n): '
    ans = input(prompt).strip().lower()
    if ans not in ['y', 'n']:
        print(f'{ans} is invalid, please try again...')
        return yesno(question)
    if ans == 'y':
        return True
    return False


def restore_pipe(p_run, bak_files, prev_config):
    # check images match
    img_f_list = getattr(prev_config, 'IMAGE_FILES')
    img_f_list = [
        item for sublist in img_f_list.values() for item in sublist
    ]
    prev_images = pd.read_parquet(
        bak_files['images'], columns=['id', 'measurements_path']
    )

    if prev_images.shape[0] != len(img_f_list):
        raise CommandError(
            'Number of images in previous config file does not'
            ' match the number found in previous images.parquet.bak.'
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
            ).unique()

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
            forced_meas_id = bak_meas_id.isin(
                meas['id'].to_numpy(), invert=True
            )

            if np.sort(forced_meas_id) != np.sort(forced_meas['id'].to_numpy()):
                raise CommandError(
                    'The forced measurements .bak files do not match the'
                    ' previous run.'
                    ' Cannot restore pipeline run.'
                )

            del meas

    logger.info("Restoring '%s' from backup parquet files.", p_run_name)

    # Delete any new sources
    bak_source_ids = pd.read_parquet(bak_files['sources'], columns=['id'])


    sources_to_delete = (
        Source.objects
        .filter(run=p_run)
        .exclude(id__in=bak_source_ids['id'].to_numpy())
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
            ~current_forced_meas.isin(forced_meas['id'].to_numpy()),
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

            prev_config = os.path.join(p_run.path, 'config_prev.py')

            if os.path.isfile(prev_config):
                prev_config = p_run.load_cfg(prev_config)
            else:
                raise CommandError(
                    f'Previous config file does not exist.'
                    ' Cannot restore pipeline run.'
                )

            bak_files = {}
            for i in [
                'associations', 'bands.parquet', 'images', 'measurement_pairs',
                'relations', 'skyregions', 'sources'
            ]:
                parquet = os.path.join(p_run.path, f'{i}.parquet')

                if os.path.isfile(parquet):
                    bak_files[i] = parquet
                else:
                    raise CommandError(
                        f'File {i}.parquet does not exist.'
                        ' Cannot restore pipeline run.'
                    )


            user_continue = yesno("Would you like to restore the run?")

            if user_continue:
                restore_pipe(p_run, bak_files, prev_config)
