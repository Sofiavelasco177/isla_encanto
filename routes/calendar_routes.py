from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from models.baseDatos import db, ReservaRestaurante, Reserva, Usuario, nuevaHabitacion, TicketHospedaje
from datetime import datetime

calendar_bp = Blueprint('calendar_routes', __name__, url_prefix='/calendar')

@calendar_bp.route('/admin/historial')
def admin_historial():
    """Ruta independiente para el calendario de administración"""
    # Verificar que sea administrador
    user = session.get('user')
    if not user or user.get('rol') != 'admin':
        flash('Acceso restringido solo para administradores', 'warning')
        return redirect(url_for('registro.login'))
    
    from sqlalchemy import or_
    
    # Obtener el mes y año actual
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Obtener reservas de restaurante
    reservas_restaurante = db.session.query(ReservaRestaurante).all()
    restaurant_data = []
    
    for reserva in reservas_restaurante:
        if reserva.fecha_reserva:
            restaurant_data.append({
                'id': reserva.id,
                'date': reserva.fecha_reserva.strftime('%Y-%m-%d'),
                'time': reserva.fecha_reserva.strftime('%H:%M'),
                'guests': reserva.cupo_personas,
                'name': reserva.nombre_cliente or 'Cliente',
                'ticket': reserva.ticket_numero,
                'status': reserva.estado
            })
    
    # Obtener reservas de hospedaje con relaciones
    reservas_hospedaje = db.session.query(Reserva)\
        .join(Usuario, Reserva.usuario_id == Usuario.idUsuario)\
        .join(nuevaHabitacion, Reserva.habitacion_id == nuevaHabitacion.id)\
        .all()
    
    hotel_data = []
    
    for reserva in reservas_hospedaje:
        # Obtener ticket asociado si existe
        ticket = TicketHospedaje.query.filter_by(reserva_id=reserva.id).first()
        
        hotel_data.append({
            'id': reserva.id,
            'checkIn': reserva.check_in.strftime('%Y-%m-%d'),
            'checkOut': reserva.check_out.strftime('%Y-%m-%d') if reserva.check_out else '',
            'room': reserva.habitacion.numero or reserva.habitacion.nombre,
            'type': reserva.habitacion.plan or 'Standard',
            'guest': ticket.nombre1 if ticket else reserva.usuario.usuario,
            'status': reserva.estado,
            'nights': (reserva.check_out - reserva.check_in).days if reserva.check_out else 1
        })
    
    # Preparar datos para el template
    reservation_data = {
        'restaurant': restaurant_data,
        'hotel': hotel_data
    }
    
    return render_template('dashboard/admin_calendar.html',
                         current_year=current_year,
                         current_month=current_month,
                         reservation_data=reservation_data)


