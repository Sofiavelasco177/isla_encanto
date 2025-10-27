from datetime import datetime, timedelta, date
from models.baseDatos import db, Reserva, ReservaDatosHospedaje, Usuario, nuevaHabitacion
from utils.mailer import send_email
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

def send_checkin_notification(reserva_id: int) -> bool:
    """
    Envía notificación de check-in al usuario
    Se ejecuta el día de la llegada
    """
    try:
        reserva = Reserva.query.get(reserva_id)
        if not reserva:
            logger.error(f"Reserva {reserva_id} no encontrada")
            return False
            
        usuario = Usuario.query.get(reserva.usuario_id)
        if not usuario or not usuario.correo:
            logger.error(f"Usuario sin email para reserva {reserva_id}")
            return False
            
        # Verificar si el usuario tiene activadas las notificaciones
        if not usuario.notif_checkin:
            logger.info(f"Usuario {usuario.idUsuario} tiene desactivadas las notificaciones de check-in")
            return True
            
        habitacion = nuevaHabitacion.query.get(reserva.habitacion_id)
        datos_hospedaje = ReservaDatosHospedaje.query.filter_by(reserva_id=reserva_id).first()
        
        # Plantilla HTML para check-in
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 30px; border-radius: 8px 8px 0 0; }}
                .content {{ background: white; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏨 ¡Bienvenido al Hotel Isla Encanto!</h1>
                    <p>Tu check-in es hoy - ¡Te esperamos!</p>
                </div>
                
                <div class="content">
                    <h2>Hola {usuario.usuario},</h2>
                    
                    <p>¡Qué emoción! Hoy es el día de tu llegada al <strong>Hotel Isla Encanto</strong>. Estamos preparando todo para que tengas una experiencia inolvidable.</p>
                    
                    <div class="highlight">
                        <h3>📋 Detalles de tu Reserva</h3>
                        <p><strong>Reserva #:</strong> {reserva.id}</p>
                        <p><strong>Habitación:</strong> {habitacion.nombre if habitacion else f'Habitación #{reserva.habitacion_id}'}</p>
                        <p><strong>Check-in:</strong> {reserva.check_in.strftime('%d de %B de %Y')}</p>
                        <p><strong>Check-out:</strong> {reserva.check_out.strftime('%d de %B de %Y') if reserva.check_out else 'No definido'}</p>
                        {f'<p><strong>Huésped Principal:</strong> {datos_hospedaje.nombre1}</p>' if datos_hospedaje else ''}
                    </div>
                    
                    <div class="warning">
                        <h3>⏰ Información Importante</h3>
                        <ul>
                            <li><strong>Horario de Check-in:</strong> 3:00 PM - 11:00 PM</li>
                            <li><strong>Documentos requeridos:</strong> Cédula de ciudadanía o pasaporte</li>
                            <li><strong>Check-in anticipado:</strong> Sujeto a disponibilidad (cargo adicional puede aplicar)</li>
                        </ul>
                    </div>
                    
                    <h3>🎯 Lo que puedes esperar:</h3>
                    <ul>
                        <li>WiFi gratuito en todas las instalaciones</li>
                        <li>Servicio de recepción 24/7</li>
                        <li>Desayuno buffet (según tu plan)</li>
                        <li>Acceso a todas nuestras instalaciones</li>
                    </ul>
                    
                    <p><strong>¿Tienes alguna pregunta?</strong> No dudes en contactarnos:</p>
                    <p>📞 <strong>Teléfono:</strong> +57 316 027 0709</p>
                    <p>📧 <strong>Email:</strong> info@hotelislaencanto.com</p>
                </div>
                
                <div class="footer">
                    <p><strong>Hotel Isla Encanto</strong></p>
                    <p>Experiencias únicas, momentos inolvidables</p>
                    <p style="font-size: 12px; color: #666; margin-top: 15px;">
                        Puedes desactivar estas notificaciones desde tu perfil de usuario.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"🏨 ¡Tu check-in es hoy! - Reserva #{reserva.id}"
        
        success = send_email(usuario.correo, subject, html_content)
        
        if success:
            logger.info(f"Notificación de check-in enviada para reserva {reserva_id}")
        else:
            logger.error(f"Error enviando notificación de check-in para reserva {reserva_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error en send_checkin_notification: {str(e)}")
        return False


def send_checkout_notification(reserva_id: int) -> bool:
    """
    Envía notificación de check-out al usuario
    Se ejecuta el día de la salida
    """
    try:
        reserva = Reserva.query.get(reserva_id)
        if not reserva:
            logger.error(f"Reserva {reserva_id} no encontrada")
            return False
            
        usuario = Usuario.query.get(reserva.usuario_id)
        if not usuario or not usuario.correo:
            logger.error(f"Usuario sin email para reserva {reserva_id}")
            return False
            
        # Verificar si el usuario tiene activadas las notificaciones
        if not usuario.notif_checkout:
            logger.info(f"Usuario {usuario.idUsuario} tiene desactivadas las notificaciones de check-out")
            return True
            
        habitacion = nuevaHabitacion.query.get(reserva.habitacion_id)
        datos_hospedaje = ReservaDatosHospedaje.query.filter_by(reserva_id=reserva_id).first()
        
        # Plantilla HTML para check-out
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 30px; border-radius: 8px 8px 0 0; }}
                .content {{ background: white; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .thanks {{ background: #f0f8ff; border-left: 4px solid #667eea; padding: 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌅 ¡Hora del Check-out!</h1>
                    <p>Esperamos que hayas disfrutado tu estadía</p>
                </div>
                
                <div class="content">
                    <h2>Hola {usuario.usuario},</h2>
                    
                    <p>¡Ha llegado el momento de despedirnos! Esperamos que tu estadía en el <strong>Hotel Isla Encanto</strong> haya sido excepcional y llena de momentos especiales.</p>
                    
                    <div class="highlight">
                        <h3>📋 Detalles de tu Estadía</h3>
                        <p><strong>Reserva #:</strong> {reserva.id}</p>
                        <p><strong>Habitación:</strong> {habitacion.nombre if habitacion else f'Habitación #{reserva.habitacion_id}'}</p>
                        <p><strong>Check-in:</strong> {reserva.check_in.strftime('%d de %B de %Y')}</p>
                        <p><strong>Check-out:</strong> {reserva.check_out.strftime('%d de %B de %Y') if reserva.check_out else 'Hoy'}</p>
                        {f'<p><strong>Huésped Principal:</strong> {datos_hospedaje.nombre1}</p>' if datos_hospedaje else ''}
                    </div>
                    
                    <div class="thanks">
                        <h3>💙 ¡Gracias por elegirnos!</h3>
                        <p>Tu confianza es nuestro mayor premio. Esperamos haberte brindado una experiencia que supere tus expectativas.</p>
                    </div>
                    
                    <h3>⏰ Recordatorios para tu Check-out:</h3>
                    <ul>
                        <li><strong>Horario límite:</strong> 12:00 PM (mediodía)</li>
                        <li><strong>Entrega de llaves:</strong> En recepción</li>
                        <li><strong>Revisión de minibar:</strong> Si aplica</li>
                        <li><strong>Check-out tardío:</strong> Disponible con costo adicional</li>
                    </ul>
                    
                    <h3>🌟 ¿Te gustaría regresar?</h3>
                    <p>Como huésped especial, tienes acceso a:</p>
                    <ul>
                        <li>Descuentos exclusivos en futuras reservas</li>
                        <li>Early check-in gratuito (sujeto a disponibilidad)</li>
                        <li>Actualizaciones de habitación sin costo</li>
                    </ul>
                    
                    <p><strong>¿Necesitas ayuda?</strong> Estamos aquí para ti:</p>
                    <p>📞 <strong>Teléfono:</strong> +57 316 027 0709</p>
                    <p>📧 <strong>Email:</strong> info@hotelislaencanto.com</p>
                    
                    <p style="margin-top: 25px;"><strong>¡Te esperamos pronto de vuelta en el Hotel Isla Encanto!</strong></p>
                </div>
                
                <div class="footer">
                    <p><strong>Hotel Isla Encanto</strong></p>
                    <p>Donde cada momento se convierte en un recuerdo especial</p>
                    <p style="font-size: 12px; color: #666; margin-top: 15px;">
                        Puedes desactivar estas notificaciones desde tu perfil de usuario.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"🌅 ¡Gracias por tu estadía! Check-out - Reserva #{reserva.id}"
        
        success = send_email(usuario.correo, subject, html_content)
        
        if success:
            logger.info(f"Notificación de check-out enviada para reserva {reserva_id}")
        else:
            logger.error(f"Error enviando notificación de check-out para reserva {reserva_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error en send_checkout_notification: {str(e)}")
        return False


def get_checkin_reservations_today() -> List[int]:
    """
    Obtiene las reservas que tienen check-in hoy
    """
    today = date.today()
    reservas = Reserva.query.filter(
        Reserva.check_in == today,
        Reserva.estado.in_(['Activa', 'Confirmada'])
    ).all()
    
    return [r.id for r in reservas]


def get_checkout_reservations_today() -> List[int]:
    """
    Obtiene las reservas que tienen check-out hoy
    """
    today = date.today()
    reservas = Reserva.query.filter(
        Reserva.check_out == today,
        Reserva.estado.in_(['Activa', 'Confirmada'])
    ).all()
    
    return [r.id for r in reservas]


def send_daily_notifications() -> Tuple[int, int]:
    """
    Función principal para enviar todas las notificaciones diarias
    Retorna (checkins_enviados, checkouts_enviados)
    """
    checkin_ids = get_checkin_reservations_today()
    checkout_ids = get_checkout_reservations_today()
    
    checkins_sent = 0
    checkouts_sent = 0
    
    # Enviar notificaciones de check-in
    for reserva_id in checkin_ids:
        if send_checkin_notification(reserva_id):
            checkins_sent += 1
    
    # Enviar notificaciones de check-out
    for reserva_id in checkout_ids:
        if send_checkout_notification(reserva_id):
            checkouts_sent += 1
    
    logger.info(f"Notificaciones enviadas: {checkins_sent} check-ins, {checkouts_sent} check-outs")
    
    return checkins_sent, checkouts_sent


def send_reminder_notifications() -> Tuple[int, int]:
    """
    Envía recordatorios un día antes del check-in y check-out
    Retorna (checkin_reminders, checkout_reminders)
    """
    tomorrow = date.today() + timedelta(days=1)
    
    # Recordatorios de check-in (1 día antes)
    checkin_reminders = Reserva.query.filter(
        Reserva.check_in == tomorrow,
        Reserva.estado.in_(['Activa', 'Confirmada'])
    ).all()
    
    # Recordatorios de check-out (1 día antes)
    checkout_reminders = Reserva.query.filter(
        Reserva.check_out == tomorrow,
        Reserva.estado.in_(['Activa', 'Confirmada'])
    ).all()
    
    checkin_sent = 0
    checkout_sent = 0
    
    # Enviar recordatorios de check-in
    for reserva in checkin_reminders:
        if send_checkin_reminder(reserva.id):
            checkin_sent += 1
    
    # Enviar recordatorios de check-out
    for reserva in checkout_reminders:
        if send_checkout_reminder(reserva.id):
            checkout_sent += 1
    
    return checkin_sent, checkout_sent


def send_checkin_reminder(reserva_id: int) -> bool:
    """
    Envía recordatorio de check-in (1 día antes)
    """
    try:
        reserva = Reserva.query.get(reserva_id)
        if not reserva:
            return False
            
        usuario = Usuario.query.get(reserva.usuario_id)
        if not usuario or not usuario.correo or not usuario.notif_checkin:
            return True
            
        habitacion = nuevaHabitacion.query.get(reserva.habitacion_id)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ffa726 0%, #ff7043 100%); color: white; text-align: center; padding: 30px; border-radius: 8px 8px 0 0; }}
                .content {{ background: white; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #fff3e0; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 ¡Mañana es tu llegada!</h1>
                    <p>Recordatorio de tu reserva</p>
                </div>
                
                <div class="content">
                    <h2>Hola {usuario.usuario},</h2>
                    
                    <p>¡Qué emoción! <strong>Mañana</strong> es el día de tu llegada al Hotel Isla Encanto. Estamos muy emocionados de recibirte.</p>
                    
                    <div class="highlight">
                        <h3>📋 Tu Reserva</h3>
                        <p><strong>Reserva #:</strong> {reserva.id}</p>
                        <p><strong>Habitación:</strong> {habitacion.nombre if habitacion else f'Habitación #{reserva.habitacion_id}'}</p>
                        <p><strong>Check-in:</strong> {reserva.check_in.strftime('%d de %B de %Y')} (mañana)</p>
                        <p><strong>Check-out:</strong> {reserva.check_out.strftime('%d de %B de %Y') if reserva.check_out else 'No definido'}</p>
                    </div>
                    
                    <p><strong>Prepárate para una experiencia increíble:</strong></p>
                    <ul>
                        <li>Lleva tu documento de identidad</li>
                        <li>Check-in a partir de las 3:00 PM</li>
                        <li>WiFi gratuito en todo el hotel</li>
                    </ul>
                    
                    <p>¡Te esperamos!</p>
                </div>
                
                <div class="footer">
                    <p><strong>Hotel Isla Encanto</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"📅 ¡Mañana es tu llegada! - Reserva #{reserva.id}"
        return send_email(usuario.correo, subject, html_content)
        
    except Exception as e:
        logger.error(f"Error en send_checkin_reminder: {str(e)}")
        return False


def send_checkout_reminder(reserva_id: int) -> bool:
    """
    Envía recordatorio de check-out (1 día antes)
    """
    try:
        reserva = Reserva.query.get(reserva_id)
        if not reserva:
            return False
            
        usuario = Usuario.query.get(reserva.usuario_id)
        if not usuario or not usuario.correo or not usuario.notif_checkout:
            return True
            
        habitacion = nuevaHabitacion.query.get(reserva.habitacion_id)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #42a5f5 0%, #1e88e5 100%); color: white; text-align: center; padding: 30px; border-radius: 8px 8px 0 0; }}
                .content {{ background: white; padding: 30px; border: 1px solid #ddd; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⏰ Check-out mañana</h1>
                    <p>Recordatorio de salida</p>
                </div>
                
                <div class="content">
                    <h2>Hola {usuario.usuario},</h2>
                    
                    <p>Esperamos que estés disfrutando tu estadía. Te recordamos que <strong>mañana</strong> es tu día de check-out.</p>
                    
                    <div class="highlight">
                        <h3>📋 Detalles</h3>
                        <p><strong>Reserva #:</strong> {reserva.id}</p>
                        <p><strong>Habitación:</strong> {habitacion.nombre if habitacion else f'Habitación #{reserva.habitacion_id}'}</p>
                        <p><strong>Check-out:</strong> {reserva.check_out.strftime('%d de %B de %Y') if reserva.check_out else 'Mañana'}</p>
                        <p><strong>Hora límite:</strong> 12:00 PM</p>
                    </div>
                    
                    <p><strong>Para tu check-out:</strong></p>
                    <ul>
                        <li>Entrega las llaves en recepción</li>
                        <li>Verifica que no olvides nada</li>
                        <li>Check-out tardío disponible (con costo adicional)</li>
                    </ul>
                    
                    <p>¡Gracias por elegirnos!</p>
                </div>
                
                <div class="footer">
                    <p><strong>Hotel Isla Encanto</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        subject = f"⏰ Check-out mañana - Reserva #{reserva.id}"
        return send_email(usuario.correo, subject, html_content)
        
    except Exception as e:
        logger.error(f"Error en send_checkout_reminder: {str(e)}")
        return False