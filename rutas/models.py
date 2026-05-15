import unicodedata

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class Driver(models.Model):
    """Conductor con calendario laboral e indisponibilidades."""

    name   = models.CharField(max_length=150, verbose_name='Nombre')
    working_days = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Días de trabajo',
        help_text='Selecciona de lunes a domingo. Array de 0-6 representando lunes a domingo.',
    )

    class Weekday(models.IntegerChoices):
        MONDAY    = 0, 'Lunes'
        TUESDAY   = 1, 'Martes'
        WEDNESDAY = 2, 'Miércoles'
        THURSDAY  = 3, 'Jueves'
        FRIDAY    = 4, 'Viernes'
        SATURDAY  = 5, 'Sábado'
        SUNDAY    = 6, 'Domingo'

    class Meta:
        verbose_name        = 'Conductor'
        verbose_name_plural = 'Conductores'
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
        VACATION   = 'VACATION',   'Vacaciones'
        SICK_LEAVE = 'SICK_LEAVE', 'Baja médica'
        PERSONAL   = 'PERSONAL',   'Asunto personal'
        OTHER      = 'OTHER',      'Otro motivo'

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='unavailabilities',
        verbose_name='Conductor',
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        verbose_name='Motivo',
    )
    start_date = models.DateField(verbose_name='Fecha de inicio')
    end_date = models.DateField(
        verbose_name='Fecha de fin',
        help_text='Si es un solo día, pon la misma fecha que inicio.',
    )
    notes = models.TextField(
        blank=True, default='',
        verbose_name='Notas',
    )

    class Meta:
        verbose_name        = 'Indisponibilidad del conductor'
        verbose_name_plural = 'Indisponibilidades del conductor'
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
        PICKUP = 1, 'Pickup'
        SMALL  = 2, 'Camión pequeño'
        LARGE  = 3, 'Camión grande'

    class Status(models.TextChoices):
        AVAILABLE   = 'AVAILABLE',   'Disponible'
        MAINTENANCE = 'MAINTENANCE', 'En mantenimiento'
        RETIRED     = 'RETIRED',     'Retirado'

    name = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name='Nombre del vehículo',
        help_text='Alias interno del vehículo (ej: Pickup 1, Camión Norte).',
    )
    license_plate = models.CharField(
        max_length=20, unique=True, verbose_name='Matrícula'
    )
    size = models.IntegerField(
        choices=Size.choices, verbose_name='Tamaño'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        verbose_name='Estado',
    )

    class Meta:
        verbose_name        = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering            = ['license_plate']

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} · {self.license_plate}"
        return f"{self.license_plate} · {self.get_size_display()}"


class Company(models.Model):
    """Empresa o cliente. Agrupa ubicaciones bajo un mismo titular."""

    name  = models.CharField(max_length=200, unique=True, verbose_name='Razón social')
    email = models.EmailField(
        verbose_name='Correo electrónico',
        help_text='Obligatorio. Se usa como fallback en el exportador cuando la ubicación no tiene email propio.',
    )

    class Meta:
        verbose_name        = 'Empresa'
        verbose_name_plural = 'Empresas'
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
        PALMA      = 'PALMA',      'Palma'
        TRAMUNTANA = 'TRAMUNTANA', 'Serra de Tramuntana'
        RAIGUER    = 'RAIGUER',    'Raiguer (Inca / Binissalem)'
        PLA        = 'PLA',        'Pla de Mallorca'
        MIGJORN    = 'MIGJORN',    'Migjorn (Llucmajor / Campos)'
        LLEVANT    = 'LLEVANT',    'Llevant (Manacor / Artà)'

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
    name    = models.CharField(max_length=200, verbose_name='Nombre del sitio')
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='locations',
        verbose_name='Empresa / Cliente',
        help_text='Empresa titular. Permite filtrar todas sus ubicaciones.',
    )

    # ── Contacto en obra ─────────────────────────────────────────────
    contact_name  = models.CharField(
        max_length=150, blank=True, default='',
        verbose_name='Persona de contacto',
        help_text='Responsable de la obra o punto de servicio.',
    )
    contact_phone = models.CharField(
        max_length=20, blank=True, default='',
        verbose_name='Teléfono de contacto',
    )
    email = models.EmailField(
        blank=True, default='',
        verbose_name='Email contacto obra',
        help_text='Opcional. Si se rellena, se usa en el exportador en lugar del email del cliente.',
    )
    comment = models.TextField(
        blank=True,
        default='',
        verbose_name='Comentario',
        help_text='Indicaciones operativas para el servicio en esta ubicación.',
    )
    cabin_count = models.PositiveIntegerField(
        default=1,
        verbose_name='Número de cabinas',
        help_text='Cantidad de cabinas a limpiar en esta ubicación.',
    )

    # ── Dirección ─────────────────────────────────────────────────────
    address     = models.TextField(verbose_name='Dirección (calle y número)')
    town        = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Población',
        help_text='Núcleo habitado (ej: Palmanyola). Se rellena automáticamente.',
    )
    municipality = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Municipio',
        help_text='Municipio administrativo (ej: Bunyola). Se usa para calcular la comarca.',
    )
    postal_code = models.CharField(
        max_length=10, blank=True, default='',
        verbose_name='Código postal',
    )
    zone        = models.CharField(
        max_length=20,
        choices=Zone.choices,
        blank=True, default='',
        verbose_name='Zona de Mallorca',
        help_text='Comarca o zona de la isla para agrupar y filtrar rutas.',
    )

    # ── Coordenadas ───────────────────────────────────────────────────
    coords_cabin = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Coordenadas cabina',
        help_text='Pega directamente desde Google Maps (ej: 39.619316, 2.643553).',
    )
    coords_entrance = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Coordenadas entrada finca',
        help_text='Opcional. Si se rellena, el exportador genera una fila adicional con "Entrada finca".',
    )

    # ── Restricción de vehículo ───────────────────────────────────────
    max_vehicle_size = models.IntegerField(
        choices=Vehicle.Size.choices,
        verbose_name='Tamaño máximo de vehículo',
        help_text='Vehículos con tamaño superior serán rechazados (gálibo).',
    )
    default_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='default_locations',
        verbose_name='Conductor por defecto',
        help_text='Se asignará automáticamente a las tareas de este sitio (puede cambiar después).',
    )

    class Meta:
        verbose_name        = 'Ubicación'
        verbose_name_plural = 'Ubicaciones'
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
        OBRA   = 'OBRA',   'Obra'
        EVENTO = 'EVENTO', 'Evento'

    class Status(models.TextChoices):
        ACTIVE      = 'ACTIVE',       'Activo'
        INTERRUPTED = 'INTERRUPTED',  'Interrumpido'
        RETIRED     = 'RETIRED',      'Retirado'

    class Weekday(models.IntegerChoices):
        MONDAY = 0, 'Lunes'
        TUESDAY = 1, 'Martes'
        WEDNESDAY = 2, 'Miercoles'
        THURSDAY = 3, 'Jueves'
        FRIDAY = 4, 'Viernes'
        SATURDAY = 5, 'Sábado'
        SUNDAY = 6, 'Domingo'

    module = models.CharField(
        max_length=10,
        choices=Module.choices,
        default=Module.OBRA,
        verbose_name='Módulo',
        help_text='Obra o Evento. Determina en qué sección aparece este pedido.',
    )
    budget_number = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Nº presupuesto',
        help_text='Número de presupuesto. Clave que identifica esta obra en el sistema.',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name='Ubicación',
    )
    start_date         = models.DateField(verbose_name='Fecha de inicio')
    end_date           = models.DateField(
        null=True, blank=True,
        verbose_name='Fecha de fin (recogida)',
        help_text='Dejar en blanco si la fecha de recogida no se conoce aún.',
    )
    cleaning_frequency = models.PositiveIntegerField(
        verbose_name='Limpiezas por semana',
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text='Numero de servicios de limpieza semanales (1 a 7).',
    )
    cleaning_weekdays = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Dias de limpieza',
        help_text='Selecciona de lunes a domingo. Deben coincidir con limpiezas por semana.',
    )
    access_start_time = models.TimeField(
        null=True, blank=True,
        verbose_name='Hora de acceso (inicio)',
        help_text='Hora a partir de la cual se puede acceder al sitio.',
    )
    access_end_time = models.TimeField(
        null=True, blank=True,
        verbose_name='Hora de acceso (fin)',
        help_text='Última hora permitida de acceso al sitio.',
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Estado',
    )

    class Meta:
        verbose_name        = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering            = ['-start_date']

    def __str__(self) -> str:
        location_str = self.location if self.location_id else '?'
        end_str = str(self.end_date) if self.end_date else '…'
        return f"Pedido #{self.pk} · {location_str} ({self.start_date} → {end_str})"

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


class ServiceTask(models.Model):
    """
    Tarea de servicio diario. Aplica las Reglas de Oro en clean():

    1. Gálibo            — el vehículo no puede superar el tamaño máximo de la ubicación.
    2. Capacidad de carga — ENTREGA y RECOGIDA solo para vehículos LARGE.
    3. Disponibilidad     — conductor disponible dinámicamente y vehículo AVAILABLE.
    4. Rango temporal     — la fecha debe caer dentro del período del contrato.
    """

    class TaskType(models.TextChoices):
        ENTREGA  = 'ENTREGA',  'Entrega'
        LIMPIEZA = 'LIMPIEZA', 'Limpieza'
        RECOGIDA = 'RECOGIDA', 'Recogida'

    task_type      = models.CharField(
        max_length=10, choices=TaskType.choices, verbose_name='Tipo de tarea'
    )
    scheduled_date = models.DateField(verbose_name='Fecha programada')
    driver         = models.ForeignKey(
        Driver, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='tasks', verbose_name='Conductor',
    )
    vehicle        = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='tasks', verbose_name='Vehículo',
    )
    location       = models.ForeignKey(
        Location, on_delete=models.PROTECT,
        related_name='tasks', verbose_name='Ubicación',
    )
    contract       = models.ForeignKey(
        Contract, on_delete=models.CASCADE,
        related_name='tasks', verbose_name='Contrato',
    )
    suggested_vehicle_size = models.IntegerField(
        choices=Vehicle.Size.choices,
        null=True, blank=True,
        verbose_name='Tamaño sugerido',
        help_text='Calculado automáticamente según tipo de tarea y ubicación.',
    )

    class Meta:
        verbose_name        = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
        ordering            = ['scheduled_date', 'task_type']

    def __str__(self) -> str:
        return (
            f"{self.get_task_type_display()} · "
            f"{self.scheduled_date} · "
            f"{self.driver.name if self.driver_id else '—'}"
        )

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
