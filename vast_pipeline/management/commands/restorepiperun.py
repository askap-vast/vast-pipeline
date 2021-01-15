import os
import logging
import shutil

from glob import glob
from django.core.management.base import BaseCommand, CommandError

from vast_pipeline.models import Run
from ..helpers import get_p_run_name


logger = logging.getLogger(__name__)


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
        flag_all_runs = True if 'clearall' in piperuns else False
        if flag_all_runs:
            logger.info('clearing all pipeline run in the database')
            piperuns = list(Run.objects.values_list('name', flat=True))

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

            # check images match
            img_f_list = getattr(prev_config, 'IMAGE_FILES')
            img_f_list = [
                item for sublist in img_f_list.values() for item in sublist
            ]
            prev_images = pd.read_parquet(bak_files['images'])

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
                    )


            logger.info("Restoring '%s' from backup parquet files.", p_run_name)
            p_run.delete()

            # Delete parquet or folder eventually
            if not options['keep_parquet'] and not options['remove_all']:
                logger.info('Deleting pipeline "%s" parquets', p_run_name)
                parquets = (
                    glob(os.path.join(p_run.path, '*.parquet'))
                    + glob(os.path.join(p_run.path, '*.arrow'))
                )
                for parquet in parquets:
                    try:
                        os.remove(parquet)
                    except OSError as e:
                        self.stdout.write(self.style.WARNING(
                            f'Parquet file "{os.path.basename(parquet)}" not existent'
                        ))
                        pass

            if options['remove_all']:
                logger.info('Deleting pipeline folder')
                try:
                    shutil.rmtree(p_run.path)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'Issues in removing run folder: {e}'
                    ))
                    pass

