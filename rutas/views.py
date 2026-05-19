from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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


def home(request):
    return redirect('/admin/')


@login_required
def set_module(request, module: str):
    allowed = _user_modules(request.user)
    if module in [m.value for m in allowed]:
        request.session['current_module'] = module
    return redirect('admin:index')
