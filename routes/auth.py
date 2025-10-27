from flask import Blueprint, request, redirect, url_for, flash, session, current_app
from models.baseDatos import db, Usuario
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__)

# ---------------- GOOGLE LOGIN ---------------- #

@auth_bp.route('/google-login')
def google_login():
    # Propagar `next` para volver post-login
    next_param = request.args.get('next')
    oauth = current_app.config.get('OAUTH')
    if oauth is None:
        # Modo desarrollo (fake login si está activado)
        if current_app.config.get('ENABLE_DEV_GOOGLE'):
            return redirect(url_for('auth.google_dev_login', next=next_param))
        flash('Google OAuth no está configurado.')
        return redirect(url_for('registro.login', next=next_param))

    try:
        # Respetar esquema preferido (https en prod) si está configurado
        scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
        redirect_uri = url_for('auth.google_authorize', _external=True, _scheme=scheme, next=next_param)
        current_app.logger.info(f"Iniciando login con Google. redirect_uri={redirect_uri}")
        return oauth.google.authorize_redirect(redirect_uri)
    except Exception as e:
        current_app.logger.exception(f'Error en Google login: {e}')
        # Si falla, usar modo desarrollo
        if current_app.config.get('ENABLE_DEV_GOOGLE'):
            return redirect(url_for('auth.google_dev_login', next=next_param))
        flash('Error al iniciar sesión con Google. Intenta con usuario y contraseña.')
        return redirect(url_for('registro.login', next=next_param))


@auth_bp.route('/google_authorize')
def google_authorize():
    next_param = request.args.get('next')
    oauth = current_app.config.get('OAUTH')
    if oauth is None:
        flash('Google OAuth no está configurado.')
        return redirect(url_for('registro.login', next=next_param))

    # Obtener token y datos del usuario desde Google
    try:
        token = oauth.google.authorize_access_token()
        current_app.logger.info('Token de Google recibido correctamente')
        user_info = oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
        current_app.logger.info(f"Usuario Google: email={user_info.get('email')}")
    except Exception as e:
        current_app.logger.exception(f'Error al autorizar con Google: {e}')
        if current_app.config.get('ENABLE_DEV_GOOGLE'):
            return redirect(url_for('auth.google_dev_login', next=next_param))
        flash('No se pudo completar el inicio de sesión con Google.')
        return redirect(url_for('registro.login', next=next_param))

    # Buscar usuario en BD por correo
    usuario = Usuario.query.filter_by(correo=user_info['email']).first()

    if not usuario:
        usuario = Usuario(
            usuario=user_info.get('name', 'Usuario Google'),
            correo=user_info['email'],
            contrasena=generate_password_hash('google_placeholder', method='pbkdf2:sha256'),  # 🔹 HASH válido
            direccion=None,
            fechaNacimiento=None,
            rol='usuario'
        )
        db.session.add(usuario)
        db.session.commit()

    # Guardar sesión
    session['user'] = {
        'id': usuario.idUsuario,
        'nombre': usuario.usuario,
        'correo': usuario.correo,
        'rol': usuario.rol or 'usuario'
    }

    flash(f'¡Bienvenido, {usuario.usuario}!', 'success')

    # Redirigir a next si está presente y es seguro
    try:
        from urllib.parse import urlparse
        if next_param:
            u = urlparse(next_param)
            if (not u.netloc) and (u.path.startswith('/')):
                return redirect(next_param)
    except Exception:
        pass
    if session['user']['rol'] == 'admin':
        return redirect(url_for('main.home_admin'))
    return redirect(url_for('main.home_usuario'))


@auth_bp.route('/google_dev_login')
def google_dev_login():
    next_param = request.args.get('next')
    """Simulación de login Google para desarrollo"""
    if not current_app.config.get('ENABLE_DEV_GOOGLE'):
        flash('Modo dev Google deshabilitado')
        return redirect(url_for('registro.login', next=next_param))

    user_info = {
        'email': 'dev.user@example.com',
        'name': 'Usuario Dev'
    }

    usuario = Usuario.query.filter_by(correo=user_info['email']).first()
    if not usuario:
        usuario = Usuario(
            usuario=user_info.get('name', 'Usuario Dev'),
            correo=user_info['email'],
            contrasena=generate_password_hash('google_dev_placeholder', method='pbkdf2:sha256'),  # 🔹 HASH válido
            direccion=None,
            fechaNacimiento=None,
            rol='usuario'
        )
        db.session.add(usuario)
        db.session.commit()

    session['user'] = {
        'id': usuario.idUsuario,
        'nombre': usuario.usuario,
        'correo': usuario.correo,
        'rol': getattr(usuario, 'rol', 'usuario')
    }

    flash('Inicio de sesión simulado en modo desarrollo', 'info')
    if next_param:
        try:
            from urllib.parse import urlparse
            u = urlparse(next_param)
            if (not u.netloc) and (u.path.startswith('/')):
                return redirect(next_param)
        except Exception:
            pass
    return redirect(url_for('main.home_usuario'))

@auth_bp.route('/logout')
def logout():
    """Cerrar sesión del usuario actual"""
    try:
        session.pop('user', None)
    except Exception:
        pass
    flash('Sesión cerrada', 'info')
    return redirect(url_for('registro.login'))


# ---------------- RECUPERAR CONTRASEÑA ---------------- #

@auth_bp.route('/password_recover', methods=['POST'])
def password_recover():
    correo = request.form.get('correo')
    if not correo:
        flash('Por favor ingresa un correo electrónico')
        return redirect(url_for('registro.login'))

    usuario = Usuario.query.filter_by(correo=correo).first()
    if usuario:
        flash('Si existe una cuenta con ese correo, se han enviado instrucciones a tu correo (simulado).')
    else:
        flash('No se encontró una cuenta asociada a ese correo')
    return redirect(url_for('registro.login'))
