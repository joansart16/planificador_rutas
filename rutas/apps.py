from django.apps import AppConfig


class RutasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rutas'
    verbose_name = 'Planificador de Rutas'

    def ready(self) -> None:
        import rutas.signals  # noqa: F401 — conecta los receptores post_save
