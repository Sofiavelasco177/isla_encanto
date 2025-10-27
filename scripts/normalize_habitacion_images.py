import os
from run import app
from models.baseDatos import db, nuevaHabitacion


def normalize_images():
    with app.app_context():
        static_dir = app.static_folder
        changed = 0
        total = 0
        rows = nuevaHabitacion.query.all()
        for h in rows:
            total += 1
            img = (h.imagen or '').replace('\\', '/').lstrip('/')
            if not img:
                # Sin imagen, dejar para que use default en UI
                continue

            def fs(p):
                return os.path.join(static_dir, p)

            # Si existe tal cual, nada que hacer
            if os.path.isfile(fs(img)):
                continue

            # Probar con prefijo 'img/' si faltó
            candidate = img
            if not img.startswith('img/'):
                candidate = f'img/{img}'
                if os.path.isfile(fs(candidate)):
                    h.imagen = candidate
                    changed += 1
                    continue

            # Como último recurso, usar default
            h.imagen = 'img/default.jpg'
            changed += 1

        if changed:
            db.session.commit()
        print(f"Habitaciones revisadas: {total} | Imágenes normalizadas: {changed}")


if __name__ == '__main__':
    normalize_images()
