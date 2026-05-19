# Changelog

Todas las versiones siguen [Semantic Versioning](https://semver.org/).  
Los despliegues de staging se hacen automáticamente en cada push a `master`.  
Los despliegues de producción son manuales desde GitHub Actions (workflow "Deploy · Production").

---

## [0.1.0] — 2026-05-18

### Primera versión funcional

**Infraestructura**
- Stack Docker: PostgreSQL 15, Gunicorn, Nginx, Certbot (Let's Encrypt)
- Entorno staging: https://planificador.desenvolupament.sarts.dev
- CI/CD: deploy automático a staging en cada push a `master`

**Módulo de Rutas**
- Modelo `ServiceTask` con tipos Entrega / Recogida / Mantenimiento
- Gestión de conductores, vehículos y ubicaciones
- Panel de despacho: vista de tareas del día con filtros Excel acumulativos
- Columnas: Presupuesto, Tipo, Fecha, Empresa, Ubicación, Pueblo, Conductor, Talla, Ruta, Estado
- Filtros por tipo de tarea, fecha, conductor, empresa, ubicación, pueblo, estado, pendiente de asignación
- Exportación a Excel

**Módulo de Ubicaciones**
- Geocodificación automática vía Google Maps API
- Zonificación por código postal (comarcas de Mallorca)
- Validación de gálibo (Level 1/2/3)

**Módulo de Pedidos (Contratos)**
- Estados: Activo / Interrumpido / Retirado
- Generación automática de tareas Entrega/Recogida al guardar

**UI / Admin**
- Tema verde Loorent (#0F6B43)
- Filtros dropdown al estilo Excel con Tom Select (búsqueda + acumulativo)
- Página "Regenerar Ruta" con selector de conductor mejorado

---

## [Unreleased]

_(cambios en staging pendientes de subir a producción)_
