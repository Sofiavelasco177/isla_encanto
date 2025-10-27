"""Check user by email or username using the app context."""
import sys
from pathlib import Path
# Ensure project root is on sys.path so `run` can be imported
root = str(Path(__file__).resolve().parents[1])
if root not in sys.path:
    sys.path.insert(0, root)
from run import app
from models.baseDatos import Usuario

def main(identifier):
    with app.app_context():
        if '@' in identifier:
            u = Usuario.query.filter_by(correo=identifier).first()
        else:
            u = Usuario.query.filter_by(usuario=identifier).first()
        if not u:
            print('NOT FOUND')
            return
        print('FOUND')
        print('idUsuario=', u.idUsuario)
        print('usuario=', u.usuario)
        print('correo=', u.correo)
        print('rol=', u.rol)
        print('reset_code=', u.reset_code)
        print('reset_expire=', u.reset_expire)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_user.py <email_or_username>')
        sys.exit(1)
    main(sys.argv[1])
