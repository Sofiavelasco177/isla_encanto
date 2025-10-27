#!/usr/bin/env python3
"""
Script para enviar notificaciones diarias de check-in y check-out
Se ejecuta automáticamente cada día para enviar alertas a los usuarios
"""

import sys
import os
from datetime import datetime
import logging

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import create_app
from utils.notifications import send_daily_notifications, send_reminder_notifications

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/notifications.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """
    Función principal para enviar notificaciones diarias
    """
    logger.info("=== Iniciando envío de notificaciones diarias ===")
    
    try:
        # Crear la aplicación Flask
        app = create_app()
        
        with app.app_context():
            # Enviar notificaciones del día
            logger.info("Enviando notificaciones del día...")
            checkins_sent, checkouts_sent = send_daily_notifications()
            
            # Enviar recordatorios para mañana
            logger.info("Enviando recordatorios para mañana...")
            checkin_reminders, checkout_reminders = send_reminder_notifications()
            
            # Resumen
            total_sent = checkins_sent + checkouts_sent + checkin_reminders + checkout_reminders
            
            logger.info("=== Resumen de notificaciones ===")
            logger.info(f"Check-ins de hoy: {checkins_sent}")
            logger.info(f"Check-outs de hoy: {checkouts_sent}")
            logger.info(f"Recordatorios check-in mañana: {checkin_reminders}")
            logger.info(f"Recordatorios check-out mañana: {checkout_reminders}")
            logger.info(f"Total enviadas: {total_sent}")
            
            if total_sent > 0:
                logger.info("✅ Notificaciones enviadas exitosamente")
            else:
                logger.info("ℹ️ No hay notificaciones para enviar hoy")
                
    except Exception as e:
        logger.error(f"❌ Error al enviar notificaciones: {str(e)}")
        sys.exit(1)
    
    logger.info("=== Proceso de notificaciones completado ===")

if __name__ == "__main__":
    main()