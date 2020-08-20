class PipelineError(Exception):
    """
    Generic pipeline error
    """

    def __init__(self, msg=None):
        self.msg = (
            'Pipeline error: {0}.'.format(msg) if msg else
            'Undefined Pipeline error.'
        )

    def __str__(self):
        return self.msg


class MaxPipelineRunsError(PipelineError):
    """
    Error for reporting the number of concurrent jobs is maxed out
    """

    def __str__(self):
        return 'Max pipeline concurrent runs reached!'


class PipelineConfigError(PipelineError):
    """
    Error for issue in the pipeline configuration
    """
    def __init__(self, msg=None):
        super(PipelineConfigError, self).__init__(msg)


class PipelineInitError(PipelineError):
    """
    Error for issue in the pipeline initialisation
    """
    def __init__(self, msg=None):
        super(PipelineInitError, self).__init__(msg)
