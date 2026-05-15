from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

from rutas import views as rutas_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', rutas_views.home, name='home'),
    path('modulo/<str:module>/', rutas_views.set_module, name='set_module'),
    path('admin/', admin.site.urls),
]
