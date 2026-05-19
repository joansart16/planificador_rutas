from django.contrib import admin
from django.urls import path, include
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from rutas import views as rutas_views


@login_required
def _admin_password_change(request):
    if not request.user.is_superuser:
        messages.error(request, 'Solo los superusuarios pueden cambiar la contraseña.')
        return HttpResponseRedirect('/admin/')
    return admin.site.password_change(request)


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', rutas_views.home, name='home'),
    path('modulo/<str:module>/', rutas_views.set_module, name='set_module'),
    # Bloquear cambio de contraseña a no-superusuarios (debe ir antes de admin/)
    path('admin/password_change/', _admin_password_change),
    path('admin/', admin.site.urls),
]
