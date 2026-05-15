"""
Management command: crear_usuarios

Creates the 4 operational users for Loorent Planificador:
  - Joan Obra      → operadores_obra group (OBRA module only)
  - Elina Obra     → operadores_obra group (OBRA module only)
  - Neus           → superuser (full access)
  - Silvia         → superuser (full access)

Usage:
    python manage.py crear_usuarios
"""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from rutas.models import Contract, ServiceTask, Company, Driver, Vehicle


USERS = [
    {
        'username': 'joan_obra',
        'first_name': 'Joan',
        'last_name': 'Obra',
        'password': 'Loorent2026!',
        'is_superuser': False,
        'group': 'operadores_obra',
    },
    {
        'username': 'elina_obra',
        'first_name': 'Elina',
        'last_name': 'Obra',
        'password': 'Loorent2026!',
        'is_superuser': False,
        'group': 'operadores_obra',
    },
    {
        'username': 'neus',
        'first_name': 'Neus',
        'last_name': '',
        'password': 'Loorent2026!',
        'is_superuser': True,
        'group': None,
    },
    {
        'username': 'silvia',
        'first_name': 'Silvia',
        'last_name': '',
        'password': 'Loorent2026!',
        'is_superuser': True,
        'group': None,
    },
]


class Command(BaseCommand):
    help = 'Creates the 4 operational users for Loorent Planificador'

    def handle(self, *args, **options):
        group = self._ensure_obra_group()

        for data in USERS:
            username = data['username']
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'  Skipped: {username} already exists'))
                continue

            user = User.objects.create_user(
                username=username,
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data['password'],
                is_staff=True,
                is_superuser=data['is_superuser'],
            )
            if data['group'] == 'operadores_obra':
                user.groups.add(group)

            self.stdout.write(self.style.SUCCESS(
                f'  Created: {username} ({"superuser" if data["is_superuser"] else "operadores_obra"})'
            ))

        self.stdout.write(self.style.SUCCESS('Done. Change passwords via /admin/auth/user/.'))

    def _ensure_obra_group(self) -> Group:
        group, created = Group.objects.get_or_create(name='operadores_obra')
        if created:
            self._assign_obra_permissions(group)
            self.stdout.write(self.style.SUCCESS('  Created group: operadores_obra'))
        return group

    def _assign_obra_permissions(self, group: Group) -> None:
        models_full = [Contract, ServiceTask]
        models_view = [Company, Driver, Vehicle]

        for model in models_full:
            ct = ContentType.objects.get_for_model(model)
            for action in ('view', 'add', 'change', 'delete'):
                perm = Permission.objects.filter(content_type=ct, codename=f'{action}_{model._meta.model_name}').first()
                if perm:
                    group.permissions.add(perm)

        for model in models_view:
            ct = ContentType.objects.get_for_model(model)
            perm = Permission.objects.filter(content_type=ct, codename=f'view_{model._meta.model_name}').first()
            if perm:
                group.permissions.add(perm)
