from django.apps import AppConfig


class ArtifactsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artifacts'

    def ready(self):
        """
        Import signal handlers when the app is ready.

        This ensures signal handlers in artifacts/signals.py are registered
        with Django's signal dispatcher.

        Related: ft-025, ADR-030
        """
        import artifacts.signals  # noqa: F401 (imported for side effects)