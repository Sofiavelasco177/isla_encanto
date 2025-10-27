# config.py
import os


class Config:
 
    DB_USER = os.environ.get('DB_USER', 'adriana')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'adrianac')
    DB_HOST = os.environ.get('DB_HOST', 'isladigital.xyz')
    DB_PORT = os.environ.get('DB_PORT', '3311')
    DB_NAME = os.environ.get('DB_NAME', 'f58_adriana')
    # Timeouts configurables (segundos) y pool
    DB_CONNECT_TIMEOUT = int(os.environ.get('DB_CONNECT_TIMEOUT', '30'))
    DB_READ_TIMEOUT = int(os.environ.get('DB_READ_TIMEOUT', '30'))
    DB_WRITE_TIMEOUT = int(os.environ.get('DB_WRITE_TIMEOUT', '30'))
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '5'))
    DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', '10'))
    DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', '280'))
    
    # Estrategia dual:
    # - Si existe DATABASE_URL -> usarla (MySQL en producción)
    # - Si no existe -> usar SQLite local en 'instance/tu_base_de_datos.db' con ruta ABSOLUTA (evita errores en Windows)
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _sqlite_path = os.path.join(_base_dir, 'instance', 'tu_base_de_datos.db')
    # Permitir forzar SQLite vía variable de entorno (útil para desarrollo local)
    _force_sqlite = os.environ.get('USE_SQLITE', '').strip().lower() in ('1', 'true', 'yes', 'on')
    # Orden de selección de la URI:
    # 1) DATABASE_URL (si está definida)
    # 2) MySQL construido desde variables/valores por defecto
    # 3) SQLite local como fallback
    if _force_sqlite:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{_sqlite_path}'
    elif os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    elif all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        SQLALCHEMY_DATABASE_URI = (
            f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
            f'?connect_timeout={DB_CONNECT_TIMEOUT}&read_timeout={DB_READ_TIMEOUT}&write_timeout={DB_WRITE_TIMEOUT}'
        )
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{_sqlite_path}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Esquema preferido para generar URLs externas (útil para OAuth tras proxy)
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'http')
    
    # Configuración adaptable según el tipo de base de datos
    if 'sqlite' in SQLALCHEMY_DATABASE_URI:
        # Configuración optimizada para SQLite
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
    else:
        # Configuración para MySQL (pool configurable)
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': DB_POOL_RECYCLE,
            'pool_size': DB_POOL_SIZE,
            'max_overflow': DB_MAX_OVERFLOW,
            'pool_timeout': DB_CONNECT_TIMEOUT
        }