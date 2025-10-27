@echo off
echo ========================================
echo Hotel Isla Encanto - Notificaciones
echo ========================================
echo.

cd /d "C:\Users\velas\OneDrive\Desktop\Resort_encanto"

echo Enviando notificaciones diarias...
python scripts\send_daily_notifications.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Notificaciones enviadas exitosamente
) else (
    echo.
    echo ✗ Error al enviar notificaciones
)

echo.
echo Proceso completado. Presiona cualquier tecla para salir...
pause >nul