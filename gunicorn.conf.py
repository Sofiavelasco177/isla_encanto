import os

# Bind al puerto proporcionado por la plataforma (p. ej. Render/Railway/DO),
# con fallback a 5000 para desarrollo/local.
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = 2  # Reducir workers para usar menos memoria
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Aumentar timeout a 2 minutos
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = False  # Cambiar a False para evitar problemas de inicialización