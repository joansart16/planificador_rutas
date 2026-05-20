from django.contrib import admin
from django.urls import path, include
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from rutas import views as rutas_views
from rutas.sites import obra_admin, evento_admin


@login_required
def _admin_password_change(request):
    if not request.user.is_superuser:
        messages.error(request, 'Solo los superusuarios pueden cambiar la contraseña.')
        return HttpResponseRedirect('/')
    return admin.site.password_change(request)


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', rutas_views.home, name='home'),
    # Módulos: cada uno tiene su propio admin montado en su URL
    path('obra/', obra_admin.urls),
    path('evento/', evento_admin.urls),
    # /admin/ se mantiene solo para login/logout y acceso de superusuario
    path('admin/password_change/', _admin_password_change),
    path('admin/', admin.site.urls),
]
