"""
Señales de la app rutas.

post_save en Contract → genera automáticamente las ServiceTask:
    · 1 ENTREGA  en start_date
    · 1 RECOGIDA en end_date  (solo si end_date está definida)
    · Las LIMPIEZA se generan manualmente desde el admin (vista "Generar tareas por día")

Driver se asigna desde Location.default_driver (puede cambiarse después).
Vehículo se deja en blanco para asignación manual posterior.

Reglas de sugerencia de tamaño:
    · ENTREGA / RECOGIDA → LARGE
    · LIMPIEZA           → max_vehicle_size de la Location
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='rutas.Contract')
def generate_service_tasks(sender, instance, created: bool, **kwargs) -> None:
    """Al crear un contrato genera la ENTREGA y, si hay fecha de fin, la RECOGIDA."""
    if not created:
        return

    from .models import ServiceTask, Vehicle

    contract = instance
    location = contract.location
    suggested_delivery = Vehicle.Size.LARGE
    default_driver = location.default_driver if location else None
    tasks = []

    # ── ENTREGA ──────────────────────────────────────────────────────────────
    tasks.append(ServiceTask(
        task_type=ServiceTask.TaskType.ENTREGA,
        scheduled_date=contract.start_date,
        location=location,
        contract=contract,
        driver=default_driver,
        vehicle=None,
        suggested_vehicle_size=suggested_delivery,
    ))

    # ── RECOGIDA (solo si se conoce la fecha de fin) ──────────────────────
    if contract.end_date:
        tasks.append(ServiceTask(
            task_type=ServiceTask.TaskType.RECOGIDA,
            scheduled_date=contract.end_date,
            location=location,
            contract=contract,
            driver=default_driver,
            vehicle=None,
            suggested_vehicle_size=suggested_delivery,
        ))

    ServiceTask.objects.bulk_create(tasks)

