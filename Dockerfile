FROM python:3.13-alpine

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para algunos paquetes de Python
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    linux-headers \
    libffi-dev \
    bash

# Copiar archivo de requerimientos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación (todo el repositorio)
COPY . .

# Normalizar nombres de carpetas para Linux (case-sensitive)
RUN bash -c '\
    if [ -d "Templates" ] && [ ! -d "templates" ]; then \
        echo "Renombrando Templates -> templates"; \
        mv Templates templates; \
    fi; \
    if [ -d "Static" ] && [ ! -d "static" ]; then \
        echo "Renombrando Static -> static"; \
        mv Static static; \
    fi; \
'

# Crear carpeta instance (para base de datos u otros archivos)
RUN mkdir -p instance && chmod 777 instance

# Verificar estructura de carpetas (solo para diagnóstico en build)
RUN bash -c '\
    echo "📂 Build check: /app y subcarpetas"; \
    ls -la /app || true; \
    if [ -d "/app/templates" ]; then ls -la /app/templates; fi; \
'

# Exponer el puerto 5000
EXPOSE 5000

# Variables de entorno
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Comando por defecto: ejecutar Gunicorn
CMD bash -c '\
    echo "🔧 Iniciando aplicación Flask con Gunicorn..."; \
    mkdir -p /app/instance && chmod 777 /app/instance; \
    gunicorn --config gunicorn.conf.py run:app \
'
