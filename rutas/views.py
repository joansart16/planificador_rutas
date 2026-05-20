from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Contract


OBRA_GROUP = 'operadores_obra'


def _user_modules(user):
    """Returns the list of modules the user may access."""
    if user.is_superuser or user.groups.filter(name='operadores_evento').exists():
        if user.is_superuser or user.groups.filter(name='operadores_obra').exists():
            return [Contract.Module.OBRA, Contract.Module.EVENTO]
    if user.groups.filter(name=OBRA_GROUP).exists():
        return [Contract.Module.OBRA]
    if user.is_superuser:
        return [Contract.Module.OBRA, Contract.Module.EVENTO]
    return [Contract.Module.OBRA]


@login_required(login_url='/admin/login/')
def home(request):
    modules = _user_modules(request.user)
    current_module = request.session.get('current_module', modules[0].value if modules else '')
    return render(request, 'home.html', {
        'modules': modules,
        'current_module': current_module,
    })
