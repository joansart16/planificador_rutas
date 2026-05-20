from django.apps import AppConfig


class RutasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rutas'
    verbose_name = 'Planificador de Rutas'

    def ready(self) -> None:
        import rutas.signals  # noqa: F401 — conecta los receptores post_save
        self._register_module_sites()

    @staticmethod
    def _register_module_sites() -> None:
        from django.contrib import admin as default_admin
        from rutas.sites import obra_admin, evento_admin

        for model, model_admin in list(default_admin.site._registry.items()):
            admin_class = type(model_admin)
            for site in (obra_admin, evento_admin):
                if model not in site._registry:
                    site.register(model, admin_class)
