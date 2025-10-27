from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, current_app, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from utils.extensions import db
from models.baseDatos import Usuario, MetodoPago, Reserva, Notificacion, ActividadUsuario, Factura, nuevaHabitacion
from werkzeug.security import generate_password_hash, check_password_hash

perfil_usuario_bp = Blueprint('perfil_usuario', __name__, template_folder='../templates')

def _current_user():
    uid = session.get('user', {}).get('id')
    return Usuario.query.get(uid) if uid else None

# Vista principal de perfil
@perfil_usuario_bp.route("/perfil_usuario")
def perfil():
    user = _current_user()
    if not user:
        flash('Inicia sesión para ver tu perfil', 'warning')
        return redirect(url_for('registro.login'))

    metodos = MetodoPago.query.filter_by(usuario_id=user.idUsuario).all()
    reservas = Reserva.query.filter_by(usuario_id=user.idUsuario).order_by(Reserva.check_in.desc()).all()
    notifs = Notificacion.query.filter_by(usuario_id=user.idUsuario).order_by(Notificacion.creado_en.desc()).limit(10).all()
    actividad = ActividadUsuario.query.filter_by(usuario_id=user.idUsuario).order_by(ActividadUsuario.creado_en.desc()).limit(10).all()
    facturas = Factura.query.filter_by(usuario_id=user.idUsuario).order_by(Factura.creado_en.desc()).limit(10).all()

    return render_template(
        "usuario/perfil_usuario.html",
        user=user,
        metodos=metodos,
        reservas=reservas,
        notifs=notifs,
        actividad=actividad,
        facturas=facturas,
    )

# Actualizar perfil y avatar
@perfil_usuario_bp.route("/perfil_usuario/editar", methods=["POST"])
def editar_perfil():
    user = _current_user()
    if not user:
        flash('Inicia sesión primero', 'warning')
        return redirect(url_for('registro.login'))

    user.usuario = request.form.get('usuario') or user.usuario
    user.correo = request.form.get('correo') or user.correo
    user.telefono = request.form.get('telefono') or user.telefono
    user.direccion = request.form.get('direccion') or user.direccion
    user.plan_tipo = request.form.get('plan_tipo') or user.plan_tipo
    user.membresia_activa = True if request.form.get('membresia_activa') == 'on' else False
    exp = request.form.get('membresia_expira')
    if exp:
        try:
            user.membresia_expira = datetime.strptime(exp, '%Y-%m-%d').date()
        except Exception:
            pass
    user.notif_checkin = True if request.form.get('notif_checkin') == 'on' else False
    user.notif_checkout = True if request.form.get('notif_checkout') == 'on' else False

    # Avatar
    avatar_file = request.files.get('avatar')
    if avatar_file and avatar_file.filename:
        from uuid import uuid4
        import time
        filename = secure_filename(avatar_file.filename)
        unique = f"{int(time.time())}_{uuid4().hex[:8]}_{filename}"
        dest = os.path.join(current_app.static_folder, 'img', 'avatars')
        os.makedirs(dest, exist_ok=True)
        avatar_file.save(os.path.join(dest, unique))
        user.avatar = f"img/avatars/{unique}"

    try:
        db.session.commit()
        flash('Perfil actualizado', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('perfil_usuario.perfil'))

# Métodos de pago CRUD
@perfil_usuario_bp.route('/perfil_usuario/metodo_pago/nuevo', methods=['POST'])
def mp_nuevo():
    user = _current_user()
    mp = MetodoPago(
        usuario_id=user.idUsuario,
        marca=request.form.get('marca'),
        ultimos4=request.form.get('ultimos4'),
        tipo=request.form.get('tipo'),
        exp_mes=int(request.form.get('exp_mes') or 0) or None,
        exp_anio=int(request.form.get('exp_anio') or 0) or None,
        predeterminado=(request.form.get('predeterminado') == 'on')
    )
    if mp.predeterminado:
        MetodoPago.query.filter_by(usuario_id=user.idUsuario, predeterminado=True).update({'predeterminado': False})
    db.session.add(mp)
    db.session.commit()
    flash('Método de pago agregado', 'success')
    return redirect(url_for('perfil_usuario.perfil'))

@perfil_usuario_bp.route('/perfil_usuario/metodo_pago/<int:mid>/eliminar', methods=['POST'])
def mp_eliminar(mid):
    mp = MetodoPago.query.get_or_404(mid)
    db.session.delete(mp)
    db.session.commit()
    flash('Método de pago eliminado', 'warning')
    return redirect(url_for('perfil_usuario.perfil'))

@perfil_usuario_bp.route('/perfil_usuario/metodo_pago/<int:mid>/predeterminado', methods=['POST'])
def mp_predeterminado(mid):
    user = _current_user()
    MetodoPago.query.filter_by(usuario_id=user.idUsuario, predeterminado=True).update({'predeterminado': False})
    mp = MetodoPago.query.get_or_404(mid)
    mp.predeterminado = True
    db.session.commit()
    flash('Método predeterminado actualizado', 'success')
    return redirect(url_for('perfil_usuario.perfil'))

# Descargar factura
@perfil_usuario_bp.route('/perfil_usuario/factura/<int:fid>')
def descargar_factura(fid):
    fac = Factura.query.get_or_404(fid)
    # Si file_path es relativo a static
    if not os.path.isabs(fac.file_path):
        dirpath = current_app.static_folder
        filename = fac.file_path.replace('\\', '/').split('/')[-1]
        subdir = fac.file_path.replace(filename, '').strip('/\\')
        full_dir = os.path.join(dirpath, subdir)
        return send_from_directory(full_dir, filename, as_attachment=True)
    # Si es absoluto
    base = os.path.dirname(fac.file_path)
    fname = os.path.basename(fac.file_path)
    return send_from_directory(base, fname, as_attachment=True)

# =====================
# Configuración rápida (AJAX): notificaciones
# =====================
@perfil_usuario_bp.route('/perfil_usuario/notif', methods=['POST'])
def update_notif():
    user = _current_user()
    if not user:
        return jsonify({'ok': False, 'error': 'not_authenticated'}), 401

    # Aceptar JSON o form-data
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    field = (data.get('field') or '').strip()
    value_raw = data.get('value')
    value = True if str(value_raw).lower() in ('1', 'true', 'on', 'yes') else False

    if field not in ('notif_checkin', 'notif_checkout'):
        return jsonify({'ok': False, 'error': 'invalid_field'}), 400

    try:
        setattr(user, field, value)
        db.session.commit()
        return jsonify({'ok': True, 'field': field, 'value': value})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# =====================
# Cambio de contraseña
# =====================
@perfil_usuario_bp.route('/perfil_usuario/cambiar_password', methods=['POST'])
def cambiar_password():
    user = _current_user()
    if not user:
        flash('Inicia sesión para continuar', 'warning')
        return redirect(url_for('registro.login'))

    actual = request.form.get('password_actual') or ''
    nueva = request.form.get('password_nueva') or ''
    confirm = request.form.get('password_confirmar') or ''

    if not actual or not nueva or not confirm:
        flash('Completa todos los campos de contraseña', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    if nueva != confirm:
        flash('La nueva contraseña y su confirmación no coinciden', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    if len(nueva) < 6:
        flash('La nueva contraseña debe tener al menos 6 caracteres', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    # Validar contraseña actual (soporta casos legacy sin hash)
    valid_actual = False
    try:
        valid_actual = check_password_hash(user.contrasena, actual)
    except Exception:
        # Si no es un hash válido, comparar en claro
        valid_actual = (user.contrasena == actual)

    if not valid_actual:
        flash('La contraseña actual no es correcta', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    try:
        user.contrasena = generate_password_hash(nueva, method='pbkdf2:sha256')
        db.session.commit()
        flash('Contraseña actualizada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error actualizando contraseña: {e}', 'danger')

    return redirect(url_for('perfil_usuario.perfil'))

# =====================
# Nuevas rutas para el diseño moderno
# =====================
@perfil_usuario_bp.route('/perfil_usuario/cambiar_contrasena', methods=['POST'])
def cambiar_contrasena():
    user = _current_user()
    if not user:
        flash('Inicia sesión para continuar', 'warning')
        return redirect(url_for('registro.login'))

    actual = request.form.get('contrasena_actual') or ''
    nueva = request.form.get('nueva_contrasena') or ''
    confirm = request.form.get('confirmar_contrasena') or ''

    if not actual or not nueva or not confirm:
        flash('Completa todos los campos de contraseña', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    if nueva != confirm:
        flash('La nueva contraseña y su confirmación no coinciden', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    if len(nueva) < 6:
        flash('La nueva contraseña debe tener al menos 6 caracteres', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    # Validar contraseña actual (soporta casos legacy sin hash)
    valid_actual = False
    try:
        valid_actual = check_password_hash(user.contrasena, actual)
    except Exception:
        # Si no es un hash válido, comparar en claro
        valid_actual = (user.contrasena == actual)

    if not valid_actual:
        flash('La contraseña actual no es correcta', 'danger')
        return redirect(url_for('perfil_usuario.perfil'))

    try:
        user.contrasena = generate_password_hash(nueva, method='pbkdf2:sha256')
        db.session.commit()
        flash('Contraseña actualizada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error actualizando contraseña: {e}', 'danger')

    return redirect(url_for('perfil_usuario.perfil'))

@perfil_usuario_bp.route('/perfil_usuario/toggle_notificacion', methods=['POST'])
def toggle_notificacion():
    user = _current_user()
    if not user:
        return jsonify({'success': False, 'error': 'not_authenticated'}), 401

    data = request.get_json(silent=True) or {}
    notification_type = data.get('type')
    value = data.get('value', False)

    if notification_type == 'checkin':
        user.notif_checkin = value
    elif notification_type == 'checkout':
        user.notif_checkout = value
    else:
        return jsonify({'success': False, 'error': 'invalid_type'}), 400

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@perfil_usuario_bp.route('/perfil_usuario/cambiar_avatar', methods=['POST'])
def cambiar_avatar():
    user = _current_user()
    if not user:
        return jsonify({'success': False, 'error': 'not_authenticated'}), 401

    avatar_file = request.files.get('avatar')
    if not avatar_file or not avatar_file.filename:
        return jsonify({'success': False, 'error': 'no_file'}), 400

    try:
        from uuid import uuid4
        import time
        filename = secure_filename(avatar_file.filename)
        unique = f"{int(time.time())}_{uuid4().hex[:8]}_{filename}"
        dest = os.path.join(current_app.static_folder, 'img', 'avatars')
        os.makedirs(dest, exist_ok=True)
        avatar_file.save(os.path.join(dest, unique))
        user.avatar = f"img/avatars/{unique}"
        db.session.commit()
        return jsonify({'success': True, 'avatar_url': url_for('static', filename=user.avatar)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

