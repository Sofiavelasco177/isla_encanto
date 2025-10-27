from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models.baseDatos import db, Usuario, PerfilAdmin

perfil_admin_bp = Blueprint('perfil_admin', __name__, url_prefix='/admin/perfil')

@perfil_admin_bp.before_request
def _require_admin():
    user = session.get('user')
    if not user or user.get('rol') != 'admin':
        flash('Acceso restringido solo para administradores', 'warning')
        return redirect(url_for('registro.login'))


@perfil_admin_bp.route('/', methods=['GET'])
def view():
    usuario_id = session.get('user', {}).get('id')
    usuario = Usuario.query.get_or_404(usuario_id)
    perfil = PerfilAdmin.query.filter_by(usuario_id=usuario_id).first()
    return render_template('dashboard/perfil_admin.html', usuario=usuario, perfil=perfil)


@perfil_admin_bp.route('/editar', methods=['POST'])
def update():
    usuario_id = session.get('user', {}).get('id')
    if not usuario_id:
        flash('Sesión no válida', 'danger')
        return redirect(url_for('registro.login'))

    usuario = Usuario.query.get_or_404(usuario_id)
    perfil = PerfilAdmin.query.filter_by(usuario_id=usuario_id).first()
    if not perfil:
        perfil = PerfilAdmin(usuario_id=usuario_id)
        db.session.add(perfil)

    # Actualizar datos básicos del usuario
    usuario.usuario = request.form.get('usuario') or usuario.usuario
    usuario.correo = request.form.get('correo') or usuario.correo
    usuario.direccion = request.form.get('direccion') or usuario.direccion
    usuario.telefono = request.form.get('telefono') or usuario.telefono
    fnac = request.form.get('fechaNacimiento')
    if fnac:
        try:
            usuario.fechaNacimiento = datetime.strptime(fnac, '%Y-%m-%d').date()
        except Exception:
            pass

    # Subir avatar si viene
    avatar_file = request.files.get('avatar')
    if avatar_file and avatar_file.filename:
        from uuid import uuid4
        import time
        filename = secure_filename(avatar_file.filename)
        unique = f"{int(time.time())}_{uuid4().hex[:8]}_{filename}"
        img_folder = os.path.join(current_app.static_folder, 'img', 'avatars')
        os.makedirs(img_folder, exist_ok=True)
        save_path = os.path.join(img_folder, unique)
        avatar_file.save(save_path)
        # Guardar ruta relativa para url_for('static', filename=...)
        usuario.avatar = f"img/avatars/{unique}"

    # Actualizar perfil admin
    perfil.cargo = request.form.get('cargo') or perfil.cargo
    perfil.area = request.form.get('area') or perfil.area
    perfil.division = request.form.get('division') or perfil.division
    perfil.empresa = request.form.get('empresa') or perfil.empresa
    perfil.supervisor = request.form.get('supervisor') or perfil.supervisor
    perfil.suplente = request.form.get('suplente') or perfil.suplente
    perfil.tipo_contrato = request.form.get('tipo_contrato') or perfil.tipo_contrato
    fing = request.form.get('fecha_ingreso')
    if fing:
        try:
            perfil.fecha_ingreso = datetime.strptime(fing, '%Y-%m-%d').date()
        except Exception:
            pass

    try:
        db.session.commit()
        flash('Perfil actualizado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar el perfil: {e}', 'danger')

    return redirect(url_for('perfil_admin.view'))


@perfil_admin_bp.route('/eliminar', methods=['POST'])
def delete():
    usuario_id = session.get('user', {}).get('id')
    perfil = PerfilAdmin.query.filter_by(usuario_id=usuario_id).first()
    if perfil:
        try:
            db.session.delete(perfil)
            db.session.commit()
            flash('Perfil eliminado', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'No se pudo eliminar: {e}', 'danger')
    return redirect(url_for('perfil_admin.view'))
"""@admin_bp.route('/perfil_admin', methods=['GET', 'POST'])
def perfil_admin():
    # Suponiendo que el admin está logueado y su id está en session['user']['id']
    usuario_id = session.get('user', {}).get('id')
    usuario = Usuario.query.get(usuario_id)
    perfil = PerfilAdmin.query.filter_by(usuario_id=usuario_id).first()
    if request.method == 'POST':
        # Actualizar o crear perfil
        if not perfil:
            perfil = PerfilAdmin(usuario_id=usuario_id)
            db.session.add(perfil)
        perfil.cargo = request.form['cargo']
        perfil.area = request.form['area']
        perfil.division = request.form['division']
        perfil.empresa = request.form['empresa']
        perfil.supervisor = request.form['supervisor']
        perfil.suplente = request.form['suplente']
        perfil.tipo_contrato = request.form['tipo_contrato']
        perfil.fecha_ingreso = request.form['fecha_ingreso']
        db.session.commit()
        flash('Datos actualizados correctamente', 'success')
        return redirect(url_for('admin.perfil_admin'))
    return render_template('dashboard/perfil_admin.html', usuario=usuario, perfil=perfil)
    return redirect(url_for("admin.admin_restaurante"))"""