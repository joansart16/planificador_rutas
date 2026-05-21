from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rutas', '0023_cancelled_flag'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepotConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='LooRent — Sede', max_length=200, verbose_name='Nombre')),
                ('address', models.CharField(blank=True, default='', help_text='Rellena con el buscador de Google Maps o escribe manualmente.', max_length=255, verbose_name='Dirección')),
                ('latitude', models.FloatField(help_text='Ej: 39.679469 — pega desde Google Maps o usa el buscador.', verbose_name='Latitud')),
                ('longitude', models.FloatField(help_text='Ej: 2.834119 — pega desde Google Maps o usa el buscador.', verbose_name='Longitud')),
            ],
            options={
                'verbose_name': 'Inicio de rutas',
                'verbose_name_plural': 'Inicio de rutas',
            },
        ),
    ]
