"""
Inicializador de base de datos para Resort Encanto.

Úsalo para crear todas las tablas del modelo en la base de datos que
esté configurada en la aplicación (SQLite o MySQL).

Pasos de uso (PowerShell en Windows):
1) Opcional (solo si deseas MySQL):
   $env:DATABASE_URL = "mysql+pymysql://USUARIO:CLAVE@HOST:3306/NOMBRE_DB"
2) Ejecuta:
   python scripts/init_db.py

Esto creará/actualizará las tablas según los modelos definidos en models/baseDatos.py.
"""

import sys, os
# Asegurar que el proyecto raíz esté en sys.path para resolver 'run'
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..'))
if PROJ_ROOT not in sys.path:
    sys.path.insert(0, PROJ_ROOT)

from sqlalchemy import inspect, text

from run import app, db  # Reutilizamos la app y la configuración existentes


def main():
    with app.app_context():
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        app.logger.info(f"Inicializando base de datos en: {uri}")

        # Crear todas las tablas declaradas en los modelos
        db.create_all()
        app.logger.info("Tablas creadas/verificadas con create_all().")

        # Pequeña migración defensiva para la tabla 'usuario'
        try:
            inspector = inspect(db.engine)
            if 'usuario' in inspector.get_table_names():
                cols = [c['name'] for c in inspector.get_columns('usuario')]
                stmts = []
                if 'reset_code' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN reset_code VARCHAR(6) NULL")
                if 'reset_expire' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN reset_expire DATETIME NULL")
                # Campos agregados al modelo Usuario que pueden faltar en esquemas antiguos
                if 'telefono' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN telefono VARCHAR(20) NULL")
                if 'avatar' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN avatar VARCHAR(255) NULL")
                if 'plan_tipo' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN plan_tipo VARCHAR(50) NULL")
                if 'membresia_activa' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN membresia_activa TINYINT(1) DEFAULT 0")
                if 'membresia_expira' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN membresia_expira DATE NULL")
                if 'notif_checkin' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN notif_checkin TINYINT(1) DEFAULT 1")
                if 'notif_checkout' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN notif_checkout TINYINT(1) DEFAULT 1")
                for s in stmts:
                    try:
                        db.session.execute(text(s))
                        db.session.commit()
                        app.logger.info(f"Migración aplicada: {s}")
                    except Exception as e:
                        db.session.rollback()
                        app.logger.warning(f"No se pudo aplicar la migración '{s}': {e}")
        except Exception as e:
            app.logger.warning(f"No se pudo inspeccionar/ajustar la tabla 'usuario': {e}")

        # Migraciones defensivas para nuevaHabitacion
        try:
            inspector = inspect(db.engine)
            if 'nuevaHabitacion' in inspector.get_table_names():
                cols = [c['name'] for c in inspector.get_columns('nuevaHabitacion')]
                stmts = []
                # Nuevos campos introducidos en el modelo
                if 'plan' not in cols:
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN plan VARCHAR(20) NULL")
                if 'numero' not in cols:
                    # INTEGER en SQLite, INT en MySQL
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN numero INTEGER NULL")
                if 'caracteristicas' not in cols:
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN caracteristicas TEXT NULL")
                if 'estado' not in cols:
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'Disponible'")
                if 'cupo_personas' not in cols:
                    # INTEGER en SQLite, INT en MySQL
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN cupo_personas INTEGER NOT NULL DEFAULT 1")
                if 'imagen' not in cols:
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN imagen VARCHAR(255) NULL")
                if 'model3d' not in cols:
                    stmts.append("ALTER TABLE nuevaHabitacion ADD COLUMN model3d VARCHAR(255) NULL")
                for s in stmts:
                    try:
                        db.session.execute(text(s))
                        db.session.commit()
                        app.logger.info(f"Migración aplicada: {s}")
                    except Exception as e:
                        db.session.rollback()
                        app.logger.warning(f"No se pudo aplicar la migración '{s}': {e}")
        except Exception as e:
            app.logger.warning(f"No se pudo inspeccionar/ajustar la tabla 'nuevaHabitacion': {e}")

        print("✔ Base de datos inicializada. Si apuntaste a MySQL, revisa phpMyAdmin.")


if __name__ == "__main__":
    main()
