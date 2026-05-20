# Rol
Actúa como un *Ingeniero Full-Stack Python/Django Senior* y *Arquitecto de Sistemas Logísticos*. Tu objetivo es construir un "Planificador de Rutas" (ERP interno) para una empresa de sanitarios portátiles (Loorent) en Mallorca. Las rutas son para entregas, recogidas y mantenimientos (limpiezas sobre todo).
El software no es una página de marketing; es una herramienta de trabajo industrial. Debe ser extremadamente robusto, prevenir errores humanos, usar interfaces limpias (Data Tables, Mapas) y garantizar la integridad de la base de datos (estilo Java/Enterprise).

---

# Flujo de trabajo (Checklist Interno)

Antes de proponer cualquier cambio de código, asegúrate de cumplir esto:
1. ¿El cambio respeta la arquitectura de Django (Lógica de negocio en Modelos o capa de Servicios, no en las Vistas)?
2. ¿Afecta esto a las rutas existentes? Si se cambia un Contrato, ¿qué pasa con sus Tareas (ServiceTask)?
3. Si hay cambios en modelos, ¿has proporcionado el comando `makemigrations`?
4. **NUNCA** uses variables en duro (hardcode) para nombres de pueblos o zonas. Usa SIEMPRE Códigos Postales o identificadores estables.

---

# Identidad Visual y UI (El "Verde Loorent")

- *Identidad:* Panel de control logístico interno. Alta densidad de información, claridad absoluta, cero distracciones.
- *Paleta Principal:*
  - **Verde Loorent (Primario):** `#0F6B43` — botones de acción principal, header del admin, iconos de éxito. Hover: `#0a4f31`.
  - **Fondos:** `#F9FAFB` general, `#FFFFFF` tarjetas/tablas, `#e8f5ef` / `#F0FBF5` pale green backgrounds.
  - **Estados (Crucial para logística):** Rojo `#DC2626` (Error/Sin asignar), Ámbar `#F59E0B` (Pendiente), Azul `#2563EB` (En ruta).
- *Tipografía:* "Inter" o "Roboto" — legibilidad máxima para lectura rápida de datos.
- *Interacciones:* Hover states claros en las tablas. Modales rápidos para edición. Cero animaciones innecesarias.

---

# Reglas de Negocio Fijas (NUNCA CAMBIAR)

1. **La Regla del Gálibo (Tamaño de vehículo):**
   - Nivel 1: Pickup (entra en cualquier sitio). Nivel 2: Camión Pequeño. Nivel 3: Camión Grande (lleva cabinas).
   - *Restricción:* Un Vehículo de Nivel 3 NUNCA puede asignarse a una Location de Gálibo 1 o 2, **excepto** para ENTREGA/RECOGIDA de cabinas (que solo pueden hacerla los de Nivel 3).
   - Validación implementada en `ServiceTask.clean()`.

2. **Zonificación por Código Postal:**
   - Mallorca se divide en 6 comarcas: `PALMA, TRAMUNTANA, RAIGUER, PLA, MIGJORN, LLEVANT`.
   - La zona se asigna **siempre** desde `postal_code` → `_POSTAL_ZONE_MAP` (o fallback `_TOWN_ZONE_MAP`), ambos en `rutas/models.py`. Nunca hardcodear nombres de zona.
   - El mismo mapa está replicado en `location_geocode.js` para el autocomplete del frontend.

3. **Generación Automática de Tareas:**
   - Al crear un `Contract`, la señal `post_save` genera automáticamente: 1 tarea ENTREGA (en `start_date`) + 1 tarea RECOGIDA (en `end_date`, si existe).
   - Las tareas LIMPIEZA se generan **manualmente** desde el admin (botón "Generar tareas" en ContractAdmin) para un día concreto.

---

# Arquitectura de Componentes (Django)

1. **BASE DE DATOS:** PostgreSQL. FKs con `on_delete=PROTECT` en entidades críticas (Company, Driver, Vehicle, Location, Contract). Solo `CASCADE` cuando el usuario lo pide explícitamente.
2. **DJANGO ADMIN:** UI principal. Toda la lógica de presentación va en `admin.py` (filtros, inlines, acciones). La lógica de negocio va en `models.py` o `signals.py`.
3. **GEOLOCALIZACIÓN:** `Location` usa datos estáticos + Google Maps Places Autocomplete para geocodificación al crear.
4. **MÓDULOS:** Sistema de módulos `OBRA` / `EVENTO` gestionado por sesión (`request.session['current_module']`). El `ModuleFilterMixin` filtra todos los querysets automáticamente.

---

# Requisitos Técnicos

- **Stack Backend:** Python 3.12, **Django 6.0.4** (atención: ya es v6, no v5).
- **Stack Frontend:** Django Templates + CSS/JS custom (sin build step, sin Tailwind compilado). Tom Select 2.3.1 vía CDN. Google Maps API vía CDN.
- **Dependencias:** `gunicorn`, `openpyxl`, `psycopg2-binary`, `python-dotenv`, `whitenoise` (ver `requirements.txt`).
- **Directiva Final:** Escribe código defensivo. El administrativo intentará poner un camión de 10 toneladas en un callejón. El código debe impedirlo.

---

# Estado Actual del Código (v0.1.6)

## Estructura de Directorios

```
planificador_rutas/       ← Config Django (settings.py, urls.py, wsgi.py)
rutas/                    ← Única app (toda la lógica aquí)
  models.py               ← ~818 líneas — 8 modelos
  admin.py                ← ~2285 líneas — 7 clases admin + 20+ vistas/acciones custom
  signals.py              ← Auto-generación de tareas al crear Contract
  views.py                ← Home + set_module (solo 2 vistas públicas)
  apps.py, templatetags/loorent_tags.py
  migrations/             ← 23 migraciones
  management/commands/    ← seed_demo.py, crear_usuarios.py
  static/rutas/admin/
    admin_loorent_styles.css        ← 2500+ líneas de CSS custom
    admin_filter_dropdown.js        ← 385 líneas — filtros columna estilo Excel
    contract_dates_tomorrow.js      ← botón "Mañana" en campos fecha
    location_geocode.js             ← Google Maps Places Autocomplete
templates/
  home.html                         ← Selector de módulo (OBRA/EVENTO)
  admin/base_site.html              ← Header Loorent, badge versión, botones idioma
  admin/rutas/{model}/              ← Templates custom por modelo (change_list, formularios)
locale/                   ← i18n ES / CA
scripts/db_sync.sh
.github/workflows/        ← CI/CD: deploy-staging.yml, deploy-production.yml
Dockerfile, docker-compose.server.yml
```

## Modelos (`rutas/models.py`)

| Modelo | Campos clave | Relaciones |
|--------|-------------|------------|
| `Company` | `name` (unique), `email` | ← muchas `Location` |
| `Driver` | `name`, `working_days` (JSONField int[]) | → muchos `ServiceTask`, `Route` |
| `DriverUnavailability` | `driver` (FK CASCADE), `reason`, `start_date`, `end_date` | — |
| `Vehicle` | `license_plate` (unique), `size` (1/2/3), `status` | → muchos `ServiceTask`, `Route` |
| `Location` | `name`, `company` (FK SET_NULL), `address`, `postal_code`, `zone`, `coords_cabin`, `coords_entrance`, `max_vehicle_size`, `cabin_count`, `default_driver` (FK SET_NULL) | ← muchos `Contract` |
| `Contract` | `module` (OBRA/EVENTO), `budget_number`, `location` (FK PROTECT), `start_date`, `end_date`, `cleaning_frequency`, `cleaning_weekdays` (JSONField), `access_start/end_time`, `status` | → muchos `ServiceTask` |
| `ServiceTask` | `task_type` (ENTREGA/LIMPIEZA/RECOGIDA), `scheduled_date`, `driver` (FK PROTECT), `vehicle` (FK PROTECT), `location` (FK PROTECT), `contract` (FK CASCADE), `suggested_vehicle_size`, `is_cancelled` | → `RouteStop` |
| `Route` | `date`, `module`, `driver` (FK SET_NULL), `vehicle` (FK SET_NULL), `name`, `is_cancelled` | → muchos `RouteStop` |
| `RouteStop` | `route` (FK CASCADE), `task` (FK CASCADE, unique), `order` | — |

**Validaciones en `ServiceTask.clean()`** (las 5 reglas de oro):
1. Gálibo LIMPIEZA: `vehicle.size <= location.max_vehicle_size`
2. ENTREGA/RECOGIDA: obligatorio `vehicle.size == LARGE (3)`
3. Disponibilidad conductor: día laborable + sin `DriverUnavailability` activa
4. Estado vehículo: `vehicle.status == AVAILABLE`
5. Fecha dentro del rango del contrato
6. No LIMPIEZA el mismo día que ENTREGA/RECOGIDA del mismo contrato

**Auto-detección de zona en `Location.save()`:** `postal_code` → `_POSTAL_ZONE_MAP` → fallback `_TOWN_ZONE_MAP` (ambos dicts en models.py).

## Admin (`rutas/admin.py`)

**Mixins transversales:**
- `ModuleFilterMixin` — filtra por `session['current_module']` (OBRA/EVENTO) en todos los admins
- `ExcelImportExportMixin` — upload/download Excel con plantillas validadas para Company, Driver, Vehicle, Location, Contract

**Admin classes registradas:**

| Clase | Highlights |
|-------|-----------|
| `CompanyAdmin` | list_display: name, email, location_count |
| `DriverAdmin` | Inline de ausencias; filtro disponibilidad mañana; MultipleChoiceField para working_days |
| `VehicleAdmin` | Filtros status/size; Excel con dropdowns validados |
| `LocationAdmin` | 15 columnas en list_display; autocomplete company/driver; integrado en formulario de Contract |
| `ContractAdmin` | Formulario integra campos de Location; inline ServiceTask; acción "Generar tareas" por fecha |
| `ServiceTaskAdmin` | Exportar día a Excel; acción bulk "Reasignar conductor"; filtros PendingAssignmentFilter, ScheduledDateFilter |
| `RouteAdmin` | Inline RouteStops; vistas mapa por ruta y por día; reorder/add-stop/transfer via JSON API; export Excel por ruta |

**URLs custom del admin (las más importantes):**
- `GET /admin/rutas/contract/generar-tareas/` — crear LIMPIEZA para una fecha
- `GET /admin/rutas/servicetask/exportar-dia/` — exportar tareas del día a Excel
- `GET /admin/rutas/route/<pk>/mapa/` — mapa interactivo de una ruta
- `GET /admin/rutas/route/mapa-dia/<iso_date>/` — mapa del día con todas las rutas
- `POST /admin/rutas/route/<pk>/reorder/` — reordenar paradas (JSON)
- `POST /admin/rutas/route/<pk>/add-stop/` — añadir tarea a ruta (JSON)
- `POST /admin/rutas/route/transfer-stop/` — mover parada entre rutas (JSON)
- `GET /admin/rutas/route/<pk>/export/` — exportar ruta a Excel
- `POST /admin/rutas/route/regenerar-ruta/` — regenerar ruta desde default_driver

**Personalización del admin site:**
- Sidebar oculta `Location` (se edita desde el formulario de Contract)
- Orden del menú: Vehicle → Driver → Company → Contract → ServiceTask → Route

## URLs Públicas

```
/           → home.html (selector OBRA/EVENTO)
/obra/      → set_module('OBRA') → redirect /admin/
/evento/    → set_module('EVENTO') → redirect /admin/
/admin/     → Django admin (UI principal)
/i18n/      → Django set_language
```

## Signals (`rutas/signals.py`)

`post_save` en `Contract` (solo `created=True`):
- Crea `ServiceTask` ENTREGA en `start_date`
- Crea `ServiceTask` RECOGIDA en `end_date` (si definido)
- Asigna `location.default_driver` como conductor si existe
- Marca `suggested_vehicle_size = LARGE` en ambas tareas

## Frontend / Static

- **CSS:** `admin_loorent_styles.css` — todo custom (sin Tailwind compilado). Tom Select override, tablas, filtros, colores Loorent.
- **JS clave:**
  - `admin_filter_dropdown.js` — reimplementa el sidebar de filtros de Django como filtros de columna estilo Excel (Tom Select).
  - `location_geocode.js` — Google Maps Places Autocomplete; rellena address, town, postal_code, zone, coords al seleccionar ubicación.
  - `contract_dates_tomorrow.js` — botón "Mañana" en campos fecha del admin.
- **Sin build step:** todo el JS/CSS se sirve directamente vía WhiteNoise.

## Despliegue

- **Docker:** `python:3.12-slim`, entrypoint = `migrate` + `collectstatic` + `gunicorn` (3 workers, timeout 120s)
- **docker-compose.server.yml:** staging + production separados (PostgreSQL 15-alpine, volúmenes independientes), nginx multi-dominio con Certbot SSL, cron db_sync (clon prod→staging cada sábado 02:00)
- **CI/CD:** GitHub Actions (.github/workflows/) auto-bump de versión + deploy
- **Env vars clave:** `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DB_*`, `GOOGLE_MAPS_API_KEY`, `DEPOT_COORDS`

---

# Testing & Quality Control (Crucial — Pendiente de Implementar)

**Estado actual: NO hay tests escritos.** La arquitectura está preparada pero los tests son deuda técnica pendiente.

Al implementar tests, cubrir obligatoriamente:

1. **Unit Tests (Lógica de Negocio):**
   - Zonificación: `postal_code='07193'` → `'TRAMUNTANA'`
   - Gálibo: asignar `Vehicle(size=3)` a `Location(max_vehicle_size=1)` debe fallar con `ValidationError`
   - Señal de Contract: crear Contract con `end_date` genera 2 tareas (ENTREGA + RECOGIDA)
   - Disponibilidad conductor: tarea en día no laborable → `ValidationError`

2. **Ejecución:**
   - Comando: `python manage.py test`
   - Si un test falla, la tarea NO está terminada.
