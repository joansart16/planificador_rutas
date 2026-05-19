"""
seed_demo — Genera un joc de dades de prova per al planificador LooRent.

Crea:
  · 7 empreses  ·  3 conductors  ·  4 vehicles
  · 21 ubicacions a Mallorca (amb coordenades reals)
  · 20 contractes (pressupost 26PC00001…26PC00020)
  · Tasques LIMPIEZA per la setmana del 11-15 maig 2026
  · 2 rutes per avui (15 maig 2026): Ruta Nord i Ruta Sud

Ús:
  python manage.py seed_demo            # crea sense esborrar
  python manage.py seed_demo --reset    # esborra tot i recomença
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from rutas.models import (
    Company, Contract, Driver, DriverUnavailability, Location,
    Route, RouteStop, ServiceTask, Vehicle,
)

TODAY   = date(2026, 5, 15)   # Divendres
MON_WK  = date(2026, 5, 11)   # Dilluns de la mateixa setmana
PREV_FRI = date(2026, 5, 8)   # Divendres anterior (per historial)

# ── Dades de referència ───────────────────────────────────────────────────────

_COMPANIES = [
    ('Construccions Balear SL',    'info@construccionsbalear.com'),
    ('Reformes Llevant SA',         'contacte@reformesllevant.com'),
    ('Grup Immobiliari Tramuntana', 'info@tramuntana-im.com'),
    ('Obres i Serveis Migjorn SL',  'obres@migjorn.com'),
    ('Constructora Raiguer SA',     'info@raiguer.com'),
    ('Esdeveniments Illes SL',      'events@illes.com'),
    ('Fires i Festes Palma SA',     'info@firespalma.com'),
]

_DRIVERS = [
    ('Miquel Ferrer Rosselló', [0, 1, 2, 3, 4]),
    ('Joan Tomàs Mas',          [0, 1, 2, 3, 4]),
    ('Pere Moll Riera',         [0, 1, 2, 3, 4, 5]),
]

_VEHICLES = [
    # (nom, matrícula, mida)
    ('Pickup 1',    'PM-1234-AB', Vehicle.Size.PICKUP),
    ('Pickup 2',    'PM-5678-CD', Vehicle.Size.PICKUP),
    ('Camió Petit', 'PM-9012-EF', Vehicle.Size.SMALL),
    ('Camió Gran',  'PM-3456-GH', Vehicle.Size.LARGE),
]

# driver_key: nom curt del conductor per defecte
_LOCATIONS = [
    # ── PALMA ─────────────────────────────────────────────────────────────────
    dict(name='Obra Can Bauzà',
         company='Construccions Balear SL',
         address='Carrer de Sant Miquel, 12', town='Palma', municipality='Palma',
         postal_code='07002', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=2,
         coords_cabin='39.574212, 2.652341', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    dict(name='Reforma Via Roma',
         company='Reformes Llevant SA',
         address='Avinguda de Gabriel Alomar, 8', town='Palma', municipality='Palma',
         postal_code='07006', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=1,
         coords_cabin='39.567821, 2.654210', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    dict(name='Edifici Carrer Manacor',
         company='Construccions Balear SL',
         address='Carrer de Manacor, 54', town='Palma', municipality='Palma',
         postal_code='07006', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=3,
         coords_cabin='39.571123, 2.655678', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    # ── TRAMUNTANA ────────────────────────────────────────────────────────────
    dict(name='Xalet Son Ferrutx',
         company='Grup Immobiliari Tramuntana',
         address='Carretera Andratx km 3', town='Calvià', municipality='Calvià',
         postal_code='07184', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=2,
         coords_cabin='39.552143, 2.534123', coords_entrance='39.553021, 2.532654',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name="Cases Port d'Andratx",
         company='Grup Immobiliari Tramuntana',
         address="Camí del Port, 18", town="Port d'Andratx", municipality='Andratx',
         postal_code='07157', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=1,
         coords_cabin='39.538412, 2.386732', coords_entrance='',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name='Finca Ses Vinyes',
         company='Obres i Serveis Migjorn SL',
         address='Camí Vell de Sóller, km 2', town='Bunyola', municipality='Bunyola',
         postal_code='07110', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=2,
         coords_cabin='39.683712, 2.723145', coords_entrance='39.684512, 2.721234',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name='Hotel Formentor',
         company='Esdeveniments Illes SL',
         address='Carretera Formentor km 15', town='Pollença', municipality='Pollença',
         postal_code='07460', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=4,
         coords_cabin='39.913312, 3.127432', coords_entrance='',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name='Urbanització Illetes',
         company='Construccions Balear SL',
         address='Carrer del Mirador, 3', town='Illetes', municipality='Calvià',
         postal_code='07181', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=1,
         coords_cabin='39.534723, 2.616812', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    # ── RAIGUER ───────────────────────────────────────────────────────────────
    dict(name='Polígon Industrial Inca',
         company='Constructora Raiguer SA',
         address='Gran Via de Colom, 28', town='Inca', municipality='Inca',
         postal_code='07300', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=3,
         coords_cabin='39.719512, 2.911234', coords_entrance='',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name='Obra Can Arabí',
         company='Constructora Raiguer SA',
         address="Camí de Can Arabí, s/n", town='Binissalem', municipality='Binissalem',
         postal_code='07350', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=2,
         coords_cabin='39.701023, 2.845123', coords_entrance='39.702145, 2.843456',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name='Nau Industrial Marratxí',
         company='Construccions Balear SL',
         address="Polígon Marratxí, Carrer Cerdà, 4", town='Marratxí', municipality='Marratxí',
         postal_code='07141', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=2,
         coords_cabin='39.634212, 2.762345', coords_entrance='',
         driver_key='Miquel Ferrer Rosselló'),
    dict(name="Xalet Port d'Alcúdia",
         company='Grup Immobiliari Tramuntana',
         address="Carrer dels Mossons, 12", town="Port d'Alcúdia", municipality='Alcúdia',
         postal_code='07420', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=1,
         coords_cabin='39.853312, 3.131023', coords_entrance='',
         driver_key='Miquel Ferrer Rosselló'),
    # ── PLA ───────────────────────────────────────────────────────────────────
    dict(name='Finca Montuïri',
         company='Reformes Llevant SA',
         address="Camí des Molins, 5", town='Montuïri', municipality='Montuïri',
         postal_code='07230', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=2,
         coords_cabin='39.566312, 3.001923', coords_entrance='39.567456, 2.999812',
         driver_key='Joan Tomàs Mas'),
    dict(name='Cases de Petra',
         company='Reformes Llevant SA',
         address="Carrer de l'Àngel, 22", town='Petra', municipality='Petra',
         postal_code='', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=1,
         coords_cabin='39.604512, 3.103423', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    dict(name='Obra Sineu Centre',
         company='Constructora Raiguer SA',
         address="Plaça de l'Ajuntament, 3", town='Sineu', municipality='Sineu',
         postal_code='', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=1,
         coords_cabin='39.644312, 3.014523', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    # ── MIGJORN ───────────────────────────────────────────────────────────────
    dict(name='Polígon Llucmajor',
         company='Obres i Serveis Migjorn SL',
         address="Carrer de les Roses, 8", town='Llucmajor', municipality='Llucmajor',
         postal_code='07620', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=3,
         coords_cabin='39.487312, 2.893423', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    dict(name='Xalet Ses Salines',
         company='Grup Immobiliari Tramuntana',
         address="Camí de sa Vall, 14", town='Ses Salines', municipality='Ses Salines',
         postal_code='07640', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=2,
         coords_cabin='39.348912, 3.047123', coords_entrance='39.350234, 3.045678',
         driver_key='Joan Tomàs Mas'),
    dict(name='Resort Santanyí',
         company='Esdeveniments Illes SL',
         address="Carrer de Ponent, 21", town='Santanyí', municipality='Santanyí',
         postal_code='07660', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=4,
         coords_cabin='39.352312, 3.128234', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    # ── LLEVANT ───────────────────────────────────────────────────────────────
    dict(name='Obra Manacor Nord',
         company='Reformes Llevant SA',
         address="Avinguda de Baix des Cos, 45", town='Manacor', municipality='Manacor',
         postal_code='07500', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=2,
         coords_cabin='39.570123, 3.207456', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
    dict(name='Finca Artà',
         company='Reformes Llevant SA',
         address="Camí de Bellpuig, s/n", town='Artà', municipality='Artà',
         postal_code='07570', max_vehicle_size=Vehicle.Size.PICKUP, cabin_count=3,
         coords_cabin='39.698234, 3.349512', coords_entrance='39.699456, 3.348023',
         driver_key='Joan Tomàs Mas'),
    dict(name='Hotel Son Servera',
         company='Esdeveniments Illes SL',
         address="Carrer de les Eres, 7", town='Son Servera', municipality='Son Servera',
         postal_code='07550', max_vehicle_size=Vehicle.Size.SMALL, cabin_count=3,
         coords_cabin='39.620812, 3.360234', coords_entrance='',
         driver_key='Joan Tomàs Mas'),
]

# (budget, loc_name, start, end_or_None, freq, cleaning_days, module, route_key)
# route_key: 'nord' | 'sud' | None  — per assignar als stops de la ruta del 15-maig
_CONTRACTS = [
    # ── 8 contractes amb neteja el DIVENDRES (dia=4) ─────────────────────────
    ('26PC00001', 'Obra Can Bauzà',          date(2026,1,15), date(2026,12,31), 1, [4],    'OBRA',   'sud'),
    ('26PC00002', 'Reforma Via Roma',          date(2026,2,1),  date(2026,10,31),2, [1,4],  'OBRA',   'sud'),
    ('26PC00003', 'Xalet Son Ferrutx',         date(2026,3,1),  date(2026,11,30),1, [4],    'OBRA',   'nord'),
    ('26PC00004', 'Finca Ses Vinyes',          date(2026,1,20), date(2026,12,31),2, [1,4],  'OBRA',   'nord'),
    ('26PC00005', 'Nau Industrial Marratxí',   date(2026,2,15), None,            1, [4],    'OBRA',   'nord'),
    ('26PC00006', 'Obra Can Arabí',            date(2026,3,15), date(2026,9,30), 2, [2,4],  'OBRA',   'nord'),
    ('26PC00007', 'Finca Montuïri',            date(2026,1,10), date(2026,12,31),1, [4],    'OBRA',   'sud'),
    ('26PC00008', 'Obra Manacor Nord',         date(2026,2,1),  date(2026,8,31), 2, [0,4],  'OBRA',   'sud'),
    # ── 12 contractes sense neteja el divendres ───────────────────────────────
    ('26PC00009', 'Edifici Carrer Manacor',    date(2026,1,5),  None,            2, [1,3],  'OBRA',   None),
    ('26PC00010', "Cases Port d'Andratx",      date(2026,2,1),  date(2026,10,31),1, [3],    'OBRA',   None),
    ('26PC00011', 'Hotel Formentor',           date(2026,4,1),  date(2026,10,15),2, [0,3],  'EVENTO', None),
    ('26PC00012', 'Urbanització Illetes',      date(2026,3,1),  date(2026,11,30),1, [2],    'OBRA',   None),
    ('26PC00013', 'Polígon Industrial Inca',   date(2026,1,15), None,            1, [0],    'OBRA',   None),
    ('26PC00014', "Xalet Port d'Alcúdia",      date(2026,3,15), date(2026,9,30), 2, [0,3],  'OBRA',   None),
    ('26PC00015', 'Cases de Petra',            date(2026,2,1),  date(2026,12,31),1, [2],    'OBRA',   None),
    ('26PC00016', 'Obra Sineu Centre',         date(2026,1,20), date(2026,7,31), 2, [0,2],  'OBRA',   None),
    ('26PC00017', 'Polígon Llucmajor',         date(2026,2,15), None,            1, [1],    'OBRA',   None),
    ('26PC00018', 'Xalet Ses Salines',         date(2026,3,1),  date(2026,11,30),2, [0,3],  'OBRA',   None),
    ('26PC00019', 'Resort Santanyí',           date(2026,4,15), date(2026,9,15), 1, [2],    'EVENTO', None),
    ('26PC00020', 'Hotel Son Servera',         date(2026,3,15), date(2026,10,31),2, [1,3],  'EVENTO', None),
]

# Ordre geogràfic de les parades dins cada ruta (NW→E/NE)
_ROUTE_STOP_ORDER = {
    'nord': ['26PC00003', '26PC00004', '26PC00005', '26PC00006'],
    #         Calvià(W)   Bunyola(NW)  Marratxí    Binissalem(E)
    'sud':  ['26PC00001', '26PC00002', '26PC00007', '26PC00008'],
    #         Palma        Palma        Montuïri     Manacor(E)
}


class Command(BaseCommand):
    help = 'Genera dades de prova per a demo del planificador LooRent.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Esborra TOTES les dades existents abans de crear-ne de noves.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self._reset_all()

        self.stdout.write('[1/6] Empreses...')
        companies = self._create_companies()

        self.stdout.write('[2/6] Conductors...')
        drivers = self._create_drivers()

        self.stdout.write('[3/6] Vehicles...')
        vehicles = self._create_vehicles()

        self.stdout.write('[4/6] Ubicacions...')
        locations = self._create_locations(companies, drivers)

        self.stdout.write('[5/6] Contractes + ENTREGA/RECOGIDA...')
        contracts = self._create_contracts(locations)

        self.stdout.write('[5b]  Tasques LIMPIEZA (setmana actual + anterior)...')
        self._create_limpiezas(contracts)

        self.stdout.write('[6/6] Rutes del 15-maig-2026...')
        self._create_routes(drivers, vehicles, contracts)

        total_tasks = ServiceTask.objects.filter(
            task_type=ServiceTask.TaskType.LIMPIEZA,
            scheduled_date=TODAY,
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f'\nFet!\n'
            f'   {len(companies)} empreses  |  {len(drivers)} conductors  |  {len(vehicles)} vehicles\n'
            f'   {len(locations)} ubicacions  |  {len(contracts)} contractes\n'
            f'   {total_tasks} LIMPIEZA programades per avui ({TODAY})\n'
        ))

    # ── Reset ─────────────────────────────────────────────────────────────────

    def _reset_all(self):
        self.stdout.write('[RESET] Esborrant dades existents...')
        RouteStop.objects.all().delete()
        Route.objects.all().delete()
        ServiceTask.objects.all().delete()
        Contract.objects.all().delete()
        Location.objects.all().delete()
        Company.objects.all().delete()
        DriverUnavailability.objects.all().delete()
        Driver.objects.all().delete()
        Vehicle.objects.all().delete()

    # ── Creators ──────────────────────────────────────────────────────────────

    def _create_companies(self):
        out = {}
        for name, email in _COMPANIES:
            obj, _ = Company.objects.get_or_create(name=name, defaults={'email': email})
            out[name] = obj
        return out

    def _create_drivers(self):
        out = {}
        for name, days in _DRIVERS:
            obj, _ = Driver.objects.get_or_create(
                name=name, defaults={'working_days': days}
            )
            out[name] = obj
        return out

    def _create_vehicles(self):
        out = {}
        for name, plate, size in _VEHICLES:
            obj, _ = Vehicle.objects.get_or_create(
                license_plate=plate,
                defaults={'name': name, 'size': size, 'status': Vehicle.Status.AVAILABLE},
            )
            out[name] = obj
        return out

    def _create_locations(self, companies, drivers):
        out = {}
        for row in _LOCATIONS:
            row = dict(row)
            driver_key = row.pop('driver_key')
            company_name = row.pop('company')
            row['company'] = companies[company_name]
            row['default_driver'] = drivers.get(driver_key)
            name = row['name']
            existing = Location.objects.filter(name=name).first()
            if existing:
                out[name] = existing
                continue
            obj = Location(**row)
            obj.save()
            out[name] = obj
        return out

    def _create_contracts(self, locations):
        out = {}
        for budget, loc_name, start, end, freq, days, module, route_key in _CONTRACTS:
            if Contract.objects.filter(budget_number=budget).exists():
                out[budget] = Contract.objects.get(budget_number=budget)
                continue
            location = locations.get(loc_name)
            if not location:
                self.stdout.write(self.style.WARNING(f'  ⚠ Ubicació no trobada: {loc_name}'))
                continue
            contract = Contract.objects.create(
                budget_number=budget,
                location=location,
                start_date=start,
                end_date=end,
                cleaning_frequency=freq,
                cleaning_weekdays=days,
                module=module,
                status=Contract.Status.ACTIVE,
            )
            out[budget] = contract
        return out

    def _create_limpiezas(self, contracts):
        """Genera LIMPIEZA per la setmana actual i el divendres anterior."""
        dates_to_generate = []
        # Setmana actual: dill 11 → div 15
        for offset in range(5):
            dates_to_generate.append(MON_WK + timedelta(days=offset))
        # Divendres anterior (historial)
        dates_to_generate.append(PREV_FRI)

        for budget, loc_name, start, end, freq, days, module, route_key in _CONTRACTS:
            contract = contracts.get(budget)
            if not contract:
                continue
            location = contract.location
            for task_date in dates_to_generate:
                if task_date.weekday() not in days:
                    continue
                if task_date < start:
                    continue
                if end and task_date > end:
                    continue
                if ServiceTask.objects.filter(
                    contract=contract,
                    task_type=ServiceTask.TaskType.LIMPIEZA,
                    scheduled_date=task_date,
                ).exists():
                    continue
                ServiceTask.objects.create(
                    task_type=ServiceTask.TaskType.LIMPIEZA,
                    scheduled_date=task_date,
                    location=location,
                    contract=contract,
                    driver=location.default_driver,
                    vehicle=None,
                    suggested_vehicle_size=location.max_vehicle_size,
                )

    def _create_routes(self, drivers, vehicles, contracts):
        routes_def = [
            ('Ruta Nord', 'Miquel Ferrer Rosselló', 'Pickup 1',  'OBRA', 'nord'),
            ('Ruta Sud',  'Joan Tomàs Mas',          'Pickup 2',  'OBRA', 'sud'),
        ]
        for name, driver_name, vehicle_name, module, route_key in routes_def:
            route, created = Route.objects.get_or_create(
                date=TODAY, name=name, module=module,
                defaults={
                    'driver':  drivers.get(driver_name),
                    'vehicle': vehicles.get(vehicle_name),
                },
            )
            if not created:
                continue

            budgets_ordered = _ROUTE_STOP_ORDER[route_key]
            for order, budget in enumerate(budgets_ordered, start=1):
                contract = contracts.get(budget)
                if not contract:
                    continue
                task = ServiceTask.objects.filter(
                    contract=contract,
                    task_type=ServiceTask.TaskType.LIMPIEZA,
                    scheduled_date=TODAY,
                ).first()
                if not task:
                    continue
                RouteStop.objects.get_or_create(
                    route=route, task=task,
                    defaults={'order': order},
                )
            self.stdout.write(f'   OK {name}: {route.stops.count()} parades')
