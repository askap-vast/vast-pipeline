class MaxPipelineRunsError(Exception):
    """
    Error for reporting the number of concurrent jobs is maxed out
    """

    def __str__(self):
        return 'Max pipeline concurrent runs reached!'


class PipelineError(Exception):
    """
    Generic pipeline error
    """

    def __init__(self, *args):
        if args:
            self.msg = args[0]
        else:
            self.msg = None

    def __str__(self):
        if self.msg:
            return 'Generic Pipeline error: {0}.'.format(self.msg)
        else:
            return 'Generic Pipeline error.'

