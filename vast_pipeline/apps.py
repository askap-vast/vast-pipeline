from django.apps import AppConfig


class PipelineConfig(AppConfig):
    """Class representing the configuration for the vast_pipeline app."""
    name = 'vast_pipeline'

    def ready(self) -> None:
        """Initialization tasks performed as soon as the app registry is populated.
        See <https://docs.djangoproject.com/en/3.1/ref/applications/#django.apps.AppConfig.ready>.
        """
        # import the signals to register them with the application
        import vast_pipeline.signals  # noqa: F401
