# Script rápido para probar el flujo de login usando app.test_client()
from run import app
from models.baseDatos import db, Usuario
from werkzeug.security import generate_password_hash
import traceback

USERNAME = 'sofi'
PASSWORD = 'testpass123'

with app.app_context():
    try:
        # asegurar usuario de prueba
        u = Usuario.query.filter_by(usuario=USERNAME).first()
        if not u:
            u = Usuario(usuario=USERNAME, correo='sofi@example.com', contraseña=generate_password_hash(PASSWORD))
            db.session.add(u)
            db.session.commit()
            print('Usuario creado')
        else:
            # actualizar contraseña para asegurarnos
            if hasattr(u, 'contraseña'):
                u.contraseña = generate_password_hash(PASSWORD)
            else:
                u.__dict__['contrasena'] = generate_password_hash(PASSWORD)
            db.session.commit()
            print('Usuario existente: contraseña actualizada')

        client = app.test_client()
        resp = client.post('/login', data={'usuario': USERNAME, 'contraseña': PASSWORD}, follow_redirects=False)
        print('STATUS:', resp.status_code)
        print('LOCATION:', resp.headers.get('Location'))
        # If redirect happened and follow_redirects=False, location shows target. If follow_redirects=True, we can inspect body.
    except Exception:
        traceback.print_exc()
