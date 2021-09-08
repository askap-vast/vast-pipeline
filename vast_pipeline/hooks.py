"""
This module contains hooks that can be accessed by DjangoQ async_tasks, which
are mainly used in 'views'.
"""

from django.db import transaction
from django_q.tasks import async_task, Task


def run_restore(task: Task) -> None:
    """
    Runs the second part of the restore run method after the successful
    completion of the first.

    Args:
        task: The DjangoQ Task object from the async_task run that uses
            the hook.

    Returns:
        None
    """
    if task.success:
        p_run = task.args[0]
        cli = task.kwargs.get('cli')
        debug_flag = task.kwargs.get('debug')
        result_prev_config, result_bak_files = task.result
        try:
            async_task(
                'vast_pipeline.management.commands.restorepiperun.restore_pipe',
                p_run,
                result_bak_files,
                result_prev_config,
                cli=cli,
                debug=debug_flag,
                hook='vast_pipeline.hooks.set_end_status',
            )
        except Exception as e:
            with transaction.atomic():
                p_run.status = 'ERR'
                p_run.save()


def set_end_status(task: Task) -> None:
    """
    Runs the final part of the restore run method after the successful
    completion of the second.

    Sets the run status to 'END'.

    Args:
        task: The DjangoQ Task object from the async_task run that uses
            the hook.

    Returns:
        None
    """
    if task.success:
        p_run = task.args[0]
        with transaction.atomic():
            p_run.status = 'END'
            p_run.save()
