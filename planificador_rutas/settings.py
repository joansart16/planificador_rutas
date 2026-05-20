"""
Django settings for planificador_rutas project.

Las variables sensibles se leen desde el archivo .env (nunca subir a git).
"""

from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga el .env que está en la raíz del proyecto (junto a manage.py)
load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# SEGURIDAD
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fallback-solo-dev')
DEBUG       = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = (
    os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if os.environ.get('DJANGO_ALLOWED_HOSTS')
    else (['*'] if DEBUG else ['localhost', '127.0.0.1'])
)

# Requerido por Django 4+ cuando hay peticiones HTTPS desde un proxy inverso
CSRF_TRUSTED_ORIGINS = [
    f"https://{h.strip()}"
    for h in ALLOWED_HOSTS
    if h.strip() and h.strip() not in ('*', 'localhost', '127.0.0.1')
]

# Nginx pasa la cabecera X-Forwarded-Proto; Django la respeta en producción
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# APLICACIONES
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rutas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    *([] if DEBUG else ['whitenoise.middleware.WhiteNoiseMiddleware']),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'rutas.middleware.ModuleSessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'planificador_rutas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,               # busca templates en <app>/templates/
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'planificador_rutas.wsgi.application'

# ---------------------------------------------------------------------------
# BASE DE DATOS — PostgreSQL (loorent_planificador)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME',     'loorent_planificador'),
        'USER':     os.environ.get('DB_USER',     'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST':     os.environ.get('DB_HOST',     'localhost'),
        'PORT':     os.environ.get('DB_PORT',     '5432'),
        'OPTIONS': {
            'client_encoding': 'UTF8',
        },
    }
}

# ---------------------------------------------------------------------------
# CONTRASEÑAS
# ---------------------------------------------------------------------------
LOGIN_URL = '/admin/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# INTERNACIONALIZACIÓN
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('es', 'Español'),
    ('ca', 'Català'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ---------------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS
# ---------------------------------------------------------------------------
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # destino de collectstatic

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# GOOGLE MAPS
# ---------------------------------------------------------------------------
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# ---------------------------------------------------------------------------
# SEDE / DEPOT — Punto de inicio y fin de todas las rutas
# Sobreescribible via .env: DEPOT_LAT / DEPOT_LNG
# ---------------------------------------------------------------------------
DEPOT_COORDS = {
    'lat': float(os.environ.get('DEPOT_LAT', '39.679469')),
    'lng': float(os.environ.get('DEPOT_LNG', '2.834119')),
    'name': os.environ.get('DEPOT_NAME', 'LooRent — Sede'),
}
