# Configuración para automatizar notificaciones en Windows (PowerShell)
# Ejecutar este script para configurar una tarea programada

# Crear una tarea programada que se ejecute todos los días a las 8:00 AM
$TaskName = "Hotel-Notifications-Daily"
$ScriptPath = "C:\Users\velas\OneDrive\Desktop\Resort_encanto\scripts\send_daily_notifications.py"
$PythonPath = "python"  # Ajustar según tu instalación de Python

# Acción que ejecutará el script
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ScriptPath

# Trigger para ejecutar todos los días a las 8:00 AM
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

# Configuración de la tarea
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Registro de la tarea
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Envío diario de notificaciones de check-in y check-out del Hotel Isla Encanto"

Write-Host "Tarea programada '$TaskName' creada exitosamente."
Write-Host "Se ejecutará todos los días a las 8:00 AM"
Write-Host ""
Write-Host "Para verificar: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Para ejecutar manualmente: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Para eliminar: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:$false"