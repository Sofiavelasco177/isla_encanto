"""
Seeder de platos del restaurante.

Úsalo después de ejecutar scripts/init_db.py.

PowerShell (Windows):

# activar venv si aplica
# .\venv\Scripts\Activate.ps1
python scripts/init_db.py
python scripts/seed_platos.py
"""

import sys, os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..'))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from run import app, db
from models.baseDatos import PlatoRestaurante

SAMPLES = [
    # Entradas
    dict(nombre="Ceviche de Camarón", categoria="Entradas", precio=28000, icono="🦐", descripcion="Clásico peruano con leche de tigre y maíz chulpe."),
    dict(nombre="Bruschetta Clásica", categoria="Entradas", precio=18000, icono="🍞", descripcion="Pan tostado con tomate, albahaca y aceite de oliva."),
    # Principales
    dict(nombre="Lomo Saltado", categoria="Principales", precio=42000, icono="🥩", descripcion="Salteado de res con papas fritas y arroz."),
    dict(nombre="Salmón a la Plancha", categoria="Principales", precio=48000, icono="🐟", descripcion="Salmón fresco con mantequilla de limón y hierbas."),
    # Postres
    dict(nombre="Cheesecake de Maracuyá", categoria="Postres", precio=22000, icono="🍰", descripcion="Cremoso, con coulis de maracuyá."),
    dict(nombre="Brownie con Helado", categoria="Postres", precio=20000, icono="🍫", descripcion="Brownie tibio con bola de vainilla."),
    # Bebidas
    dict(nombre="Limonada de Coco", categoria="Bebidas", precio=12000, icono="🥥", descripcion="Refrescante y cremosa."),
    dict(nombre="Café Espresso", categoria="Bebidas", precio=8000, icono="☕", descripcion="Tostado medio, intenso."),
]


def ensure_orders(session):
    # Asignar 'orden' incremental por categoría cuando esté vacío
    from collections import defaultdict
    buckets = defaultdict(list)
    for p in session.query(PlatoRestaurante).order_by(PlatoRestaurante.categoria.asc(), PlatoRestaurante.id.asc()).all():
        buckets[p.categoria].append(p)
    for cat, items in buckets.items():
        needs = False
        current_max = 0
        for p in items:
            current_max = max(current_max, p.orden or 0)
            if not p.orden:
                needs = True
        if needs:
            order = 1
            for p in items:
                p.orden = order
                order += 1


def main():
    with app.app_context():
        count = PlatoRestaurante.query.count()
        if count == 0:
            # Insertar muestras con orden por categoría
            from collections import defaultdict
            next_order = defaultdict(int)
            for d in SAMPLES:
                cat = d.get('categoria') or 'Otros'
                next_order[cat] += 1
                pr = PlatoRestaurante(
                    nombre=d['nombre'],
                    categoria=cat,
                    precio=float(d['precio']),
                    descripcion=d.get('descripcion'),
                    icono=d.get('icono'),
                    orden=next_order[cat],
                    activo=True,
                )
                db.session.add(pr)
            db.session.commit()
            print(f"✔ Insertados {len(SAMPLES)} platos de ejemplo")
        else:
            print(f"Ya existen {count} platos; no se insertó nada nuevo.")
            ensure_orders(db.session)
            db.session.commit()
            print("✔ Orden normalizado por categoría")


if __name__ == '__main__':
    main()
