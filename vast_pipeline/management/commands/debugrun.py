from django.core.management.base import BaseCommand, CommandError

from vast_pipeline.models import (
    Run, Measurement, Image, Source, Association
)
from ..helpers import get_p_run_name


class Command(BaseCommand):
    """
    This script is used to debug data on specific pipeline run(s) or all.
    Use --help for usage.
    """

    help = (
        'Print out total metrics such as nr of measurements for runs'
    )

    def add_arguments(self, parser):
        # positional arguments (required)
        parser.add_argument(
            'piperuns',
            nargs='+',
            type=str,
            help=(
                'Name or path of pipeline run(s) to debug.Pass "all" to'
                ' print summary data of all the runs.'
            )
        )

    def handle(self, *args, **options):
        piperuns = options['piperuns']
        flag_all_runs = True if 'all' in piperuns else False
        if flag_all_runs:
            piperuns = list(Run.objects.values_list('name', flat=True))

        print(' '.join(40 * ['*']))
        for piperun in piperuns:
            p_run_name = get_p_run_name(piperun)
            try:
                p_run = Run.objects.get(name=p_run_name)
            except Run.DoesNotExist:
                raise CommandError(f'Pipeline run {p_run_name} does not exist')

            print(
                f'Printing summary data of pipeline run "{p_run.name}"'
            )
            images = list(p_run.image_set.values_list('name', flat=True))
            print(f'Nr of images: {len(images)}', )
            print(
                'Nr of measurements:',
                Measurement.objects.filter(image__name__in=images).count()
            )
            print(
                'Nr of forced measurements:',
                (
                    Measurement.objects.filter(
                        image__name__in=images,
                        forced=True
                    )
                    .count()
                )
            )
            sources = (
                Source.objects.filter(run__name=p_run.name)
                .values_list('id', flat=True)
            )
            print('Nr of sources:',len(sources))
            print(
                'Nr of association:',
                Association.objects.filter(source_id__in=sources).count()
                )
            print(' '.join(40 * ['*']))
