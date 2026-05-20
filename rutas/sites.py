from django.contrib.admin import AdminSite


class LoorentAdminSite(AdminSite):
    pass


obra_admin = LoorentAdminSite(name='obra')
obra_admin.site_header = 'Loorent · Obras'
obra_admin.site_title = 'Obras'
obra_admin.index_title = 'Módulo Obra'

evento_admin = LoorentAdminSite(name='evento')
evento_admin.site_header = 'Loorent · Eventos'
evento_admin.site_title = 'Eventos'
evento_admin.index_title = 'Módulo Evento'
