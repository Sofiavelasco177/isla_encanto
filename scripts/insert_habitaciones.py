import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.baseDatos import db, nuevaHabitacion
from run import app

habitaciones_fijas = [
    {
        "nombre": "Habitación Básica",
        "descripcion": "Vista al jardín, cama queen size, baño privado, Wi-Fi gratuito, minibar básico.",
        "precio": 180000,
        "cupo_personas": 2,
        "estado": "Disponible",
        "imagen": "img/habitacion(1).jpg"
    },
    {
        "nombre": "Habitación Estándar",
        "descripcion": "Vista parcial al mar, cama king size, baño con ducha y bañera, Wi-Fi de alta velocidad, minibar surtido.",
        "precio": 250000,
        "cupo_personas": 2,
        "estado": "Mantenimiento",
        "imagen": "img/habitacion(2).jpg"
    },
    {
        "nombre": "Habitación Premium",
        "descripcion": "Vista al mar, cama king size premium, baño de mármol con jacuzzi, Wi-Fi VIP ultra rápido, minibar premium.",
        "precio": 320000,
        "cupo_personas": 2,
        "estado": "Ocupada",
        "imagen": "img/habitacion(3).jpg"
    },
    {
        "nombre": "Suite Familiar",
        "descripcion": "Espaciosa suite para familias, con dos ambientes, sala privada, y vistas al jardín. Capacidad para 4 personas.",
        "precio": 400000,
        "cupo_personas": 4,
        "estado": "Disponible",
        "imagen": "img/habitacion(7).jpg"
    },
    {
        "nombre": "Suite Deluxe",
        "descripcion": "Lujo y confort en una suite con vistas parciales al mar, cama king size, y baño en mármol con amenities premium.",
        "precio": 350000,
        "cupo_personas": 2,
        "estado": "Mantenimiento",
        "imagen": "img/habitacion(5).jpg"
    },
    {
        "nombre": "Villa Privada",
        "descripcion": "Villa independiente con piscina privada, jardín y servicio personalizado. Ideal para grupos o celebraciones.",
        "precio": 600000,
        "cupo_personas": 6,
        "estado": "Ocupada",
        "imagen": "img/habitacion(6).jpg"
    }
]

with app.app_context():
    # Asegurar columnas nuevas existen (si se ejecuta sin init_db)
    try:
        from sqlalchemy import inspect, text
        insp = inspect(db.engine)
        cols = [c['name'] for c in insp.get_columns('nuevaHabitacion')]
        stmts = []
        if 'plan' not in cols:
            stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN plan VARCHAR(20) NULL")
        if 'numero' not in cols:
            stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN numero INTEGER NULL")
        if 'caracteristicas' not in cols:
            stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN caracteristicas TEXT NULL")
        for s in stmts:
            try:
                db.session.execute(text(s))
                db.session.commit()
            except Exception:
                db.session.rollback()
    except Exception:
        pass

    static_dir = app.static_folder
    for h in habitaciones_fijas:
        if not nuevaHabitacion.query.filter_by(nombre=h["nombre"]).first():
            # Validar que la imagen exista; si no, usar default
            img = h["imagen"]
            import os
            img_fs = os.path.join(static_dir, img)
            if not os.path.isfile(img_fs):
                img = 'img/default.jpg'

            nueva = nuevaHabitacion(
                nombre=h["nombre"],
                descripcion=h["descripcion"],
                precio=h["precio"],
                cupo_personas=h["cupo_personas"],
                estado=h["estado"],
                imagen=img
            )
            db.session.add(nueva)
    db.session.commit()

    # ----------------- Planes Oro y Plata -----------------
    # Plan Oro: 8 habitaciones, 4.500.000 COP por noche, suite presidencial con jacuzzi y lujos
    oro_precio = 4500000
    oro_features = {
        "area_interior": [
            "Dormitorio principal con cama King Size y sábanas de alta calidad",
            "Sala de estar amplia con sofás, Smart TV y sonido envolvente",
            "Comedor privado para 4–6 personas",
            "Oficina/escritorio ejecutivo con buena iluminación",
            "Vestidor y armario de gran capacidad",
            "Baño tipo spa con jacuzzi con vista al mar, rain shower, lavamanos doble",
            "Amenities de lujo premium"
        ],
        "area_exterior": [
            "Terraza/balcón privado con vista panorámica al mar",
            "Piscina o jacuzzi privado al aire libre",
            "Camas balinesas/tumbonas exclusivas",
            "Zona lounge/comedor exterior",
            "Acceso directo a la playa (según disponibilidad)"
        ],
        "servicios": [
            "Minibar premium (vinos, champaña, snacks gourmet)",
            "Cafetera Nespresso / máquina de espresso",
            "Servicio de mayordomo/asistente personal",
            "Room service 24 horas",
            "Desayuno personalizado en la suite",
            "Decoración romántica a solicitud"
        ],
        "lujo": [
            "Diseño interior con materiales naturales",
            "Arte local / temática marina"
        ]
    }

    # Plan Plata: 12 habitaciones, 2.500.000 COP por noche, sin jacuzzi
    plata_precio = 2500000
    plata_features = {
        "area_interior": [
            "Cama Queen Size o dos dobles",
            "Ropa de cama cómoda",
            "Área de descanso con sillón",
            "TV pantalla plana con cable",
            "A/C o ventilador de techo",
            "Armario o clóset",
            "Escritorio/tocador",
            "Mini nevera / minibar básico",
            "Caja fuerte y teléfono"
        ],
        "bano": [
            "Ducha",
            "Toallas y amenities básicos",
            "Secador de cabello (opcional)"
        ],
        "area_exterior": [
            "Balcón pequeño o terraza compartida (si aplica)",
            "Vista parcial al mar o jardín",
            "Sillas de exterior o hamaca (en algunos casos)"
        ],
        "servicios": [
            "Room service limitado",
            "Limpieza diaria",
            "WiFi gratuito",
            "Desayuno incluido buffet/continental",
            "Agua embotellada de cortesía"
        ],
        "detalles": [
            "Decoración sencilla colores cálidos/tropicales",
            "Piso cerámica o madera laminada",
            "Iluminación natural y blackout"
        ]
    }

    import json

    # Crear Oro habitaciones enumeradas O-101..O-108 (numero 1..8)
    for i in range(1, 9):
        nombre = f"Suite Oro #{i:02d}"
        exists = nuevaHabitacion.query.filter_by(nombre=nombre).first()
        if not exists:
            nueva = nuevaHabitacion(
                nombre=nombre,
                plan='Oro',
                numero=i,
                descripcion="Suite Oro con jacuzzi y lujos.",
                caracteristicas=json.dumps(oro_features, ensure_ascii=False),
                precio=oro_precio,
                estado='Disponible',
                cupo_personas=2,
                imagen='img/habitacion(3).jpg'
            )
            db.session.add(nueva)

    # Crear Plata habitaciones enumeradas P-201..P-212 (numero 1..12)
    for i in range(1, 13):
        nombre = f"Habitación Plata #{i:02d}"
        exists = nuevaHabitacion.query.filter_by(nombre=nombre).first()
        if not exists:
            nueva = nuevaHabitacion(
                nombre=nombre,
                plan='Plata',
                numero=i,
                descripcion="Habitación Plata cómoda sin jacuzzi.",
                caracteristicas=json.dumps(plata_features, ensure_ascii=False),
                precio=plata_precio,
                estado='Disponible',
                cupo_personas=2,
                imagen='img/habitacion(2).jpg'
            )
            db.session.add(nueva)

    db.session.commit()
    # ----------------- Plan Bronce (20) con distribución solicitada -----------------
    # 5 habitaciones ocupación 2 con dos camas sencillas
    # 5 habitaciones ocupación 3 con tres camas sencillas
    # 10 habitaciones cama doble con ocupación de 2
    bronce_precio = 150000  # Ajustable; no se especificó precio, usamos base
    bronce_features = {
        "area_interior": [
            "1 cama doble o dos camas sencillas",
            "Ropa de cama estándar",
            "Ventilador de techo o A/C básico",
            "TV pequeña con señal local/cable limitado",
            "Mesa de noche y lámpara",
            "Clóset pequeño o perchero",
            "Mini nevera (opcional)"
        ],
        "bano": [
            "Baño privado con ducha",
            "Toallas básicas",
            "Jabón y champú sencillos",
            "Agua caliente (según disponibilidad)"
        ],
        "area_exterior": [
            "Sin balcón o ventana a jardín/pasillo",
            "Acceso a áreas comunes"
        ],
        "servicios": [
            "WiFi básico",
            "Limpieza cada 2 días o bajo solicitud",
            "Desayuno continental básico",
            "Estacionamiento compartido",
            "Recepción 12/24 horas (según categoría)"
        ],
        "detalles": [
            "Decoración sencilla (neutros/tropicales)",
            "Mobiliario funcional",
            "Piso cerámica o cemento pulido",
            "Buena ventilación natural"
        ]
    }

    import json as _json
    # 5 de 2 pax con dos camas sencillas
    for i in range(1, 6):
        nombre = f"Habitación Bronce DobleSencillas #{i:02d}"
        if not nuevaHabitacion.query.filter_by(nombre=nombre).first():
            desc = "Dos camas sencillas, ocupación 2."
            car = dict(bronce_features)
            car["layout"] = "2 camas sencillas, 2 pax"
            nueva = nuevaHabitacion(
                nombre=nombre,
                plan='Bronce',
                numero=i,
                descripcion=desc,
                caracteristicas=_json.dumps(car, ensure_ascii=False),
                precio=bronce_precio,
                estado='Disponible',
                cupo_personas=2,
                imagen='img/habitacion(1).jpg'
            )
            db.session.add(nueva)

    # 5 de 3 pax con tres camas sencillas
    for i in range(1, 6):
        nombre = f"Habitación Bronce TripleSencillas #{i:02d}"
        if not nuevaHabitacion.query.filter_by(nombre=nombre).first():
            desc = "Tres camas sencillas, ocupación 3."
            car = dict(bronce_features)
            car["layout"] = "3 camas sencillas, 3 pax"
            nueva = nuevaHabitacion(
                nombre=nombre,
                plan='Bronce',
                numero=5 + i,
                descripcion=desc,
                caracteristicas=_json.dumps(car, ensure_ascii=False),
                precio=bronce_precio,
                estado='Disponible',
                cupo_personas=3,
                imagen='img/habitacion(1).jpg'
            )
            db.session.add(nueva)

    # 10 de cama doble con ocupación 2
    for i in range(1, 11):
        nombre = f"Habitación Bronce Doble #{i:02d}"
        if not nuevaHabitacion.query.filter_by(nombre=nombre).first():
            desc = "Cama doble, ocupación 2."
            car = dict(bronce_features)
            car["layout"] = "1 cama doble, 2 pax"
            nueva = nuevaHabitacion(
                nombre=nombre,
                plan='Bronce',
                numero=10 + i,
                descripcion=desc,
                caracteristicas=_json.dumps(car, ensure_ascii=False),
                precio=bronce_precio,
                estado='Disponible',
                cupo_personas=2,
                imagen='img/habitacion(1).jpg'
            )
            db.session.add(nueva)

    db.session.commit()
    print("Habitaciones fijas + Plan Oro (8), Plata (12) y Bronce (20) registradas en la base de datos.")
