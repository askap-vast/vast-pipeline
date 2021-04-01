"""
Defines errors for the pipeline to return.
"""

class PipelineError(Exception):
    """
    Generic pipeline error

    Attributes:
        msg (str): The full error string to return.
    """

    def __init__(self, msg: str=None) -> None:
        """
        Initialises the error.

        Args:
            msg: The error message returned by the pipeline.
        """
        self.msg = (
            'Pipeline error: {0}.'.format(msg) if msg else
            'Undefined Pipeline error.'
        )

    def __str__(self) -> str:
        """
        Returns the string representation.

        Returns:
            The string representation of the error.
        """
        return self.msg


class MaxPipelineRunsError(PipelineError):
    """
    Error for reporting the number of concurrent jobs is maxed out.
    """

    def __str__(self) -> str:
        """
        Returns the string representation.

        Returns:
            The string representation of the error.
        """
        return 'Max pipeline concurrent runs reached!'


class PipelineConfigError(PipelineError):
    """
    Error for issue in the pipeline configuration
    """
    def __init__(self, msg=None):
        """
        Initialises the config error.

        Args:
            msg: The error message returned by the pipeline.
        """
        super(PipelineConfigError, self).__init__(msg)


class PipelineInitError(PipelineError):
    """
    Error for issue in the pipeline initialisation
    """
    def __init__(self, msg=None):
        """
        Initialises the init error.

        Args:
            msg: The error message returned by the pipeline.
        """
        super(PipelineInitError, self).__init__(msg)
