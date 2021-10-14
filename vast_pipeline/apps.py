from django.apps import AppConfig


class PipelineConfig(AppConfig):
    """Class representing the configuration for the vast_pipeline app."""
    name = 'vast_pipeline'

    def ready(self):
        # import the signals to register them with the application
        import vast_pipeline.signals  # noqa: F401
