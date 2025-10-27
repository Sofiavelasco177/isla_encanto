"""Send a test recovery code to a user's registered email (uses app context)."""
import sys
from pathlib import Path
# Ensure project root is on sys.path so `run` can be imported
root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)
from run import app
from models.baseDatos import Usuario, db
from utils.mail_helper import enviar_codigo
from datetime import datetime, timedelta

def main(identifier):
    with app.app_context():
        if '@' in identifier:
            u = Usuario.query.filter_by(correo=identifier).first()
        else:
            u = Usuario.query.filter_by(usuario=identifier).first()
        if not u:
            print('Usuario no encontrado')
            return
        codigo = '999999'
        u.reset_code = codigo
        u.reset_expire = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    enviar_codigo(u.correo, codigo)
    print('Intentado enviar código a', u.correo)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: send_test_code.py <email_or_username>')
        sys.exit(1)
    main(sys.argv[1])
