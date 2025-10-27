from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from urllib.parse import urlparse
from models.baseDatos import db, Usuario
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

registro_bp = Blueprint('registro', __name__)

@registro_bp.route('/login', methods=['GET', 'POST'])
def login():
    def _safe_next(target: str | None):
        if not target:
            return None
        try:
            u = urlparse(target)
            # Solo permitir rutas relativas o absolutas sin netloc externo
            if (not u.netloc) and (u.path.startswith('/')):
                return target
        except Exception:
            pass
        return None

    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        # Buscar usuario
        user = Usuario.query.filter_by(usuario=usuario).first()

        if user:
            print('DEBUG: user.rol =', user.rol)  # <-- Depuración
            try:
                # Intentar validar como hash
                if check_password_hash(user.contrasena, contrasena):
                    session['user'] = {
                        'id': user.idUsuario,
                        'nombre': user.usuario,
                        'correo': user.correo,
                        'rol': user.rol or 'usuario'
                    }
                    flash(f'¡Bienvenido, {user.usuario}!', 'success')

                    nxt = _safe_next(request.args.get('next') or request.form.get('next'))
                    if nxt:
                        return redirect(nxt)
                    return redirect(url_for('main.home_admin' if session['user']['rol']=='admin' else 'main.home_usuario'))

            except ValueError:
                # 🚨 Si falla porque no está hasheada, re-hasheamos en caliente
                if user.contrasena == contrasena:
                    user.contrasena = generate_password_hash(contrasena, method='pbkdf2:sha256')
                    db.session.commit()

                    session['user'] = {
                        'id': user.idUsuario,
                        'nombre': user.usuario,
                        'correo': user.correo,
                        'rol': user.rol or 'usuario'
                    }
                    flash(f'¡Bienvenido, {user.usuario}! (contraseña actualizada a hash)', 'success')

                    nxt = _safe_next(request.args.get('next') or request.form.get('next'))
                    if nxt:
                        return redirect(nxt)
                    return redirect(url_for('main.home_admin' if session['user']['rol']=='admin' else 'main.home_usuario'))

        flash('Usuario o contraseña incorrectos', 'danger')

    # GET o POST con error: mantener `next` para no perder el destino
    next_param = request.args.get('next')
    return render_template('home/Login.html', next=next_param)


@registro_bp.route('/register', methods=['POST'])
def register():
    usuario = request.form['usuario']
    correo = request.form['correo']
    contrasena = request.form['contrasena']
    direccion = request.form['direccion']
    fechaNacimiento = datetime.strptime(request.form['fechaNacimiento'], "%Y-%m-%d").date()

    # Verificar si el correo ya existe
    if Usuario.query.filter_by(correo=correo).first():
        flash('El correo ya está registrado. Intenta con otro.', 'danger')
        return redirect(url_for('registro.login'))

    # ✅ Encriptar la contraseña antes de guardarla
    hashed = generate_password_hash(contrasena, method='pbkdf2:sha256')

    nuevo_usuario = Usuario(
        usuario=usuario,
        correo=correo,
        contrasena=hashed,
        direccion=direccion,
        fechaNacimiento=fechaNacimiento
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
    return redirect(url_for('registro.login'))