 Resort Encanto - Aplicación Flask

Una aplicación web para la gestión de un resort con funcionalidades de reservas, autenticación y administración.
 Despliegue con Docker

Requisitos previos
- Docker instalado
- Docker Compose instalado

Configuración rápida

1. Clonar el repositorio
```bash
git clone <tu-repositorio>
cd Resort_encanto
```



3. Construir y ejecutar con Docker Compose
```bash
docker-compose up --build
```



 Comandos útiles

Construir la imagen Docker:
```bash
docker build -t resort-encanto .
```

Ejecutar el contenedor:
```bash
docker run -p 5000:5000 --env-file .env resort-encanto
```




 Base de datos

Por defecto usa SQLite. La base de datos se almacena en `instance/tu_base_de_datos.db` y se persiste usando volúmenes de Docker


Estructura del proyecto

Resort_encanto/
├── run.py                 # Punto de entrada
├── config.py             # Configuración
├── requirements.txt      # Dependencias
├── Dockerfile           # Imagen Docker
├── docker-compose.yml   # Orquestación
├── gunicorn.conf.py     # Configuración Gunicorn
├── models/              # Modelos de base de datos
├── routes/              # Rutas de la aplicación
├── templates/           # Plantillas HTML
├── static/              # Archivos estáticos
└── utils/               # Utilidades
```
