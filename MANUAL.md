# Manual Tècnic — Planificador de Rutes Loorent

> Guia de referència per entendre, mantenir i evolucionar el projecte.  
> Actualitzat a la versió 0.1.x

---

## Taula de continguts

1. [Visió general](#1-visió-general)
2. [Estructura de carpetes](#2-estructura-de-carpetes)
3. [Models de dades](#3-models-de-dades)
4. [Mòduls del Admin](#4-mòduls-del-admin)
5. [On modificar cada cosa](#5-on-modificar-cada-cosa)
6. [Infraestructura i entorns](#6-infraestructura-i-entorns)
7. [Operacions habituals al servidor](#7-operacions-habituals-al-servidor)
8. [Regles de negoci fixades](#8-regles-de-negoci-fixades)
9. [Referència tècnica](#9-referència-tècnica)

---

## 1. Visió general

**Planificador de Rutes** és un ERP intern per a Loorent (sanitaris portàtils a Mallorca).  
Gestiona entregues, recollides i manteniments (neteges) des d'un panell d'administració Django.

**Stack tècnic:**

| Capa | Tecnologia |
|------|-----------|
| Backend | Python 3.12 + Django 6 |
| Base de dades | PostgreSQL 15 |
| Servidor web | Gunicorn + Nginx |
| Infraestructura | Docker + Docker Compose a AWS EC2 |
| CI/CD | GitHub Actions (auto-deploy) |

---

## 2. Estructura de carpetes

```
planificador_rutas/            ← Configuració Django (settings, urls, wsgi)
  settings.py                  ← Variables d'entorn, middleware, BD, i18n
  urls.py                      ← Rutes URL principals
  wsgi.py                      ← Punt d'entrada del servidor

rutas/                         ← Aplicació principal (TOTA la lògica aquí)
  models.py                    ← Models de dades i regles de negoci
  admin.py                     ← Interfície d'administració (UI principal)
  views.py                     ← Home i selecció de mòdul (OBRA/EVENTO)
  signals.py                   ← Generació automàtica de tasques al guardar contractes
  apps.py                      ← Configuració de l'app Django

  migrations/                  ← Historial de canvis a la BD (no tocar manualment)
    0001_initial.py ... 0023_*

  templates/admin/rutas/       ← Plantilles HTML de cada mòdul
    company/                   ← Llistat d'empreses
    contract/                  ← Formulari i llistat de pedidos
    driver/                    ← Llistat de conductors
    location/                  ← Formulari i llistat d'ubicacions
    route/                     ← Rutes, mapes, regeneració
    servicetask/               ← Llistat de tasques, exportació, reassignació
    vehicle/                   ← Llistat de vehicles
    shared/
      upload_excel.html        ← Plantilla reutilitzable per importació Excel

  static/rutas/admin/          ← CSS i JavaScript propi
    admin_loorent_styles.css   ← Tema verd Loorent (#0F6B43)
    admin_filter_dropdown.js   ← Filtres desplegables estil Excel (Tom Select)
    location_geocode.js        ← Integració Google Maps als formularis d'ubicació
    contract_dates_tomorrow.js ← Botó "Demà" als selectors de data

  templatetags/
    loorent_tags.py            ← Tag {% app_version %} que llegeix el fitxer VERSION

  management/commands/
    seed_demo.py               ← Carrega dades de demostració
    crear_usuarios.py          ← Creació massiva d'usuaris

templates/admin/               ← Plantilles globals Django admin
  base_site.html               ← Header verd + badge de versió + selector d'idioma

locale/                        ← Traduccions (es / ca)
scripts/
  db_sync.sh                   ← Sincronització producció → staging (cron dissabtes)

.github/workflows/
  deploy-staging.yml           ← Auto-deploy staging + bump de versió en cada push
  deploy-production.yml        ← Deploy manual a producció (botó GitHub Actions)

docker-compose.server.yml      ← Tots els serveis Docker (staging + producció)
nginx.server.conf              ← Proxy invers Nginx multi-domini
Dockerfile                     ← Imatge Docker de l'aplicació
docker-entrypoint.sh           ← migrate + collectstatic + gunicorn

VERSION                        ← Versió actual (s'actualitza automàticament)
CHANGELOG.md                   ← Historial de versions
requirements.txt               ← Dependències Python
```

---

## 3. Models de dades

Tots els models estan a **`rutas/models.py`**.

### Diagrama de relacions

```
Company ──< Location ──< Contract ──< ServiceTask >── Driver
                │                                 └── Vehicle
                └── default_driver (FK → Driver)

Driver ──< DriverUnavailability

Route ──< RouteStop >── ServiceTask
```

---

### Company (Empresa)
Agrupa les ubicacions d'un client.

| Camp | Descripció |
|------|-----------|
| `name` | Nom de l'empresa (únic) |
| `email` | Correu electrònic |

---

### Location (Ubicació / Obra)

| Camp | Descripció |
|------|-----------|
| `name` | Nom de l'obra o event |
| `company` | FK → Company |
| `default_driver` | FK → Driver (conductor habitual) |
| `address` | Adreça completa |
| `town` | Població |
| `postal_code` | Codi postal |
| `zone` | Comarca (calculada automàticament des del CP) |
| `latitude / longitude` | Coordenades GPS |
| `max_vehicle_size` | Gàlib màxim (1=Pickup, 2=Petit, 3=Gran) |
| `cabin_count` | Nombre de cabines instal·lades |
| `comment` | Comentari lliure |

**Zones de Mallorca:**

| Codi | Zona |
|------|------|
| PALMA | Palma |
| TRAMUNTANA | Serra de Tramuntana |
| RAIGUER | Raiguer (Inca / Binissalem) |
| PLA | Pla de Mallorca |
| MIGJORN | Migjorn (Llucmajor / Campos) |
| LLEVANT | Llevant (Manacor / Artà) |

La zona es **detecta automàticament** al guardar, mirant el codi postal al diccionari `_POSTAL_ZONE_MAP` de `models.py`.

---

### Driver (Conductor)

| Camp | Descripció |
|------|-----------|
| `name` | Nom complet |
| `working_days` | JSON array de dies laborables [0=Dll … 6=Dg] |
| `default_vehicle` | FK → Vehicle (habitual) |

**Mètodes clau:**
- `is_available_on(date)` → comprova dia laborable + sense indisponibilitat activa

---

### DriverUnavailability (Indisponibilitat)

Períodes en els quals el conductor no pot treballar.

| Camp | Valors |
|------|--------|
| `reason` | VACATION, SICK_LEAVE, PERSONAL, OTHER |
| `start_date / end_date` | Rang de dates (inclosos) |

---

### Vehicle

| Camp | Valors |
|------|--------|
| `size` | PICKUP (1), SMALL (2), LARGE (3) |
| `status` | AVAILABLE, MAINTENANCE, RETIRED |

---

### Contract (Pedido)

| Camp | Descripció |
|------|-----------|
| `location` | FK → Location |
| `start_date` | Data d'entrega |
| `end_date` | Data de recollida (opcional) |
| `cleaning_frequency` | Neteges per setmana (1–7) |
| `cleaning_weekdays` | JSON array de dies de neteja [0–6] |
| `status` | ACTIVE, INTERRUPTED, RETIRED |

> **Important:** En guardar un contract es generen automàticament (via `signals.py`):
> - 1 tasca **DELIVERY** a `start_date`
> - 1 tasca **PICKUP** a `end_date` (si existeix)

---

### ServiceTask (Tasca de Servei)

| Camp | Descripció |
|------|-----------|
| `task_type` | DELIVERY, CLEANING, PICKUP |
| `scheduled_date` | Data programada |
| `driver` | FK → Driver (nullable) |
| `location` | FK → Location |
| `contract` | FK → Contract |
| `is_cancelled` | Boolean |
| `suggested_vehicle_size` | Talla recomanada (calculada) |

---

### Route (Ruta)

| Camp | Descripció |
|------|-----------|
| `driver` | FK → Driver |
| `vehicle` | FK → Vehicle |
| `date` | Data de la ruta |
| `module` | OBRA o EVENTO |

---

### RouteStop (Parada de Ruta)

Ordena les tasques dins d'una ruta.

| Camp | Descripció |
|------|-----------|
| `route` | FK → Route |
| `task` | FK → ServiceTask |
| `order` | Número d'ordre (enter) |

---

## 4. Mòduls del Admin

El panell `/admin/` és la interfície principal. Cada secció:

### Empreses
Gestió de clients. Importació/exportació Excel.

### Ubicacions
Llista d'obres. Geocodificació automàtica amb Google Maps.  
Columnes: Empresa · Nom · Poble · Zona · Gàlib · Cabines.

### Conductors
Gestió de conductors i dies laborables. Badge de disponibilitat.

### Vehicles
Gestió de flota: mida i estat (Disponible / Manteniment / Retirat).

### Pedidos (Contractes)
Acords de servei.
- Botó **"Generar tasques de neteja"** per dia concret
- Badge d'alerta si `cleaning_frequency` ≠ dies seleccionats
- Llistat de tasques inline (visible, no editable des d'aquí)

### Tasques de Servei
Vista principal de despatx. Filtres acumulatius estil Excel per:
- Tipus · Data · Conductor · Empresa · Ubicació · Poble · Estat · Pendent d'assignació

### Rutes
- **Mapa** de la ruta amb reordenació drag & drop
- **Mapa del dia**: totes les rutes d'un dia en un sol mapa Google
- **Regenerar ruta**: reassigna tasques automàticament per conductor
- **Exportar**: Excel amb coordenades, cabines i comentaris

---

## 5. On modificar cada cosa

### Afegir un camp nou a un model
1. Editar `rutas/models.py` → classe corresponent
2. `python manage.py makemigrations`
3. Revisar el fitxer creat a `rutas/migrations/`
4. Push → s'aplica automàticament a staging i producció

### Canviar columnes visibles al llistat d'un mòdul
```
rutas/admin.py → classe [Model]Admin → list_display = (...)
```

### Canviar els filtres de la barra lateral
```
rutas/admin.py → classe [Model]Admin → list_filter = (...)
```

### Canviar un formulari d'edició
```
rutas/admin.py → classe [Model]Admin → fieldsets = (...)
# Per camps especials:
rutas/templates/admin/rutas/[model]/change_form.html
```

### Afegir una nova validació de negoci
```
rutas/models.py → mètode clean() del model corresponent
# Les validacions de gàlib i disponibilitat estan a ServiceTask.clean()
```

### Canviar colors o estils visuals
```
rutas/static/rutas/admin/admin_loorent_styles.css
# Color principal: #0F6B43 (verd Loorent)
```

### Canviar el comportament dels filtres desplegables Excel
```
rutas/static/rutas/admin/admin_filter_dropdown.js
```

### Canviar el header / branding del admin
```
templates/admin/base_site.html
```

### Canviar la lògica de generació automàtica de tasques
```
rutas/signals.py → funció generate_service_tasks
```

### Afegir un poble o codi postal que no detecta la zona
```
rutas/models.py → diccionari _POSTAL_ZONE_MAP (codis postals)
rutas/models.py → diccionari _TOWN_ZONE_MAP (municipis)
rutas/static/rutas/admin/location_geocode.js → objectes POSTAL_ZONE / TOWN_ZONE
```

### Canviar traduccions (ES / CA)
1. Editar `locale/es/LC_MESSAGES/django.po` i/o `locale/ca/`
2. `python compile_mo.py`
3. Push

---

## 6. Infraestructura i entorns

### Entorns

| Entorn | URL | S'actualitza |
|--------|-----|--------------|
| **Local** | http://127.0.0.1:8000 | En executar `runserver` |
| **Staging** | https://planificador.desenvolupament.sarts.dev | Automàtic en cada push a master |
| **Producció** | https://planificador.sarts.dev | Manual via botó GitHub Actions |

### Servidor AWS
- EC2 · Ubuntu · IP: `15.217.218.32`
- Connexió SSH: `ssh ubuntu@15.217.218.32`
- Staging: `/srv/planificador_rutas/`
- Producció: `/srv/planificador_rutas_prod/`

### Serveis Docker (gestionats per `docker-compose.server.yml`)

| Contenidor | Funció |
|-----------|--------|
| `db_staging` | PostgreSQL per staging |
| `db_production` | PostgreSQL per producció |
| `staging_web` | Django + Gunicorn (staging, porta 8000 interna) |
| `production_web` | Django + Gunicorn (producció, porta 8000 interna) |
| `nginx_proxy` | Nginx · ports 80/443 · proxy invers SSL |
| `certbot` | Renovació certificats SSL automàtica (cada 12h) |
| `db_sync` | Cron dissabtes 02:00 (clona prod → staging) |

### Fitxers de configuració al servidor *(NO estan al git)*

| Fitxer | Contingut |
|--------|-----------|
| `/srv/planificador_rutas/.env.server` | Credencials de BD (staging + producció) |
| `/srv/planificador_rutas/.env.staging` | Config Django staging |
| `/srv/planificador_rutas_prod/.env.production` | Config Django producció |

### Variables d'entorn importants

| Variable | Descripció |
|----------|-----------|
| `DJANGO_SECRET_KEY` | Clau secreta (mínim 50 caràcters) |
| `DJANGO_DEBUG` | `False` en staging i producció |
| `DJANGO_ALLOWED_HOSTS` | Domini del servidor |
| `DB_NAME / DB_USER / DB_PASSWORD` | Credencials de BD |
| `DB_HOST` | `db_staging` o `db_production` (nom del contenidor) |
| `GOOGLE_MAPS_API_KEY` | API Key de Google Maps |

### Flux de versions

```
push a master
    │
    ▼
GitHub Actions (deploy-staging.yml)
    ├── Llegeix VERSION (ex: 0.1.5)
    ├── Suma +1 al patch → 0.1.6
    ├── Fa commit "v0.1.6 [skip ci]" + tag git v0.1.6
    ├── Push a master
    └── SSH al servidor → rebuild staging_web

Quan vols publicar a producció:
    GitHub → Actions → "Deploy · Production" → Run workflow → escriu "0.1.6"
    └── SSH al servidor → checkout v0.1.6 a /srv/planificador_rutas_prod → rebuild production_web
```

---

## 7. Operacions habituals al servidor

### Veure estat de tots els serveis
```bash
sudo docker compose --env-file .env.server -f docker-compose.server.yml ps
```

### Veure logs d'un servei
```bash
sudo docker logs staging_web --tail 50
sudo docker logs production_web --tail 50
sudo docker logs nginx_proxy --tail 30
```

### Reiniciar un servei
```bash
sudo docker compose --env-file .env.server -f docker-compose.server.yml restart staging_web
```

### Crear un superusuari
```bash
sudo docker exec -it production_web python manage.py createsuperuser
sudo docker exec -it staging_web python manage.py createsuperuser
```

### Aplicar migracions manualment
```bash
sudo docker exec staging_web python manage.py migrate
sudo docker exec production_web python manage.py migrate
```

### Sincronitzar BD producció → staging manualment
```bash
sudo docker exec db_sync sh /sync/db_sync.sh
# Des del PC local (sense connectar-se al servidor):
ssh ubuntu@15.217.218.32 "sudo docker exec db_sync sh /sync/db_sync.sh"
```

### Veure log de l'última sincronització
```bash
sudo docker exec db_sync cat /var/log/db_sync.log
```

### Renovar certificat SSL manualment
```bash
sudo docker exec certbot certbot renew
sudo docker exec nginx_proxy nginx -s reload
```

### Generar una secret key segura
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Posada en marxa en local
```bash
# 1. Activar entorn virtual
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# 2. Instal·lar dependències
pip install -r requirements.txt

# 3. Crear fitxer .env a l'arrel (veure .env.server.example com a referència)

# 4. Aplicar migracions
python manage.py migrate

# 5. Crear superusuari
python manage.py createsuperuser

# 6. Arrancar
python manage.py runserver
```

---

## 8. Regles de negoci fixades

Codificades a `ServiceTask.clean()` — **no canviar sense analitzar l'impacte**.

| Regla | Descripció |
|-------|-----------|
| **Gàlib** | El vehicle no pot superar `location.max_vehicle_size` en tasques CLEANING |
| **Entregues/Recollides** | Només vehicles `LARGE` per DELIVERY i PICKUP |
| **Disponibilitat conductor** | El conductor ha de tenir aquell dia com a laborable i sense indisponibilitat activa |
| **Disponibilitat vehicle** | El vehicle ha d'estar en estat `AVAILABLE` |
| **Rang temporal** | La data de la tasca ha de caure dins el període del contracte |
| **No superposició** | No es pot crear una CLEANING el mateix dia que una DELIVERY o PICKUP del mateix contracte |

---

## 9. Referència tècnica

### Importació / Exportació Excel

Cada model suporta càrrega massiva. Flux:
1. Descarregar la **plantilla Excel** (botó al llistat)
2. Omplir les dades seguint el format (fila d'exemple inclosa)
3. Carregar des del botó **"Cargar Excel"**

Els registres existents s'**ometen** (no es dupliquen). Els errors es mostren per fila.

### Exportació del parte diari (Tasques de Servei)

Columnes del Excel exportat:

| Columna | Contingut |
|---------|-----------|
| CLIENTE | Nom de l'empresa |
| POBLACION | Població (majúscules) |
| ID EXTERNO | Nom de la ubicació |
| DIRECCION | Coordenades `lat, lon` |
| LIMPIEZA | `S` (setmanal) o fracció (ex: `2/3`) |
| UNIDADES | Nombre de cabines |
| COMENTARIOS | Comentari o `EO`/`RE` per entrega/recollida |
| PERSONA DE REF. | Contacte a l'obra |
| TELÉFONO | Telèfon de contacte |
| EMAIL | Email de l'empresa |

### Geocodificació Google Maps

El formulari d'ubicació té un cercador d'adreça integrat.  
En seleccionar un resultat s'emplenen automàticament: `address`, `lat/lng`, `town`, `postal_code`, `zone`.

**APIs de Google necessàries:** Maps JavaScript API · Places API · Geocoding API

### Senyals Django (`signals.py`)

`generate_service_tasks` s'executa amb `post_save` al crear un `Contract`:
- Crea 1 tasca `DELIVERY` a `start_date`
- Crea 1 tasca `PICKUP` a `end_date` (si existeix)
- Assigna `location.default_driver` a totes dues

### Mòduls OBRA / EVENTO

L'aplicació filtra el contingut per mòdul (guardat a la sessió).  
Els superusuaris veuen tots els mòduls. Els usuaris normals, només el seu grup.  
Canviar el grup d'un usuari: `Admin → Auth → Users → [usuari] → Groups`.
