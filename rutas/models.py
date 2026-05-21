import unicodedata

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class Driver(models.Model):
    """Conductor con calendario laboral e indisponibilidades."""

    name   = models.CharField(max_length=150, verbose_name=_('Nombre'))
    working_days = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Días de trabajo'),
        help_text=_('Selecciona de lunes a domingo. Array de 0-6 representando lunes a domingo.'),
    )

    class Weekday(models.IntegerChoices):
        MONDAY    = 0, _('Lunes')
        TUESDAY   = 1, _('Martes')
        WEDNESDAY = 2, _('Miércoles')
        THURSDAY  = 3, _('Jueves')
        FRIDAY    = 4, _('Viernes')
        SATURDAY  = 5, _('Sábado')
        SUNDAY    = 6, _('Domingo')

    class Meta:
        verbose_name        = _('Conductor')
        verbose_name_plural = _('Conductores')
        ordering            = ['name']

    def __str__(self) -> str:
        return self.name

    def is_working_day(self, day: int) -> bool:
        """True si el conductor trabaja en el día de semana indicado (0=lunes ... 6=domingo)."""
        return int(day) in (self.working_days or [])

    def get_active_unavailability(self, target_date):
        """Devuelve la indisponibilidad activa para la fecha, o None si no existe."""
        return self.unavailabilities.filter(start_date__lte=target_date, end_date__gte=target_date).first()

    def is_available_on(self, target_date) -> bool:
        """Disponibilidad dinámica: día laboral y sin período de indisponibilidad activo."""
        if not target_date:
            return True
        if not self.is_working_day(target_date.weekday()):
            return False
        return self.get_active_unavailability(target_date) is None


class DriverUnavailability(models.Model):
    """Períodos en los que un conductor no está disponible (vacaciones, baja, etc.)."""

    class Reason(models.TextChoices):
        VACATION   = 'VACATION',   _('Vacaciones')
        SICK_LEAVE = 'SICK_LEAVE', _('Baja médica')
        PERSONAL   = 'PERSONAL',   _('Asunto personal')
        OTHER      = 'OTHER',      _('Otro motivo')

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='unavailabilities',
        verbose_name=_('Conductor'),
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        verbose_name=_('Motivo'),
    )
    start_date = models.DateField(verbose_name=_('Fecha de inicio'))
    end_date = models.DateField(
        verbose_name=_('Fecha de fin'),
        help_text=_('Si es un solo día, pon la misma fecha que inicio.'),
    )
    notes = models.TextField(
        blank=True, default='',
        verbose_name=_('Notas'),
    )

    class Meta:
        verbose_name        = _('Indisponibilidad del conductor')
        verbose_name_plural = _('Indisponibilidades del conductor')
        ordering            = ['-start_date']

    def __str__(self) -> str:
        return f"{self.driver.name} · {self.get_reason_display()} ({self.start_date} → {self.end_date})"

    def clean(self) -> None:
        errors = {}
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors['end_date'] = 'La fecha de fin no puede ser anterior a la fecha de inicio.'
        if errors:
            raise ValidationError(errors)


class Vehicle(models.Model):
    """Vehículo. Solo los AVAILABLE pueden ser asignados a tareas."""

    class Size(models.IntegerChoices):
        PICKUP = 1, _('Pickup')
        SMALL  = 2, _('Camión pequeño')
        LARGE  = 3, _('Camión grande')

    class Status(models.TextChoices):
        AVAILABLE   = 'AVAILABLE',   _('Disponible')
        MAINTENANCE = 'MAINTENANCE', _('En mantenimiento')
        RETIRED     = 'RETIRED',     _('Retirado')

    name = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name=_('Nombre del vehículo'),
        help_text=_('Alias interno del vehículo (ej: Pickup 1, Camión Norte).'),
    )
    license_plate = models.CharField(
        max_length=20, unique=True, verbose_name=_('Matrícula')
    )
    size = models.IntegerField(
        choices=Size.choices, verbose_name=_('Tamaño')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        verbose_name=_('Estado'),
    )

    class Meta:
        verbose_name        = _('Vehículo')
        verbose_name_plural = _('Vehículos')
        ordering            = ['license_plate']

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} · {self.license_plate}"
        return f"{self.license_plate} · {self.get_size_display()}"


class Company(models.Model):
    """Empresa o cliente. Agrupa ubicaciones bajo un mismo titular."""

    name  = models.CharField(max_length=200, unique=True, verbose_name=_('Razón social'))
    email = models.EmailField(
        verbose_name=_('Correo electrónico'),
        help_text=_('Obligatorio. Se usa como fallback en el exportador cuando la ubicación no tiene email propio.'),
    )

    class Meta:
        verbose_name        = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering            = ['name']

    def __str__(self) -> str:
        return self.name


class Location(models.Model):
    """
    Ubicación (obra, evento o punto de servicio).

    Atributos geográficos y empresariales que permiten filtrar y buscar
    rápidamente en el desplegable del admin (autocomplete).
    """

    class Zone(models.TextChoices):
        PALMA      = 'PALMA',      _('Palma')
        TRAMUNTANA = 'TRAMUNTANA', _('Serra de Tramuntana')
        RAIGUER    = 'RAIGUER',    _('Raiguer (Inca / Binissalem)')
        PLA        = 'PLA',        _('Pla de Mallorca')
        MIGJORN    = 'MIGJORN',    _('Migjorn (Llucmajor / Campos)')
        LLEVANT    = 'LLEVANT',    _('Llevant (Manacor / Artà)')

    # Mapa normalizado municipio → zona (catalán + castellano)
    _TOWN_ZONE_MAP: dict[str, str] = {
        # ── Palma ──────────────────────────────────────────────────────
        'palma': 'PALMA', 'palma de mallorca': 'PALMA',
        # ── Serra de Tramuntana ────────────────────────────────────────
        'andratx': 'TRAMUNTANA', 'andrach': 'TRAMUNTANA',
        'banyalbufar': 'TRAMUNTANA', 'bañalbufar': 'TRAMUNTANA',
        'bunyola': 'TRAMUNTANA', 'buñola': 'TRAMUNTANA',
        'calvia': 'TRAMUNTANA',
        'deia': 'TRAMUNTANA', 'deya': 'TRAMUNTANA',
        'escorca': 'TRAMUNTANA',
        'esporles': 'TRAMUNTANA', 'esporlas': 'TRAMUNTANA',
        'estellencs': 'TRAMUNTANA', 'estellenchs': 'TRAMUNTANA',
        'fornalutx': 'TRAMUNTANA', 'fornaluch': 'TRAMUNTANA',
        'pollenca': 'TRAMUNTANA', 'pollensa': 'TRAMUNTANA',
        'puigpunyent': 'TRAMUNTANA', 'puigpuñent': 'TRAMUNTANA',
        'soller': 'TRAMUNTANA',
        'valldemossa': 'TRAMUNTANA', 'valldemosa': 'TRAMUNTANA',
        # ── Raiguer ────────────────────────────────────────────────────
        'alaro': 'RAIGUER',
        'alcudia': 'RAIGUER',
        'binissalem': 'RAIGUER',
        'buger': 'RAIGUER',
        'campanet': 'RAIGUER',
        'consell': 'RAIGUER',
        'inca': 'RAIGUER',
        'lloseta': 'RAIGUER',
        'mancor de la vall': 'RAIGUER', 'mancor del valle': 'RAIGUER',
        'marratxi': 'RAIGUER', 'marrachi': 'RAIGUER',
        'sa pobla': 'RAIGUER', 'la puebla': 'RAIGUER',
        'santa maria del cami': 'RAIGUER', 'santa maria del camino': 'RAIGUER',
        'selva': 'RAIGUER',
        # ── Pla de Mallorca ────────────────────────────────────────────
        'algaida': 'PLA',
        'ariany': 'PLA',
        'costitx': 'PLA', 'costich': 'PLA',
        'lloret de vistalegre': 'PLA', 'lloret de vista alegre': 'PLA',
        'llubi': 'PLA',
        'maria de la salut': 'PLA', 'maria de la salud': 'PLA',
        'montuiri': 'PLA',
        'muro': 'PLA',
        'petra': 'PLA',
        'porreres': 'PLA', 'porreras': 'PLA',
        'sant joan': 'PLA', 'san juan': 'PLA',
        'santa eugenia': 'PLA',
        'santa margalida': 'PLA', 'santa margarita': 'PLA',
        'sencelles': 'PLA', 'sancellas': 'PLA',
        'sineu': 'PLA',
        'vilafranca de bonany': 'PLA', 'villafranca de bonany': 'PLA',
        # ── Migjorn ────────────────────────────────────────────────────
        'campos': 'MIGJORN',
        'felanitx': 'MIGJORN', 'felanich': 'MIGJORN',
        'llucmajor': 'MIGJORN',
        'ses salines': 'MIGJORN', 'las salinas': 'MIGJORN',
        'santanyi': 'MIGJORN',
        # ── Llevant ────────────────────────────────────────────────────
        'arta': 'LLEVANT',
        'capdepera': 'LLEVANT',
        'manacor': 'LLEVANT',
        'sant llorenc des cardassar': 'LLEVANT', 'san lorenzo del cardezar': 'LLEVANT',
        'son servera': 'LLEVANT',
    }

    _POSTAL_ZONE_MAP: dict[str, str] = {
        # --- PALMA ---
        '07001': 'PALMA', '07002': 'PALMA', '07003': 'PALMA', '07004': 'PALMA', '07005': 'PALMA',
        '07006': 'PALMA', '07007': 'PALMA', '07008': 'PALMA', '07009': 'PALMA', '07010': 'PALMA',
        '07011': 'PALMA', '07012': 'PALMA', '07013': 'PALMA', '07014': 'PALMA', '07015': 'PALMA',
        '07120': 'PALMA', '07198': 'PALMA', '07199': 'PALMA', '07600': 'PALMA', '07610': 'PALMA',

        # --- TRAMUNTANA ---
        '07110': 'TRAMUNTANA',  # Bunyola
        '07193': 'TRAMUNTANA',  # Palmanyola
        '07190': 'TRAMUNTANA',  # Esporles
        '07140': 'TRAMUNTANA',  # Sencelles (al límit amb Pla)
        '07150': 'TRAMUNTANA',  # Andratx
        '07157': 'TRAMUNTANA',  # Port d'Andratx
        '07160': 'TRAMUNTANA',  # Peguera / Calvia
        '07170': 'TRAMUNTANA',  # Soller
        '07180': 'TRAMUNTANA',  # Santa Ponca
        '07181': 'TRAMUNTANA',  # Portals Nous / Palmanova
        '07184': 'TRAMUNTANA',  # Calvia poble
        '07460': 'TRAMUNTANA',  # Pollenca
        '07470': 'TRAMUNTANA',  # Port de Pollenca
        '07340': 'TRAMUNTANA',  # Alaro
        '07100': 'TRAMUNTANA',  # Soller

        # --- RAIGUER ---
        '07300': 'RAIGUER',
        '07310': 'RAIGUER',
        '07320': 'RAIGUER',
        '07330': 'RAIGUER',
        '07350': 'RAIGUER',
        '07360': 'RAIGUER',
        '07141': 'RAIGUER',
        '07420': 'RAIGUER',
        '07430': 'RAIGUER',
        '07510': 'RAIGUER',

        # --- PLA ---
        '07144': 'PLA',
        '07210': 'PLA',
        '07220': 'PLA',
        '07230': 'PLA',
        '07240': 'PLA',
        '07250': 'PLA',
        '07260': 'PLA',
        '07313': 'PLA',
        '07440': 'PLA',
        '07450': 'PLA',
        '07458': 'PLA',

        # --- MIGJORN ---
        '07620': 'MIGJORN',
        '07630': 'MIGJORN',
        '07640': 'MIGJORN',
        '07650': 'MIGJORN',
        '07660': 'MIGJORN',
        '07670': 'MIGJORN',
        '07680': 'MIGJORN',
        '07690': 'MIGJORN',

        # --- LLEVANT ---
        '07500': 'LLEVANT',
        '07550': 'LLEVANT',
        '07560': 'LLEVANT',
        '07570': 'LLEVANT',
        '07580': 'LLEVANT',
        '07590': 'LLEVANT',
    }

    @classmethod
    def get_zone_for_town(cls, town: str) -> str:
        """Devuelve el código de zona para un municipio, o '' si no se reconoce."""
        if not town:
            return ''
        normalized = (
            unicodedata.normalize('NFD', town.lower().strip())
            .encode('ascii', 'ignore')
            .decode()
        )
        return cls._TOWN_ZONE_MAP.get(normalized, '')

    @classmethod
    def normalize_postal_code(cls, postal_code: str) -> str:
        """Normaliza un código postal y extrae los 5 dígitos si existen."""
        if not postal_code:
            return ''
        digits = ''.join(ch for ch in postal_code if ch.isdigit())
        return digits[:5] if len(digits) >= 5 else ''

    @classmethod
    def get_zone_for_postal_code(cls, postal_code: str) -> str:
        """Devuelve el código de zona por código postal, o '' si no se reconoce."""
        normalized = cls.normalize_postal_code(postal_code)
        if not normalized:
            return ''
        return cls._POSTAL_ZONE_MAP.get(normalized, '')

    # ── Identificación ────────────────────────────────────────────────
    name    = models.CharField(max_length=200, verbose_name=_('Nombre del sitio'))
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='locations',
        verbose_name=_('Empresa / Cliente'),
        help_text=_('Empresa titular. Permite filtrar todas sus ubicaciones.'),
    )

    # ── Contacto en obra ─────────────────────────────────────────────
    contact_name  = models.CharField(
        max_length=150, blank=True, default='',
        verbose_name=_('Persona de contacto'),
        help_text=_('Responsable de la obra o punto de servicio.'),
    )
    contact_phone = models.CharField(
        max_length=20, blank=True, default='',
        verbose_name=_('Teléfono de contacto'),
    )
    email = models.EmailField(
        blank=True, default='',
        verbose_name=_('Email contacto obra'),
        help_text=_('Opcional. Si se rellena, se usa en el exportador en lugar del email del cliente.'),
    )
    comment = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Comentario'),
        help_text=_('Indicaciones operativas para el servicio en esta ubicación.'),
    )
    cabin_count = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Número de cabinas'),
        help_text=_('Cantidad de cabinas a limpiar en esta ubicación.'),
    )

    # ── Dirección ─────────────────────────────────────────────────────
    address     = models.TextField(verbose_name=_('Dirección (calle y número)'))
    town        = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name=_('Población'),
        help_text=_('Núcleo habitado (ej: Palmanyola). Se rellena automáticamente.'),
    )
    municipality = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name=_('Municipio'),
        help_text=_('Municipio administrativo (ej: Bunyola). Se usa para calcular la comarca.'),
    )
    postal_code = models.CharField(
        max_length=10, blank=True, default='',
        verbose_name=_('Código postal'),
    )
    zone        = models.CharField(
        max_length=20,
        choices=Zone.choices,
        blank=True, default='',
        verbose_name=_('Zona de Mallorca'),
        help_text=_('Comarca o zona de la isla para agrupar y filtrar rutas.'),
    )

    # ── Coordenadas ───────────────────────────────────────────────────
    coords_cabin = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name=_('Coordenadas cabina'),
        help_text=_('Pega directamente desde Google Maps (ej: 39.619316, 2.643553).'),
    )
    coords_entrance = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name=_('Coordenadas entrada finca'),
        help_text=_('Opcional. Si se rellena, el exportador genera una fila adicional con "Entrada finca".'),
    )

    # ── Restricción de vehículo ───────────────────────────────────────
    max_vehicle_size = models.IntegerField(
        choices=Vehicle.Size.choices,
        verbose_name=_('Tamaño máximo de vehículo'),
        help_text=_('Vehículos con tamaño superior serán rechazados (gálibo).'),
    )
    default_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='default_locations',
        verbose_name=_('Conductor por defecto'),
        help_text=_('Se asignará automáticamente a las tareas de este sitio (puede cambiar después).'),
    )

    class Meta:
        verbose_name        = _('Ubicación')
        verbose_name_plural = _('Ubicaciones')
        ordering            = ['company__name', 'name']

    def __str__(self) -> str:
        parts = [self.name]
        if self.company_id:
            parts.insert(0, self.company.name)
        if self.town:
            parts.append(self.town)
        return ' · '.join(parts)

    def save(self, *args, **kwargs) -> None:
        """
        Auto-detecta la zona con prioridad:
        1) Código postal
        2) Municipio administrativo
        3) Núcleo habitado (población)

        Si se detecta una zona en cualquiera de estos pasos, se sobreescribe
        para garantizar coherencia.
        """
        detected_by_postal = self.get_zone_for_postal_code(self.postal_code)
        if detected_by_postal:
            self.zone = detected_by_postal
            super().save(*args, **kwargs)
            return

        for candidate in [self.municipality, self.town]:
            if candidate:
                detected = self.get_zone_for_town(candidate)
                if detected:
                    self.zone = detected
                    break
        super().save(*args, **kwargs)


class Contract(models.Model):
    """
    Contrato de obra o evento.

    Al crear un contrato se generan automáticamente las ServiceTask
    mediante la señal post_save definida en rutas/signals.py:
      · 1 ENTREGA en start_date
      · N LIMPIEZA cada cleaning_frequency días
      · 1 RECOGIDA en end_date

        Las restricciones de tamaño de vehículo se definen en la Location
        asociada (max_vehicle_size). Para ENTREGA y RECOGIDA se exige LARGE.
    """

    class Module(models.TextChoices):
        OBRA   = 'OBRA',   _('Obra')
        EVENTO = 'EVENTO', _('Evento')

    class Status(models.TextChoices):
        ACTIVE      = 'ACTIVE',       _('Activo')
        INTERRUPTED = 'INTERRUPTED',  _('Interrumpido')
        RETIRED     = 'RETIRED',      _('Retirado')
        CANCELLED   = 'CANCELLED',    _('Cancelado')

    class Weekday(models.IntegerChoices):
        MONDAY    = 0, _('Lunes')
        TUESDAY   = 1, _('Martes')
        WEDNESDAY = 2, _('Miercoles')
        THURSDAY  = 3, _('Jueves')
        FRIDAY    = 4, _('Viernes')
        SATURDAY  = 5, _('Sábado')
        SUNDAY    = 6, _('Domingo')

    module = models.CharField(
        max_length=10,
        choices=Module.choices,
        default=Module.OBRA,
        verbose_name=_('Módulo'),
        help_text=_('Obra o Evento. Determina en qué sección aparece este pedido.'),
    )
    budget_number = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name=_('Nº presupuesto'),
        help_text=_('Número de presupuesto. Clave que identifica esta obra en el sistema.'),
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name=_('Ubicación'),
    )
    start_date         = models.DateField(verbose_name=_('Fecha de inicio'))
    end_date           = models.DateField(
        null=True, blank=True,
        verbose_name=_('Fecha de fin (recogida)'),
        help_text=_('Dejar en blanco si la fecha de recogida no se conoce aún.'),
    )
    cleaning_frequency = models.PositiveIntegerField(
        verbose_name=_('Limpiezas por semana'),
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text=_('Numero de servicios de limpieza semanales (1 a 7).'),
    )
    cleaning_weekdays = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Dias de limpieza'),
        help_text=_('Selecciona de lunes a domingo. Deben coincidir con limpiezas por semana.'),
    )
    access_start_time = models.TimeField(
        null=True, blank=True,
        verbose_name=_('Hora de acceso (inicio)'),
        help_text=_('Hora a partir de la cual se puede acceder al sitio.'),
    )
    access_end_time = models.TimeField(
        null=True, blank=True,
        verbose_name=_('Hora de acceso (fin)'),
        help_text=_('Última hora permitida de acceso al sitio.'),
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Estado'),
    )

    class Meta:
        verbose_name        = _('Pedido')
        verbose_name_plural = _('Pedidos')
        ordering            = ['-start_date']

    def __str__(self) -> str:
        budget = self.budget_number if self.budget_number else f'#{self.pk}'
        location_name = self.location.name if self.location_id else '?'
        return f"{budget} · {location_name}"

    def clean(self) -> None:
        errors = {}

        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors['end_date'] = 'La fecha de fin (recogida) no puede ser anterior a la fecha de inicio.'

        raw_days = self.cleaning_weekdays or []
        if not isinstance(raw_days, list):
            errors['cleaning_weekdays'] = 'El formato de dias de limpieza no es valido.'
        else:
            parsed_days = []
            for day in raw_days:
                try:
                    day_int = int(day)
                except (TypeError, ValueError):
                    errors['cleaning_weekdays'] = 'Cada dia debe ser un numero entre 0 y 6.'
                    parsed_days = []
                    break
                parsed_days.append(day_int)

            if parsed_days:
                if any(day < 0 or day > 6 for day in parsed_days):
                    errors['cleaning_weekdays'] = 'Solo se permiten dias de lunes a domingo.'

                unique_days = sorted(set(parsed_days))
                if len(unique_days) != len(parsed_days):
                    errors['cleaning_weekdays'] = 'No repitas dias de limpieza.'

                if self.cleaning_frequency and len(unique_days) != self.cleaning_frequency:
                    errors['cleaning_weekdays'] = (
                        'El numero de dias seleccionados debe ser igual a "Limpiezas por semana".'
                    )

                self.cleaning_weekdays = unique_days

        if errors:
            raise ValidationError(errors)


class Route(models.Model):
    """Ruta de un día: agrupa mantenimientos asignados a un conductor y vehículo."""

    date    = models.DateField(verbose_name=_('Fecha'))
    module  = models.CharField(
        max_length=10,
        choices=Contract.Module.choices,
        default=Contract.Module.OBRA,
        verbose_name=_('Módulo'),
    )
    driver  = models.ForeignKey(
        Driver, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='routes', verbose_name=_('Conductor'),
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='routes', verbose_name=_('Vehículo'),
    )
    name = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name=_('Nombre / alias'),
        help_text=_('Opcional. Ej: Ruta Norte, Ruta Sur.'),
    )
    is_cancelled = models.BooleanField(
        default=False, verbose_name=_('Cancelada'),
    )

    class Meta:
        verbose_name        = _('Ruta')
        verbose_name_plural = _('Rutas')
        ordering            = ['-date', 'driver__name']

    def __str__(self) -> str:
        parts = [str(self.date)]
        if self.driver_id:
            parts.append(self.driver.name)
        if self.vehicle_id:
            parts.append(str(self.vehicle))
        if self.name:
            parts.append(f'({self.name})')
        return ' · '.join(parts)


class ServiceTask(models.Model):  # forward declaration — RouteStop is defined below
    """
    Tarea de servicio diario. Aplica las Reglas de Oro en clean():

    1. Gálibo            — el vehículo no puede superar el tamaño máximo de la ubicación.
    2. Capacidad de carga — ENTREGA y RECOGIDA solo para vehículos LARGE.
    3. Disponibilidad     — conductor disponible dinámicamente y vehículo AVAILABLE.
    4. Rango temporal     — la fecha debe caer dentro del período del contrato.
    """

    class TaskType(models.TextChoices):
        ENTREGA  = 'ENTREGA',  _('Entrega')
        LIMPIEZA = 'LIMPIEZA', _('Limpieza')
        RECOGIDA = 'RECOGIDA', _('Recogida')

    task_type      = models.CharField(
        max_length=10, choices=TaskType.choices, verbose_name=_('Tipo de tarea')
    )
    scheduled_date = models.DateField(verbose_name=_('Fecha programada'))
    driver         = models.ForeignKey(
        Driver, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='tasks', verbose_name=_('Conductor'),
    )
    vehicle        = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='tasks', verbose_name=_('Vehículo'),
    )
    location       = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        related_name='tasks', verbose_name=_('Ubicación'),
    )
    contract       = models.ForeignKey(
        Contract, on_delete=models.CASCADE,
        related_name='tasks', verbose_name=_('Contrato'),
    )
    suggested_vehicle_size = models.IntegerField(
        choices=Vehicle.Size.choices,
        null=True, blank=True,
        verbose_name=_('Tamaño sugerido'),
        help_text=_('Calculado automáticamente según tipo de tarea y ubicación.'),
    )
    is_cancelled = models.BooleanField(
        default=False, verbose_name=_('Cancelado'),
    )

    class Meta:
        verbose_name        = _('Mantenimiento')
        verbose_name_plural = _('Mantenimientos')
        ordering            = ['scheduled_date', 'task_type']

    def __str__(self) -> str:
        budget = self.contract.budget_number if self.contract_id else '—'
        return f"{budget} · {self.get_task_type_display()}"

    # ------------------------------------------------------------------
    # REGLAS DE ORO
    # ------------------------------------------------------------------
    def clean(self) -> None:
        errors: dict[str, list | str] = {}
        vehicle_errors: list[str] = []

        # Cargamos los objetos relacionados de forma segura
        # (pueden ser None en validaciones parciales de formulario)
        vehicle  = self.vehicle  if self.vehicle_id  else None
        driver   = self.driver   if self.driver_id   else None
        location = self.location if self.location_id else None
        contract = self.contract if self.contract_id else None

        # ── Regla 1 · Tamaño en LIMPIEZA según Location.max_vehicle_size ──
        if vehicle and location and self.task_type == self.TaskType.LIMPIEZA:
            if vehicle.size > location.max_vehicle_size:
                vehicle_errors.append(
                    f"Tamaño no permitido en limpieza: '{vehicle}' "
                    f"(tamaño: {vehicle.get_size_display()}) supera el máximo "
                    f"permitido en '{location}' "
                    f"(máx.: {location.get_max_vehicle_size_display()})."
                )

        # ── Regla 2 · Capacidad de carga ───────────────────────────────
        if vehicle and self.task_type in (self.TaskType.ENTREGA, self.TaskType.RECOGIDA):
            if vehicle.size != Vehicle.Size.LARGE:
                vehicle_errors.append(
                    f"Tamaño inválido: las tareas de {self.get_task_type_display()} "
                    f"deben hacerse con vehículo Camión grande."
                )

        # ── Regla 3a · Disponibilidad dinámica del conductor ───────────
        if driver and self.scheduled_date:
            weekday = self.scheduled_date.weekday()
            if not driver.is_working_day(weekday):
                day_name = dict(Driver.Weekday.choices).get(weekday, str(weekday))
                errors['driver'] = (
                    f"Conductor no disponible: '{driver}' no trabaja los {day_name}."
                )
            else:
                unavailability = driver.get_active_unavailability(self.scheduled_date)
                if unavailability:
                    errors['driver'] = (
                        f"Conductor no disponible: '{driver}' tiene una indisponibilidad activa "
                        f"({unavailability.get_reason_display()}) del {unavailability.start_date} "
                        f"al {unavailability.end_date}."
                    )

        # ── Regla 3b · Disponibilidad del vehículo ─────────────────────
        if vehicle and vehicle.status != Vehicle.Status.AVAILABLE:
            vehicle_errors.append(
                f"Vehículo no disponible: '{vehicle}' tiene estado "
                f"«{vehicle.get_status_display()}». Solo se permiten vehículos AVAILABLE."
            )

        if vehicle_errors:
            errors['vehicle'] = vehicle_errors

        # ── Regla 4 · Rango temporal del contrato ──────────────────────
        if contract and self.scheduled_date:
            too_early = self.scheduled_date < contract.start_date
            too_late  = contract.end_date and self.scheduled_date > contract.end_date
            if too_early or too_late:
                end_str = str(contract.end_date) if contract.end_date else '…'
                errors['scheduled_date'] = (
                    f"Fecha fuera de rango: {self.scheduled_date} no pertenece al "
                    f"período del contrato ({contract.start_date} → {end_str})."
                )

        # ── Regla 5 · No limpiar el día de entrega o recogida ──────────
        if (
            self.task_type == self.TaskType.LIMPIEZA
            and contract
            and self.scheduled_date
        ):
            conflict = ServiceTask.objects.filter(
                contract=contract,
                task_type__in=[self.TaskType.ENTREGA, self.TaskType.RECOGIDA],
                scheduled_date=self.scheduled_date,
            ).exclude(pk=self.pk)
            if conflict.exists():
                tipo = conflict.first().get_task_type_display()
                errors['task_type'] = (
                    f"No se puede programar una limpieza el mismo día que una "
                    f"{tipo} del mismo contrato ({self.scheduled_date})."
                )

        if errors:
            raise ValidationError(errors)


class DepotConfig(models.Model):
    """Punto de inicio y fin de todas las rutas. Singleton (pk=1 siempre)."""

    name = models.CharField(
        max_length=200, default='LooRent — Sede',
        verbose_name=_('Nombre'),
    )
    address = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name=_('Dirección'),
        help_text=_('Rellena con el buscador de Google Maps o escribe manualmente.'),
    )
    latitude = models.FloatField(
        verbose_name=_('Latitud'),
        help_text=_('Ej: 39.679469 — pega desde Google Maps o usa el buscador.'),
    )
    longitude = models.FloatField(
        verbose_name=_('Longitud'),
        help_text=_('Ej: 2.834119 — pega desde Google Maps o usa el buscador.'),
    )

    class Meta:
        verbose_name        = _('Inicio de rutas')
        verbose_name_plural = _('Inicio de rutas')

    def __str__(self):
        return f"{self.name} ({self.latitude:.5f}, {self.longitude:.5f})"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton: siempre pk=1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # No se puede eliminar

    def as_dict(self):
        """Formato compatible con el contexto depot_coords de los templates de mapa."""
        return {'lat': self.latitude, 'lng': self.longitude, 'name': self.name}

    @classmethod
    def get_current(cls):
        """Devuelve la instancia activa o un objeto transient con los defaults de settings."""
        from django.conf import settings as _s
        d = getattr(_s, 'DEPOT_COORDS', {})
        try:
            return cls.objects.get(pk=1)
        except cls.DoesNotExist:
            return cls(
                pk=1,
                name=d.get('name', 'LooRent — Sede'),
                latitude=d.get('lat', 39.679469),
                longitude=d.get('lng', 2.834119),
            )

    @classmethod
    def get_or_create_default(cls):
        """Garantiza que existe un registro en BD, creándolo desde settings si hace falta."""
        from django.conf import settings as _s
        d = getattr(_s, 'DEPOT_COORDS', {})
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'name': d.get('name', 'LooRent — Sede'),
            'latitude': d.get('lat', 39.679469),
            'longitude': d.get('lng', 2.834119),
        })
        return obj



class RouteStop(models.Model):
    """Mantenimiento assignat a una ruta, amb el seu ordre de visita."""

    route = models.ForeignKey(
        Route, on_delete=models.CASCADE,
        related_name='stops', verbose_name=_('Ruta'),
    )
    task = models.ForeignKey(
        ServiceTask, on_delete=models.CASCADE,
        related_name='route_stops', verbose_name=_('Mantenimiento'),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Orden'),
        help_text=_('Posición en la ruta (1 = primera parada).'),
    )

    class Meta:
        verbose_name        = _('Mantenimiento de la ruta')
        verbose_name_plural = _('Mantenimientos de la ruta')
        ordering            = ['order', 'pk']
        constraints         = [
            models.UniqueConstraint(fields=['task'], name='routestop_task_unique'),
        ]

    def __str__(self) -> str:
        return f"{self.order}. {self.task}"
