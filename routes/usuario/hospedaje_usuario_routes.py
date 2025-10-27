from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models.baseDatos import db, nuevaHabitacion, Huesped, Reserva, ReservaDatosHospedaje
from datetime import datetime, date, timedelta
from sqlalchemy.exc import SQLAlchemyError

hospedaje_usuario_bp = Blueprint('hospedaje_usuario', __name__)

@hospedaje_usuario_bp.route('/hospedaje_usuario')
def hospedaje_usuario():
    habitaciones = nuevaHabitacion.query.order_by(nuevaHabitacion.plan.asc(), nuevaHabitacion.numero.asc()).all()
    # Agrupar por plan para la vista
    grouped = { 'Oro': [], 'Plata': [], 'Bronce': [], 'Otro': [] }
    for h in habitaciones:
        key = (h.plan or 'Otro')
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(h)
    current_year = datetime.utcnow().year
    return render_template('usuario/hospedaje_usuario.html', habitaciones=habitaciones, habitaciones_por_plan=grouped, current_year=current_year)


@hospedaje_usuario_bp.route('/reservar/<int:habitacion_id>', methods=['GET', 'POST'])
def reservar_habitacion(habitacion_id):
    habitacion = nuevaHabitacion.query.get_or_404(habitacion_id)

    if request.method == 'POST':
        # Requiere usuario logueado
        uid = session.get('user', {}).get('id')
        if not uid:
            flash('Inicia sesión para continuar con la reserva', 'warning')
            return redirect(url_for('registro.login'))

        # Validar fechas y disponibilidad antes de persistir
        try:
            check_in = datetime.strptime(request.form.get('check_in'), '%Y-%m-%d').date()
            check_out = datetime.strptime(request.form.get('check_out'), '%Y-%m-%d').date()
        except Exception:
            flash('Fechas inválidas', 'danger')
            return redirect(url_for('hospedaje_usuario.reservar_habitacion', habitacion_id=habitacion.id))

        if check_out <= check_in:
            flash('La fecha de salida debe ser posterior al check-in', 'danger')
            return redirect(url_for('hospedaje_usuario.reservar_habitacion', habitacion_id=habitacion.id))

        # Bloquear fechas si hay traslape con reservas activas/no canceladas
        if not _habitacion_disponible(habitacion.id, check_in, check_out):
            flash('La habitación no está disponible para las fechas seleccionadas. Por favor elige otras fechas.', 'warning')
            return redirect(url_for('hospedaje_usuario.reservar_habitacion', habitacion_id=habitacion.id))

        # Validar número de documento (columna es Integer actualmente)
        ndoc_raw = (request.form.get('numeroDocumento') or '').strip()
        try:
            ndoc = int(ndoc_raw)
        except Exception:
            flash('El número de documento debe ser numérico.', 'danger')
            return redirect(url_for('hospedaje_usuario.reservar_habitacion', habitacion_id=habitacion.id))

    # Guardar o reutilizar huésped en BD (evitar error de UNIQUE)
        huesped = Huesped.query.filter_by(numeroDocumento=ndoc).first()
        if huesped:
            # Actualizar datos básicos para mantenerlos al día
            huesped.nombre = request.form.get('nombre') or huesped.nombre
            huesped.tipoDocumento = request.form.get('tipoDocumento') or huesped.tipoDocumento
            huesped.telefono = request.form.get('telefono') or huesped.telefono
            huesped.correo = request.form.get('correo') or huesped.correo
            huesped.procedencia = request.form.get('procedencia') or huesped.procedencia
            huesped.nuevaHabitacion_id = habitacion.id
        else:
            huesped = Huesped(
                nombre=request.form['nombre'],
                tipoDocumento=request.form['tipoDocumento'],
                numeroDocumento=ndoc,
                telefono=request.form.get('telefono'),
                correo=request.form.get('correo'),
                procedencia=request.form.get('procedencia'),
                nuevaHabitacion_id=habitacion.id  # Usa la FK correcta
            )
            db.session.add(huesped)

        noches = max(1, (check_out - check_in).days)
        total = float(habitacion.precio or 0) * noches

        reserva = Reserva(
            usuario_id=uid,
            habitacion_id=habitacion.id,
            check_in=check_in,
            check_out=check_out,
            estado='Activa',
            total=total
        )
        db.session.add(reserva)
        db.session.flush()  # asegurar ID de reserva antes de usarlo en datos
        # También persistir datos declarados en el formulario (titular + acompañante opcional)
        datos = ReservaDatosHospedaje(
            reserva_id=reserva.id,
            nombre1=request.form.get('nombre'),
            tipo_doc1=request.form.get('tipoDocumento'),
            num_doc1=str(ndoc_raw),
            telefono1=request.form.get('telefono'),
            correo1=request.form.get('correo'),
            procedencia1=request.form.get('procedencia'),
            # acompañante (si fue diligenciado en el formulario)
            nombre2=(request.form.get('nombre2') or None),
            tipo_doc2=(request.form.get('tipoDocumento2') or None),
            num_doc2=(request.form.get('numeroDocumento2') or None),
            telefono2=(request.form.get('telefono2') or None),
            correo2=(request.form.get('correo2') or None),
            procedencia2=(request.form.get('procedencia2') or None),
        )
        db.session.add(datos)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            # Mensaje genérico; en logs quedará el detalle
            flash('No se pudo crear la reserva. Verifica tus datos e inténtalo de nuevo.', 'danger')
            # Registrar error para diagnóstico
            try:
                from flask import current_app
                current_app.logger.exception('Error guardando reserva/huésped: %s', e)
            except Exception:
                pass
            return redirect(url_for('hospedaje_usuario.reservar_habitacion', habitacion_id=habitacion.id))

    # Redirigir a checkout del proveedor configurado
        return redirect(url_for('pagos_usuario.checkout_reserva', reserva_id=reserva.id))

    return render_template('usuario/reservas.html', habitacion=habitacion)


def _habitacion_disponible(habitacion_id: int, check_in, check_out) -> bool:
    """Retorna True si no existen reservas traslapadas para la habitación en el rango dado.
    La lógica de traslape permite check-in el mismo día del check-out previo.
    """
    # Excluir reservas canceladas
    qs = Reserva.query.filter(
        Reserva.habitacion_id == habitacion_id,
        Reserva.estado != 'Cancelada'
    )
    # overlap si (nuevo_in < existente_out) y (nuevo_out > existente_in)
    qs = qs.filter(Reserva.check_in < check_out, Reserva.check_out > check_in)
    return qs.count() == 0


@hospedaje_usuario_bp.route('/disponibilidad/<int:habitacion_id>')
def disponibilidad_habitacion(habitacion_id):
    """Endpoint simple para consultar disponibilidad por fechas."""
    habitacion = nuevaHabitacion.query.get_or_404(habitacion_id)
    sin = request.args.get('check_in')
    sout = request.args.get('check_out')
    try:
        d_in = datetime.strptime(sin, '%Y-%m-%d').date() if sin else None
        d_out = datetime.strptime(sout, '%Y-%m-%d').date() if sout else None
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_dates'}), 400

    if not d_in or not d_out or d_out <= d_in:
        return jsonify({'ok': False, 'error': 'invalid_range'}), 400

    available = _habitacion_disponible(habitacion.id, d_in, d_out)
    return jsonify({'ok': True, 'available': available})


@hospedaje_usuario_bp.route('/calendar/<int:habitacion_id>')
def calendario_habitacion(habitacion_id: int):
    """Devuelve el cronograma anual día a día para una habitación.
    Response JSON shape:
    {
      ok: true,
      habitacion_id: N,
      year: 2025,
      days: [{date:"YYYY-MM-DD", status:"disponible|ocupada|mantenimiento"}, ...]
    }
    """
    habitacion = nuevaHabitacion.query.get_or_404(habitacion_id)
    # Año solicitado o actual
    try:
        year = int(request.args.get('year')) if request.args.get('year') else datetime.utcnow().year
    except Exception:
        year = datetime.utcnow().year

    start = date(year, 1, 1)
    end = date(year, 12, 31)

    # Pre-cargar reservas no canceladas que intersecten con el año
    reservas = (
        Reserva.query
        .filter(Reserva.habitacion_id == habitacion.id, Reserva.estado != 'Cancelada')
        .filter(Reserva.check_out >= start, Reserva.check_in <= end)
        .all()
    )

    # Construir mapa de fechas
    days = {}

    # Si la habitación está en mantenimiento permanente, marcar todo el año
    if (habitacion.estado or '').lower() == 'mantenimiento':
        cur = start
        while cur <= end:
            days[cur] = 'mantenimiento'
            cur += timedelta(days=1)
    else:
        # Inicialmente disponible
        cur = start
        while cur <= end:
            days[cur] = 'disponible'
            cur += timedelta(days=1)

        # Marcar ocupadas según reservas (check_in inclusive, check_out exclusivo)
        for r in reservas:
            d0 = max(start, r.check_in)
            # check_out puede ser None; asumir al menos 1 noche
            co = r.check_out or (r.check_in + timedelta(days=1))
            # exclusivo al salir; acotar al rango del año (+1 para poder usar <)
            d1_excl = min(end + timedelta(days=1), co)
            cur = d0
            while cur < d1_excl:
                days[cur] = 'ocupada'
                cur += timedelta(days=1)

    payload = {
        'ok': True,
        'habitacion_id': habitacion.id,
        'year': year,
        'days': [{'date': d.isoformat(), 'status': days[d]} for d in sorted(days.keys())]
    }
    return jsonify(payload)
