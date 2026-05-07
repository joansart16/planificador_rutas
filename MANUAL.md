# Manual de Usuario y Desarrollador — Planificador de Rutas (Loorent)

## Índice

1. [¿Qué es este proyecto?](#1-qué-es-este-proyecto)
2. [Instalación y puesta en marcha](#2-instalación-y-puesta-en-marcha)
3. [Arquitectura del proyecto](#3-arquitectura-del-proyecto)
4. [Modelos de datos](#4-modelos-de-datos)
5. [Panel de administración](#5-panel-de-administración)
6. [Flujo de trabajo operativo](#6-flujo-de-trabajo-operativo)
7. [Importación y exportación Excel](#7-importación-y-exportación-excel)
8. [Reglas de validación (Reglas de Oro)](#8-reglas-de-validación-reglas-de-oro)
9. [Geocodificación Google Maps](#9-geocodificación-google-maps)
10. [Referencia técnica](#10-referencia-técnica)

---

## 1. ¿Qué es este proyecto?

**Planificador de Rutas** es una aplicación Django para gestionar la logística de alquiler y limpieza de cabinas (baños portátiles, módulos de obra, etc.) en **Mallorca**.

Permite:
- Registrar clientes (empresas), ubicaciones de obra y vehículos.
- Crear contratos de servicio con fechas de entrega y recogida.
- Generar automáticamente las tareas de **ENTREGA** y **RECOGIDA**.
- Generar manualmente las tareas de **LIMPIEZA** por día de la semana.
- Asignar conductores y vehículos a cada tarea validando disponibilidad y tamaño.
- Exportar el parte de trabajo diario a Excel.

---

## 2. Instalación y puesta en marcha

### Requisitos previos

- Python 3.11+
- PostgreSQL 14+
- Cuenta Google Cloud con Maps JavaScript API + Geocoding API habilitadas

### Pasos

```bash
# 1. Clonar el repositorio
git clone <url-repo> planificador_rutas
cd planificador_rutas

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

# 3. Crear base de datos PostgreSQL
createdb loorent_planificador

# 4. Configurar variables de entorno — copiar y editar .env
```

Contenido del archivo `.env` (en la raíz del proyecto):

```ini
DJANGO_SECRET_KEY=una-clave-secreta-muy-larga-y-aleatoria
DJANGO_DEBUG=True

DB_NAME=loorent_planificador
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

GOOGLE_MAPS_API_KEY=AIza...tu-clave-de-google-maps
```

```bash
# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Arrancar el servidor
python manage.py runserver
```

Acceder a: **http://127.0.0.1:8000/admin/**

---

## 3. Arquitectura del proyecto

```
planificador_rutas/          ← Configuración Django (settings, urls, wsgi)
rutas/                       ← Aplicación principal
  models.py                  ← 7 modelos de datos
  admin.py                   ← Panel de administración completo
  signals.py                 ← Generación automática de tareas al crear contratos
  migrations/                ← 16 migraciones de base de datos
  static/rutas/admin/        ← JavaScript: geocodificación y atajos de fecha
  templates/admin/rutas/     ← Plantillas HTML del panel admin
```

### Stack tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Backend | Django 6 |
| Base de datos | PostgreSQL |
| Panel admin | Django Admin (personalizado) |
| Excel | openpyxl |
| Geocodificación | Google Maps Places Autocomplete |
| Configuración | python-dotenv |

---

## 4. Modelos de datos

### Diagrama de relaciones

```
Company ──< Location ──< Contract ──< ServiceTask
                 │                         │
                 └── default_driver        ├── driver (FK → Driver)
                                           └── vehicle (FK → Vehicle)

Driver ──< DriverUnavailability
```

### Driver (Conductor)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | CharField | Nombre completo |
| `working_days` | JSONField | Array de días laborales (0=Lunes … 6=Domingo) |

**Métodos clave:**
- `is_working_day(day)` → `bool` — ¿trabaja ese día de semana?
- `is_available_on(date)` → `bool` — día laboral Y sin indisponibilidad activa
- `get_active_unavailability(date)` → `DriverUnavailability | None`

### DriverUnavailability (Indisponibilidad)

Registra períodos en los que el conductor no está disponible.

| Campo | Valores posibles |
|-------|-----------------|
| `reason` | VACATION, SICK_LEAVE, PERSONAL, OTHER |
| `start_date` / `end_date` | Rango de fechas (inclusive) |

### Vehicle (Vehículo)

| Campo | Valores |
|-------|---------|
| `size` | 1=Pickup, 2=Camión pequeño, 3=Camión grande |
| `status` | AVAILABLE, MAINTENANCE, RETIRED |

> Solo los vehículos con `status=AVAILABLE` pueden asignarse a tareas.

### Company (Empresa / Cliente)

Agrupa ubicaciones bajo un mismo titular. Solo tiene `name` (único) y `email`.

### Location (Ubicación)

El modelo más rico. Representa una obra, evento o punto de servicio.

**Campos principales:**

| Grupo | Campos |
|-------|--------|
| Identificación | `name`, `company`, `default_driver` |
| Contacto | `contact_name`, `contact_phone`, `comment`, `cabin_count` |
| Dirección | `address`, `town`, `municipality`, `postal_code`, `zone` |
| Coordenadas | `latitude`, `longitude` |
| Restricción | `max_vehicle_size` |

**Zonas de Mallorca:**

| Código | Nombre |
|--------|--------|
| PALMA | Palma |
| TRAMUNTANA | Serra de Tramuntana |
| RAIGUER | Raiguer (Inca / Binissalem) |
| PLA | Pla de Mallorca |
| MIGJORN | Migjorn (Llucmajor / Campos) |
| LLEVANT | Llevant (Manacor / Artà) |

La zona se **detecta automáticamente** al guardar, con esta prioridad:
1. Código postal → tabla `_POSTAL_ZONE_MAP`
2. Municipio administrativo → tabla `_TOWN_ZONE_MAP`
3. Población → tabla `_TOWN_ZONE_MAP`

### Contract (Contrato)

| Campo | Descripción |
|-------|-------------|
| `location` | Ubicación del contrato |
| `start_date` | Fecha de entrega |
| `end_date` | Fecha de recogida (opcional) |
| `cleaning_frequency` | Limpiezas por semana (1–7) |
| `cleaning_weekdays` | Array JSON de días (0–6) |
| `access_start_time` / `access_end_time` | Ventana horaria (informativo) |
| `status` | ACTIVE, CLOSED |

> Al crear un contrato se generan automáticamente 1 tarea ENTREGA y (si hay fecha de fin) 1 tarea RECOGIDA. Las tareas de LIMPIEZA se generan manualmente.

### ServiceTask (Tarea de Servicio)

| Campo | Descripción |
|-------|-------------|
| `task_type` | ENTREGA, LIMPIEZA, RECOGIDA |
| `scheduled_date` | Fecha programada |
| `driver` | Conductor asignado (nullable) |
| `vehicle` | Vehículo asignado (nullable) |
| `location` | Ubicación |
| `contract` | Contrato al que pertenece |
| `suggested_vehicle_size` | Tamaño recomendado (calculado) |

---

## 5. Panel de administración

Accede en `/admin/`. Los modelos aparecen en este orden en el menú:

1. Vehículos
2. Conductores
3. Empresas
4. Ubicaciones
5. Contratos
6. Tareas de servicio

### Funcionalidades especiales por modelo

#### Conductores
- Filtro **"Disponibilidad mañana"** en la barra lateral.
- Vista de indisponibilidades en línea (inline).
- Badge de disponibilidad por conductor en la lista.

#### Ubicaciones
- **Buscador de dirección Google Maps** en el formulario de edición: escribe una dirección y se rellenan automáticamente latitud, longitud, población, municipio, código postal y zona.
- Columnas comprimidas con tooltip para pantallas pequeñas.

#### Contratos
- **Botón "Mañana"** en los selectores de fecha (en lugar de "Hoy").
- **Vista "Generar limpiezas por día"** — genera en masa las tareas LIMPIEZA para un día concreto.
- Aviso al eliminar: muestra cuántas tareas se eliminarán en cascada.
- Badge de coherencia: alerta si `cleaning_frequency` ≠ número de `cleaning_weekdays`.
- Inline con las tareas del contrato (readonly para tipo/fecha, editable para conductor/vehículo).

#### Tareas de servicio
- **Vista "Exportar tareas por día"** — descarga Excel con el parte de trabajo.
- **Acción "Reasignar conductor"** — permite asignar un conductor a múltiples tareas seleccionadas.
- Filtros avanzados: por tipo, fecha exacta, conductor, estado del vehículo, zona, empresa, estado del contrato, y asignación pendiente.

---

## 6. Flujo de trabajo operativo

### Alta de un nuevo cliente y obra

```
1. Crear Empresa (nombre + email)
2. Crear Conductor si no existe (nombre + días de trabajo)
3. Crear Vehículo si no existe (matrícula + tipo + estado)
4. Crear Ubicación:
   - Seleccionar empresa
   - Usar el buscador de Google Maps para rellenar la dirección
   - Elegir tamaño máximo de vehículo (gálibo)
   - Seleccionar conductor por defecto
5. Crear Contrato en la ubicación:
   - Fecha de inicio (entrega)
   - Fecha de fin (recogida, si se conoce)
   - Frecuencia de limpieza y días de la semana
   → El sistema genera automáticamente la tarea ENTREGA (y RECOGIDA si hay fecha de fin)
```

### Preparar el parte del día

```
1. Ir a Contratos → "Generar limpiezas por día"
   - Seleccionar la fecha (o usar botón rápido)
   - El sistema crea las tareas LIMPIEZA para todos los contratos activos ese día
2. Ir a Tareas de servicio
   - Filtrar por fecha
   - Asignar conductor y vehículo a cada tarea
   - Para reasignaciones masivas: seleccionar tareas → Acción "Reasignar conductor"
3. Exportar el parte: "Exportar tareas por día" → descarga Excel
```

### Gestionar indisponibilidades de conductores

```
1. Ir a Conductores → editar el conductor
2. En la sección "Indisponibilidades", añadir el período:
   - Motivo (vacaciones, baja médica, etc.)
   - Fecha inicio y fin
3. Al asignar ese conductor a una tarea en ese período, el sistema mostrará error
```

---

## 7. Importación y exportación Excel

Cada modelo soporta carga masiva desde Excel. El flujo es:

1. Descargar la **plantilla Excel de prueba** (incluye fila de ejemplo y hoja "Valores").
2. Rellenar los datos siguiendo el formato.
3. Cargar el archivo desde el botón **"Cargar Excel"**.

### Columnas por modelo

**Empresas:** `razon_social`, `correo_electronico`

**Conductores:** `nombre`, `dias_trabajo` (ej: `0,1,2,3,4`)

**Vehículos:** `nombre_vehiculo`, `matricula`, `tipo`, `estado`

**Ubicaciones:** `nombre`, `empresa`, `contacto_nombre`, `contacto_telefono`, `direccion`, `comentario`, `poblacion`, `municipio`, `codigo_postal`, `zona`, `cabinas`, `tipo_max_vehiculo`, `conductor_por_defecto`, `latitud`, `longitud`

**Contratos:** `ubicacion`, `fecha_inicio`, `fecha_fin`, `limpiezas_semana`, `dias_limpieza`, `hora_acceso_inicio`, `hora_acceso_fin`, `estado`

### Comportamiento de la importación
- Registros existentes se **omiten** (no se duplican ni actualizan).
- Se muestran avisos por fila con errores o registros omitidos.
- Se muestran hasta 10 errores/avisos; el resto se cuenta.

---

## 8. Reglas de validación (Reglas de Oro)

Al asignar conductor y vehículo a una `ServiceTask`, el sistema valida:

| Regla | Descripción |
|-------|-------------|
| **1. Gálibo** | El vehículo no puede superar `location.max_vehicle_size` en tareas LIMPIEZA. |
| **2. Capacidad de carga** | Tareas ENTREGA y RECOGIDA solo admiten vehículos de tamaño LARGE (Camión grande). |
| **3a. Disponibilidad del conductor** | El conductor debe tener ese día como laboral y no tener indisponibilidad activa. |
| **3b. Disponibilidad del vehículo** | El vehículo debe estar en estado `AVAILABLE`. |
| **4. Rango temporal** | La fecha de la tarea debe caer dentro del período del contrato. |
| **5. No superponer** | No se puede crear una LIMPIEZA el mismo día que una ENTREGA o RECOGIDA del mismo contrato. |

Estas validaciones se ejecutan en `ServiceTask.clean()` y se muestran como errores en el formulario del admin.

---

## 9. Geocodificación Google Maps

El formulario de edición de **Ubicaciones** incluye un buscador de dirección integrado con Google Maps.

### Cómo funciona

1. Escribe una dirección en el campo de búsqueda (ej: `Avinguda Violetes, 18, Bunyola`).
2. Al seleccionar un resultado del autocompletado, se rellenan automáticamente:
   - `address` (calle y número)
   - `latitude` y `longitude`
   - `town` (población)
   - `municipality` (municipio administrativo)
   - `postal_code`
   - `zone` (comarca detectada automáticamente)
3. Se muestra un mini-mapa con la ubicación.
4. Si editas manualmente `latitude` o `longitude`, los demás campos se actualizan via reverse geocoding.

### Configuración necesaria

La API Key de Google Maps debe tener habilitados:
- **Maps JavaScript API**
- **Places API**
- **Geocoding API**

Configúrala en `.env`:
```ini
GOOGLE_MAPS_API_KEY=AIza...
```

---

## 10. Referencia técnica

### Señales Django (`signals.py`)

`generate_service_tasks` se dispara con `post_save` al crear un `Contract`:
- Crea 1 tarea `ENTREGA` en `start_date`.
- Crea 1 tarea `RECOGIDA` en `end_date` (si existe).
- Asigna `location.default_driver` a ambas.
- Vehículo queda en blanco para asignación manual.

### Orden del menú admin

Controlado por el diccionario `ROUTES_MENU_ORDER` en `admin.py`. Para cambiar el orden modifica los valores numéricos:

```python
ROUTES_MENU_ORDER = {
    'Vehicle': 1,
    'Driver': 2,
    'Company': 3,
    'Location': 4,
    'Contract': 5,
    'ServiceTask': 6,
}
```

### Añadir un municipio o código postal

Si aparece una zona no detectada, edita los diccionarios en `rutas/models.py`:

- `Location._TOWN_ZONE_MAP` — para municipios (en minúsculas, sin tildes)
- `Location._POSTAL_ZONE_MAP` — para códigos postales

Y replica el cambio en `rutas/static/rutas/admin/location_geocode.js` en los objetos `TOWN_ZONE` y `POSTAL_ZONE`.

### Exportación Excel diaria (parte de trabajo)

Las columnas del Excel exportado son:

| Columna | Contenido |
|---------|-----------|
| CLIENTE | Nombre de la empresa |
| POBLACION | Población (en mayúsculas) |
| ID EXTERNO | Nombre de la ubicación |
| DIRECCION LINEA 2 | Dirección textual |
| DIRECCION | Coordenadas `lat, lon` |
| LIMPIEZA | `S` (semanal) o `N/Total` (ej: `2/3`) |
| UNIDADES | Número de cabinas |
| COMENTARIOS | Comentario de la ubicación (o `EO`/`RE` para entrega/recogida) |
| HORA | (vacío, para rellenar manualmente) |
| PERSONA DE REF. | Contacto en obra |
| TELÉFONO | Teléfono de contacto |
| EMAIL | Email de la empresa |

### Variables de entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `DJANGO_SECRET_KEY` | Clave secreta Django | `django-insecure-fallback-solo-dev` |
| `DJANGO_DEBUG` | Modo debug | `True` |
| `DB_NAME` | Nombre de la BD | `loorent_planificador` |
| `DB_USER` | Usuario PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña PostgreSQL | *(vacío)* |
| `DB_HOST` | Host PostgreSQL | `localhost` |
| `DB_PORT` | Puerto PostgreSQL | `5432` |
| `GOOGLE_MAPS_API_KEY` | API Key de Google Maps | *(vacío)* |
