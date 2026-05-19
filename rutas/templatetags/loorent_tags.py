import os
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def app_version():
    try:
        with open(os.path.join(settings.BASE_DIR, 'VERSION')) as f:
            return f.read().strip()
    except Exception:
        return '?'
