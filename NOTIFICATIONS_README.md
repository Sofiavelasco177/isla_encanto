# 📧 Sistema de Notificaciones - Hotel Isla Encanto

Este sistema envía automáticamente notificaciones por correo electrónico a los huéspedes para alertas de check-in y check-out.

## 🚀 Características

### Notificaciones Automáticas
- **Check-in**: Se envían el día de llegada del huésped
- **Check-out**: Se envían el día de salida del huésped
- **Recordatorios**: Se envían 1 día antes del check-in/check-out

### Personalización
- Los usuarios pueden activar/desactivar notificaciones desde su perfil
- Plantillas HTML personalizadas con información de la reserva
- Soporte para múltiples idiomas (actualmente español)

## ⚙️ Configuración

### 1. Variables de Entorno SMTP
Configura las siguientes variables en tu entorno:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-password-de-aplicacion
SMTP_USE_TLS=true
SMTP_FROM=Hotel Isla Encanto <noreply@hotelislaencanto.com>
```

### 2. Configuración de Base de Datos
Las columnas `notif_checkin` y `notif_checkout` se agregan automáticamente al iniciar la aplicación.

### 3. Automatización (Windows)
Para automatizar el envío diario:

#### Opción A: Tarea Programada (Recomendado)
```powershell
# Ejecutar como administrador
PowerShell -ExecutionPolicy Bypass -File scripts/setup_notifications_scheduler.ps1
```

#### Opción B: Ejecución Manual
```batch
# Doble clic en:
scripts/send_notifications.bat
```

## 🎯 Uso

### Panel de Administración
1. Ve a **Dashboard → Notificaciones**
2. Visualiza estadísticas de notificaciones
3. Envía notificaciones manualmente
4. Configura preferencias de usuarios

### Envío Manual
```python
from utils.notifications import send_daily_notifications

# Enviar notificaciones del día
checkins_sent, checkouts_sent = send_daily_notifications()
```

### Configuración de Usuario
Los usuarios pueden configurar sus notificaciones desde:
- **Perfil de Usuario → Configuración de Notificaciones**

## 📋 Tipos de Notificaciones

### 1. Check-in (Día de llegada)
- **Asunto**: 🏨 ¡Tu check-in es hoy! - Reserva #123
- **Contenido**: 
  - Información de la reserva
  - Horarios de check-in
  - Documentos requeridos
  - Amenidades incluidas

### 2. Check-out (Día de salida)
- **Asunto**: 🌅 ¡Gracias por tu estadía! Check-out - Reserva #123
- **Contenido**:
  - Agradecimiento por la estadía
  - Recordatorios de check-out
  - Ofertas para futuras reservas

### 3. Recordatorios (1 día antes)
- **Check-in**: Recordatorio para mañana
- **Check-out**: Preparación para la salida

## 🔧 API de Notificaciones

### Funciones Principales

```python
# Envío diario automático
send_daily_notifications() -> Tuple[int, int]

# Envío de recordatorios
send_reminder_notifications() -> Tuple[int, int]

# Notificación específica de check-in
send_checkin_notification(reserva_id: int) -> bool

# Notificación específica de check-out
send_checkout_notification(reserva_id: int) -> bool
```

### Rutas de Administración

- `GET /admin/notifications` - Panel principal
- `POST /admin/notifications/send-manual` - Envío manual
- `GET /admin/notifications/settings` - Configuración de usuarios
- `POST /admin/notifications/settings/user/<id>` - Actualizar usuario

## 📊 Logs y Monitoreo

Los logs se guardan en:
- `logs/notifications.log` - Registro de envíos
- Nivel de logging configurable
- Información de éxito/error para cada envío

## 🛠️ Solución de Problemas

### Notificaciones no se envían
1. Verifica configuración SMTP
2. Revisa que el usuario tenga email configurado
3. Confirma que las notificaciones estén activadas
4. Consulta logs en `logs/notifications.log`

### Error de autenticación SMTP
- Usa contraseñas de aplicación para Gmail
- Verifica configuración de 2FA
- Confirma credenciales SMTP

### Base de datos
```sql
-- Verificar columnas de notificaciones
DESCRIBE usuario;

-- Activar notificaciones para todos los usuarios
UPDATE usuario SET notif_checkin = 1, notif_checkout = 1;
```

## 📈 Estadísticas

El panel de administración muestra:
- Check-ins/check-outs programados para hoy
- Recordatorios programados para mañana
- Porcentaje de usuarios con notificaciones activas
- Historial de envíos

## 🔒 Seguridad

- Las credenciales SMTP se almacenan como variables de entorno
- Los emails se envían usando conexiones TLS/SSL
- Los usuarios pueden desactivar notificaciones en cualquier momento
- No se almacenan credenciales de email en la base de datos

## 🚀 Próximas Características

- [ ] Notificaciones por SMS
- [ ] Plantillas personalizables por administrador
- [ ] Notificaciones de promociones
- [ ] Integración con WhatsApp Business
- [ ] Estadísticas avanzadas de engagement

## 📞 Soporte

Para soporte técnico, contacta al equipo de desarrollo o revisa los logs del sistema.