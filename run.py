from flask import Flask, render_template, send_from_directory, url_for, redirect
import logging
import os
from datetime import datetime
from config import Config
from werkzeug.middleware.proxy_fix import ProxyFix

# Configurar logging temprano
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from sqlalchemy import inspect, text
from models.baseDatos import Usuario
from routes.main import main_bp
from routes.registro import registro_bp
from routes.auth import auth_bp
from authlib.integrations.flask_client import OAuth
from utils.extensions import db, bcrypt, serializer
from routes.usuario.perfil_usuario_routes import perfil_usuario_bp
from routes.usuario.pagos_usuario import pagos_usuario_bp
from routes.usuario.restaurante_usuario_cart import restaurante_cart_bp
from flask import Blueprint

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Preferir minúsculas por compatibilidad Linux; fallback a 'Static' si es lo que existe
default_static = 'static' if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')) else 'Static'
app = Flask(__name__, template_folder='templates', static_folder=default_static, static_url_path='/static')
# Respetar cabeceras del proxy (X-Forwarded-Proto, Host, etc.) para generar URLs https correctas
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Mitigación defensiva: algunos navegadores (Edge) pueden enviar cookies heredadas/dañadas
# que rompen el parser de cookies de Werkzeug y generan 400 antes de llegar a la vista.
# Estas opciones ayudan a que nuestros cookies sean más seguros; el handler 400 más abajo
# nos permitirá registrar el error y ofrecer una forma de limpiar cookies.
try:
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    # Si estamos detrás de HTTPS, el proxy nos marca X-Forwarded-Proto; ProxyFix ya ajusta.
    # Aún así, marcamos Secure para producción si el esquema preferido es https.
    if (os.environ.get('PREFERRED_URL_SCHEME', 'http').lower() == 'https'):
        app.config.setdefault('SESSION_COOKIE_SECURE', True)
except Exception:
    pass

# Soportar nombres de carpetas con mayúsculas (por compatibilidad)
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, 'templates')
templates_dir_cap = os.path.join(base_dir, 'Templates')
static_dir = os.path.join(base_dir, 'static')
static_dir_cap = os.path.join(base_dir, 'Static')

try:
    # Siempre incluir ambas rutas si existen, primero 'templates', luego 'Templates'
    search_paths = list(getattr(app.jinja_loader, 'searchpath', []))
    to_add = []
    if os.path.isdir(templates_dir) and templates_dir not in search_paths:
        to_add.append(templates_dir)
    if os.path.isdir(templates_dir_cap) and templates_dir_cap not in search_paths:
        to_add.append(templates_dir_cap)
    if to_add:
        # Insertar al inicio manteniendo el orden preferido
        for p in reversed(to_add):
            search_paths.insert(0, p)
        app.jinja_loader.searchpath = search_paths
        logger.info(f"Plantillas: rutas de búsqueda actualizadas: {app.jinja_loader.searchpath}")
except Exception as e:
    logger.warning(f"No se pudo ajustar rutas de plantillas: {e}")

if not os.path.isdir(static_dir) and os.path.isdir(static_dir_cap):
    # Reasignar static_folder si solo existe 'Static'
    try:
        app.static_folder = static_dir_cap
        logger.info("Usando carpeta 'Static' como fallback para archivos estáticos")
    except Exception as e:
        logger.warning(f"No se pudo reasignar static_folder a 'Static': {e}")

# Debug: Log de la configuración de la base de datos
logger.info(f"DATABASE_URL configurada: {'Sí' if os.environ.get('DATABASE_URL') else 'No'}")
logger.info(f"DB_USER configurada: {'Sí' if os.environ.get('DB_USER') else 'No'}")

# Asegurar ruta de plantillas y loguearla para diagnosticar TemplateNotFound
templates_path = templates_dir if os.path.isdir(templates_dir) else (templates_dir_cap if os.path.isdir(templates_dir_cap) else os.path.join(base_dir, 'templates'))
try:
    search_paths = getattr(app.jinja_loader, 'searchpath', [])
    logger.info(f"Rutas de búsqueda de plantillas iniciales: {search_paths}")
    if templates_path not in search_paths:
        search_paths.insert(0, templates_path)
        app.jinja_loader.searchpath = search_paths
        logger.info(f"Rutas de búsqueda de plantillas actualizadas: {app.jinja_loader.searchpath}")
    # Comprobar si existe la plantilla principal esperada
    home_tpl = os.path.join(templates_path, 'home', 'Home.html')
    logger.info(f"Existe templates/home/Home.html? {'Sí' if os.path.exists(home_tpl) else 'No'} ({home_tpl})")
    try:
        logger.info(f"Listado de templates/: {os.listdir(templates_path)}")
        home_dir = os.path.join(templates_path, 'home')
        if os.path.isdir(home_dir):
            logger.info(f"Listado de templates/home: {os.listdir(home_dir)}")
        else:
            logger.info("La carpeta templates/home no existe")
    except Exception as e_ls:
        logger.warning(f"No se pudo listar templates: {e_ls}")
except Exception as e:
    logger.warning(f"No se pudo ajustar rutas de plantillas: {e}")

try:
    app.config.from_object(Config)
    import os as _os
    app.secret_key = _os.getenv('SECRET_KEY') or 'isla_encanto'
    
    # Log de la URI final que se está usando (sin mostrar credenciales completas)
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if 'mysql' in db_uri:
        logger.info("Usando MySQL como base de datos")
    else:
        logger.info("Usando SQLite como base de datos de fallback")
        
    logger.info("Configuración de Flask aplicada exitosamente")
except Exception as e:
    logger.error(f"Error al configurar Flask: {e}")
    raise

# inicializar extensiones
try:
    db.init_app(app)
    logger.info("SQLAlchemy inicializado correctamente")
    bcrypt.init_app(app)
    logger.info("Bcrypt inicializado correctamente")
except Exception as e:
    logger.error(f"Error al inicializar extensiones: {e}")
    raise

from itsdangerous import URLSafeTimedSerializer
import utils.extensions as extensions
extensions.serializer = URLSafeTimedSerializer(app.secret_key)

perfil_bp = Blueprint("perfil_usuario", __name__, url_prefix="/usuario")


# Inyectar el usuario actual en todas las plantillas (aunque flask_login no esté instalado)
@app.context_processor

def inject_current_user():
    try:
        from flask_login import current_user
        return {'current_user': current_user}
    except Exception:
        class _Anonymous:
            is_authenticated = False
        return {'current_user': _Anonymous()}

# Utilidades para plantillas: resolver URL de imágenes con fallback seguro
@app.context_processor
def media_utilities():
    import os as _os
    base = _os.path.dirname(_os.path.abspath(__file__))
    def media_url(image_path, version=None):
        try:
            placeholder = url_for('static', filename='img/OIP.webp')
            if not image_path:
                return placeholder
            s = str(image_path).strip()
            def _add_ver(u, path=None):
                if version is not None:
                    return f"{u}?v={version}"
                try:
                    if path and _os.path.isfile(path):
                        ts = int(_os.path.getmtime(path))
                        return f"{u}?v={ts}"
                except Exception:
                    pass
                return u
            if s.startswith('http://') or s.startswith('https://'):
                return s
            # uploads/<file>
            if s.startswith('uploads/'):
                rel = s[8:]
                inst = _os.path.join(base, 'instance', 'uploads', rel)
                if _os.path.isfile(inst):
                    u = url_for('media_file', filename=rel)
                    return _add_ver(u, inst)
                # ¿sigue en static por volumen legacy?
                legacy = _os.path.join(app.static_folder, 'img', 'uploads', rel)
                if _os.path.isfile(legacy):
                    return _add_ver(url_for('static', filename=f'img/uploads/{rel}'), legacy)
                return placeholder
            # img/uploads/<file>
            if s.startswith('img/uploads/'):
                rel = s.split('img/uploads/', 1)[1]
                legacy = _os.path.join(app.static_folder, 'img', 'uploads', rel)
                if _os.path.isfile(legacy):
                    return _add_ver(url_for('static', filename=f'img/uploads/{rel}'), legacy)
                inst = _os.path.join(base, 'instance', 'uploads', rel)
                if _os.path.isfile(inst):
                    return _add_ver(url_for('media_file', filename=rel), inst)
                return placeholder
            # static/<...>
            if s.startswith('static/'):
                rel = s[7:]
                cand = _os.path.join(app.static_folder, rel)
                if _os.path.isfile(cand):
                    return _add_ver(url_for('static', filename=rel), cand)
                return placeholder
            # tratar como ruta relativa bajo static/
            cand = _os.path.join(app.static_folder, s)
            if _os.path.isfile(cand):
                return _add_ver(url_for('static', filename=s), cand)
            return placeholder
        except Exception:
            try:
                return url_for('static', filename='img/OIP.webp')
            except Exception:
                return '/static/img/OIP.webp'
    return dict(media_url=media_url)


# Verificar y crear columnas necesarias en la tabla usuario
def init_database():
    try:
        with app.app_context():
            # Asegurar que el directorio instance existe y tiene permisos
            import os
            # Usar ruta relativa para desarrollo local
            instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
            
            if not os.path.exists(instance_dir):
                os.makedirs(instance_dir, exist_ok=True)
                app.logger.info(f'Directorio instance creado: {instance_dir}')
            
            try:
                # Crear las tablas primero
                db.create_all()
                app.logger.info('Tablas de la base de datos creadas/verificadas')
                
                # Luego verificar columnas
                inspector = inspect(db.engine)
                cols = [c['name'] for c in inspector.get_columns('usuario')] if 'usuario' in inspector.get_table_names() else []
                stmts = []
                # Agregar columnas para recuperación de contraseña si no existen
                if cols and 'reset_code' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN reset_code VARCHAR(6) NULL")
                if cols and 'reset_expire' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN reset_expire DATETIME NULL")
                # Columnas nuevas del modelo Usuario para compatibilidad con esquemas antiguos
                if cols and 'telefono' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN telefono VARCHAR(20) NULL")
                if cols and 'avatar' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN avatar VARCHAR(255) NULL")
                if cols and 'plan_tipo' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN plan_tipo VARCHAR(50) NULL")
                if cols and 'membresia_activa' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN membresia_activa TINYINT(1) DEFAULT 0")
                if cols and 'membresia_expira' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN membresia_expira DATE NULL")
                if cols and 'notif_checkin' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN notif_checkin TINYINT(1) DEFAULT 1")
                if cols and 'notif_checkout' not in cols:
                    stmts.append("ALTER TABLE usuario ADD COLUMN notif_checkout TINYINT(1) DEFAULT 1")
                for s in stmts:
                    try:
                        db.session.execute(text(s))
                        db.session.commit()
                        app.logger.info('Migración aplicada: %s', s)
                    except Exception as e:
                        db.session.rollback()
                        app.logger.exception('No se pudo aplicar la migración %s: %s', s, e)

                # Migraciones para tabla post (agregar columna 'orden')
                try:
                    post_cols = [c['name'] for c in inspector.get_columns('post')] if 'post' in inspector.get_table_names() else []
                except Exception:
                    post_cols = []
                if 'post' in inspector.get_table_names() and 'orden' not in post_cols:
                    try:
                        db.session.execute(text("ALTER TABLE post ADD COLUMN orden INTEGER NOT NULL DEFAULT 0"))
                        db.session.commit()
                        app.logger.info('Columna orden agregada a post')
                    except Exception as e:
                        db.session.rollback()
                        app.logger.exception('No se pudo agregar columna orden a post: %s', e)

                # Backfill orden para posts de categoría 'home'
                try:
                    from models.baseDatos import Post
                    home_posts = db.session.query(Post).filter(Post.categoria == 'home').order_by(Post.creado_en.asc()).all()
                    changed = False
                    for idx, p in enumerate(home_posts, start=1):
                        if getattr(p, 'orden', 0) in (None, 0):
                            p.orden = idx
                            changed = True
                    if changed:
                        db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    app.logger.warning('No se pudo hacer backfill de orden en posts home: %s', e)

                # Migraciones defensivas para nuevaHabitacion (agregar columnas faltantes)
                try:
                    if 'nuevaHabitacion' in inspector.get_table_names():
                        hab_cols = [c['name'] for c in inspector.get_columns('nuevaHabitacion')]
                    else:
                        hab_cols = []
                except Exception:
                    hab_cols = []
                stmts_hab = []
                if hab_cols is not None and 'plan' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN plan VARCHAR(20) NULL")
                if hab_cols is not None and 'numero' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN numero INTEGER NULL")
                if hab_cols is not None and 'caracteristicas' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN caracteristicas TEXT NULL")
                if hab_cols is not None and 'estado' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'Disponible'")
                if hab_cols is not None and 'cupo_personas' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN cupo_personas INTEGER NOT NULL DEFAULT 1")
                if hab_cols is not None and 'imagen' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN imagen VARCHAR(255) NULL")
                if hab_cols is not None and 'model3d' not in hab_cols:
                    stmts_hab.append("ALTER TABLE nuevaHabitacion ADD COLUMN model3d VARCHAR(255) NULL")
                for s in stmts_hab:
                    try:
                        db.session.execute(text(s))
                        db.session.commit()
                        app.logger.info('Migración aplicada a nuevaHabitacion: %s', s)
                    except Exception as e:
                        db.session.rollback()
                        app.logger.warning('No se pudo aplicar migración a nuevaHabitacion %s: %s', s, e)

                # Migraciones defensivas para plato_restaurante (agregar columna imagen si falta)
                try:
                    if 'plato_restaurante' in inspector.get_table_names():
                        plato_cols = [c['name'] for c in inspector.get_columns('plato_restaurante')]
                    else:
                        plato_cols = []
                except Exception:
                    plato_cols = []
                if plato_cols is not None and 'imagen' not in plato_cols:
                    try:
                        db.session.execute(text("ALTER TABLE plato_restaurante ADD COLUMN imagen VARCHAR(255) NULL"))
                        db.session.commit()
                        app.logger.info('Columna imagen agregada a plato_restaurante')
                    except Exception as e:
                        db.session.rollback()
                        app.logger.warning('No se pudo agregar columna imagen a plato_restaurante: %s', e)

                # Intentar migrar imágenes legacy de platos si guardadas en static/img/uploads -> instance/uploads
                try:
                    from models.baseDatos import PlatoRestaurante as _Plato
                    import shutil
                    legacy_prefix = os.path.join(app.static_folder, 'img', 'uploads')
                    inst_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'uploads')
                    os.makedirs(inst_uploads, exist_ok=True)
                    platos = db.session.query(_Plato).filter(_Plato.imagen.isnot(None)).all()
                    migrated_p = False
                    for p in platos:
                        path = (p.imagen or '').strip()
                        if not path:
                            continue
                        # Si ya es uploads/<file>
                        if path.startswith('uploads/'):
                            fname = path[8:]
                            dst = os.path.join(inst_uploads, fname)
                            if os.path.isfile(dst):
                                continue
                            src = os.path.join(legacy_prefix, fname)
                            try:
                                if os.path.isfile(src):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.move(src, dst)
                                    migrated_p = True
                            except Exception as em:
                                app.logger.warning(f'No se pudo mover legacy uploads de plato a instance: {src} -> {dst}: {em}')
                            continue
                        # img/uploads/<file>
                        if path.startswith('img/uploads/'):
                            fname = path.split('img/uploads/', 1)[1]
                            src = os.path.join(legacy_prefix, fname)
                            dst = os.path.join(inst_uploads, fname)
                            try:
                                if os.path.isfile(src):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.move(src, dst)
                                    p.imagen = f'uploads/{fname}'
                                    migrated_p = True
                                elif os.path.isfile(dst):
                                    p.imagen = f'uploads/{fname}'
                                    migrated_p = True
                            except Exception as em:
                                app.logger.warning(f'No se pudo migrar imagen de plato {src} -> {dst}: {em}')
                            continue
                        # static/img/uploads/<file>
                        if path.startswith('static/img/uploads/'):
                            fname = path.split('static/img/uploads/', 1)[1]
                            src = os.path.join(legacy_prefix, fname)
                            dst = os.path.join(inst_uploads, fname)
                            try:
                                if os.path.isfile(src):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.move(src, dst)
                                    p.imagen = f'uploads/{fname}'
                                    migrated_p = True
                                elif os.path.isfile(dst):
                                    p.imagen = f'uploads/{fname}'
                                    migrated_p = True
                            except Exception as em:
                                app.logger.warning(f'No se pudo migrar imagen de plato {src} -> {dst}: {em}')
                    if migrated_p:
                        db.session.commit()
                        app.logger.info('Migración de imágenes de platos a instance/uploads completada')
                except Exception as e:
                    db.session.rollback()
                    app.logger.warning('No se pudo migrar imágenes legacy de platos: %s', e)

                # Migrar imágenes legacy de static/img/uploads -> instance/uploads
                try:
                    from models.baseDatos import Post
                    import shutil
                    legacy_prefix = os.path.join(app.static_folder, 'img', 'uploads')
                    inst_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'uploads')
                    os.makedirs(inst_uploads, exist_ok=True)
                    posts = db.session.query(Post).filter(Post.imagen.isnot(None)).all()
                    migrated = False
                    for p in posts:
                        path = (p.imagen or '').strip()
                        if not path:
                            continue
                        # Si ya está en 'uploads/', no migrar
                        if path.startswith('uploads/'):
                            # asegurarnos que exista en instance o en legacy
                            fname = path[8:]
                            dst = os.path.join(inst_uploads, fname)
                            if os.path.isfile(dst):
                                continue
                            src = os.path.join(legacy_prefix, fname)
                            try:
                                if os.path.isfile(src):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.move(src, dst)
                                    migrated = True
                            except Exception as em:
                                app.logger.warning(f'No se pudo mover legacy uploads a instance: {src} -> {dst}: {em}')
                            continue
                        # Si es 'img/uploads/...'
                        if path.startswith('img/uploads/'):
                            fname = path.split('img/uploads/', 1)[1]
                            src = os.path.join(legacy_prefix, fname)
                            dst = os.path.join(inst_uploads, fname)
                            try:
                                if os.path.isfile(src):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.move(src, dst)
                                    p.imagen = f'uploads/{fname}'
                                    migrated = True
                                elif os.path.isfile(dst):
                                    p.imagen = f'uploads/{fname}'
                                    migrated = True
                                else:
                                    app.logger.warning(f'Archivo no encontrado en legacy ni instance: {fname}')
                            except Exception as em:
                                app.logger.warning(f'No se pudo migrar imagen {src} -> {dst}: {em}')
                            continue
                        # Si es 'static/img/uploads/...'
                        if path.startswith('static/img/uploads/'):
                            fname = path.split('static/img/uploads/', 1)[1]
                            src = os.path.join(legacy_prefix, fname)
                            dst = os.path.join(inst_uploads, fname)
                            try:
                                if os.path.isfile(src):
                                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                                    shutil.move(src, dst)
                                    p.imagen = f'uploads/{fname}'
                                    migrated = True
                                elif os.path.isfile(dst):
                                    p.imagen = f'uploads/{fname}'
                                    migrated = True
                                else:
                                    app.logger.warning(f'Archivo no encontrado en legacy ni instance: {fname}')
                            except Exception as em:
                                app.logger.warning(f'No se pudo migrar imagen {src} -> {dst}: {em}')
                    if migrated:
                        db.session.commit()
                        app.logger.info('Migración de imágenes a instance/uploads completada')
                except Exception as e:
                    db.session.rollback()
                    app.logger.warning('No se pudo migrar imágenes legacy: %s', e)

                # Asegurar tablas de reservas de restaurante
                try:
                    from models.baseDatos import ReservaRestaurante, ReservaPlato
                    db.create_all()  # crea si faltan
                except Exception as e:
                    app.logger.warning('No se pudieron crear tablas de restaurante: %s', e)

            except Exception as e:
                app.logger.exception('Error revisando/alterando la tabla usuario al iniciar: %s', e)

    except Exception as e:
        app.logger.exception('Error inicializando la base de datos: %s', e)

# Inicializar/verificar esquema de base de datos en cualquier motor (SQLite o MySQL)
try:
    logger.info('Verificando esquema de base de datos y aplicando migraciones seguras...')
    init_database()
except Exception as _e:
    logger.warning(f"No se pudo inicializar/verificar automáticamente la base de datos: {_e}")

# Registrar blueprints (después de init_db)
app.register_blueprint(restaurante_cart_bp)

# ---------------- GOOGLE OAUTH ---------------- #
oauth = OAuth(app)
app.config['OAUTH'] = oauth

# Verificar que las credenciales estén cargadas
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

# Endpoints explícitos de Google para evitar fallos de descubrimiento
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

if client_id and client_secret:
    app.logger.info(f'Google OAuth configurado con Client ID: {client_id[:10]}...')
    try:
        # Registrar con endpoints explícitos (más robusto en entornos con red limitada)
        oauth.register(
            name='google',
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=GOOGLE_AUTHORIZE_URL,
            token_url=GOOGLE_TOKEN_URL,
            client_kwargs={"scope": "openid email profile", "timeout": 10}
        )
        app.logger.info('Google OAuth registrado exitosamente')
    except Exception as e:
        app.logger.warning(f'Error configurando Google OAuth: {e}. Usando modo desarrollo.')
        app.config['ENABLE_DEV_GOOGLE'] = True
        # Registrar cliente dummy para evitar errores
        oauth.register(
            name='google',
            client_id='dummy',
            client_secret='dummy',
            authorize_url=GOOGLE_AUTHORIZE_URL,
            token_url=GOOGLE_TOKEN_URL,
            client_kwargs={"scope": "openid email profile"}
        )
else:
    app.logger.warning('Credenciales de Google OAuth no encontradas. Usando modo desarrollo.')
    app.config['ENABLE_DEV_GOOGLE'] = True
    # Registrar cliente dummy para evitar errores
    oauth.register(
        name='google',
        client_id='dummy',
        client_secret='dummy',
        authorize_url=GOOGLE_AUTHORIZE_URL,
        token_url=GOOGLE_TOKEN_URL,
        client_kwargs={"scope": "openid email profile"}
    )



# ------------------- Registro de Blueprints -------------------
from routes.registro import registro_bp
from routes.main import main_bp
from routes.auth import auth_bp
from routes.dashboard.admin import admin_bp
from routes.recuperar_contraseña import recuperar_bp
from routes.usuario.hospedaje_usuario_routes import hospedaje_usuario_bp
from routes.usuario.perfil_usuario_routes import perfil_usuario_bp
from routes.dashboard.perfil_admin_routes import perfil_admin_bp
from routes.calendar_routes import calendar_bp


app.register_blueprint(registro_bp, url_prefix='/registro')
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')  # ✅ Registrar blueprint admin
app.register_blueprint(recuperar_bp, url_prefix='/recuperar')
app.register_blueprint(hospedaje_usuario_bp, url_prefix='/hospedaje')
app.register_blueprint(perfil_usuario_bp, url_prefix='/perfil')
app.register_blueprint(pagos_usuario_bp, url_prefix='/usuario')
app.register_blueprint(perfil_admin_bp)
app.register_blueprint(calendar_bp, url_prefix='/calendar')



# ------------------- Aliases de Rutas (compatibilidad con plantillas) -------------------
from routes import main as _main
from routes import auth as _auth
from routes import registro as _registro

# Rutas públicas
app.add_url_rule('/', endpoint='home', view_func=_main.home)
app.add_url_rule('/hospedaje', endpoint='hospedaje', view_func=_main.hospedaje)
app.add_url_rule('/restaurante', endpoint='restaurantes', view_func=_main.restaurantes)
app.add_url_rule('/nosotros', endpoint='nosotros', view_func=_main.nosotros)
app.add_url_rule('/Experiencias', endpoint='experiencias', view_func=_main.experiencias, methods=['GET', 'POST'])
app.add_url_rule('/login', endpoint='login', view_func=_registro.login, methods=['GET', 'POST'])

#Ruta de autenticación con Google (implementada en auth.py)
app.add_url_rule('/google-login', endpoint='google_login', view_func=_auth.google_login)


# Health check y verificación de entorno (sin filtrar secretos)
@app.route('/health')
def health_check():
    import os as _os
    def _bool_env(name, default=False):
        val = _os.getenv(name)
        if val is None:
            return default
        return str(val).lower() in ("1", "true", "yes", "on")

    # Estado DB
    db_status = 'unknown'
    http_code = 200
    try:
        db.engine.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        logger.error(f"Health check DB failed: {e}")
        db_status = f'unavailable: {e}'
        http_code = 500

    # Entorno
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    is_sqlite = 'sqlite' in (uri or '')
    is_mysql = 'mysql' in (uri or '')

    static_dir = app.static_folder
    instance_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'instance')

    def _is_writable(path):
        try:
            return _os.path.isdir(path) and _os.access(path, _os.W_OK)
        except Exception:
            return False

    env_report = {
        'flask_env': _os.getenv('FLASK_ENV', 'unset'),
        'secret_key_from_env': bool(_os.getenv('SECRET_KEY')),
        'database_url_set': bool(_os.getenv('DATABASE_URL')),
        'db_uri_kind': 'sqlite' if is_sqlite else ('mysql' if is_mysql else 'other'),
        'static_folder_exists': _os.path.isdir(static_dir),
        'static_folder_writable': _is_writable(static_dir),
        'instance_exists': _os.path.isdir(instance_dir),
        'instance_writable': _is_writable(instance_dir),
        'smtp': {
            'host_set': bool(_os.getenv('SMTP_HOST')),
            'user_set': bool(_os.getenv('SMTP_USER')),
            'password_set': bool(_os.getenv('SMTP_PASSWORD')),
            'use_tls': _bool_env('SMTP_USE_TLS', True),
            'use_ssl': _bool_env('SMTP_USE_SSL', False),
        },
        'google_oauth': {
            'client_id_set': bool(_os.getenv('GOOGLE_CLIENT_ID')),
            'client_secret_set': bool(_os.getenv('GOOGLE_CLIENT_SECRET')),
        },
    }

    return {
        'status': 'healthy' if http_code == 200 else 'unhealthy',
        'database': db_status,
        'env': env_report,
        'static_folder': static_dir,
        'timestamp': str(datetime.now())
    }, http_code

# Aliases para el administrador (dashboard restaurante)
#from routes import admin as _admin
#app.add_url_rule('/admin/restaurante', endpoint='admin_restaurante', view_func=_admin.admin_restaurante)
#app.add_url_rule('/admin/restaurante/nuevo', endpoint='admin_restaurante_nuevo', view_func=_admin.admin_restaurante_nuevo, methods=['GET','POST'])
#app.add_url_rule('/admin/restaurante/editar/<int:plato_id>', endpoint='admin_restaurante_editar', view_func=_admin.admin_restaurante_editar, methods=['GET','POST'])
#app.add_url_rule('/admin/restaurante/eliminar/<int:plato_id>', endpoint='admin_restaurante_eliminar', view_func=_admin.admin_restaurante_eliminar, methods=['POST'])


# ------------------- Configuración de logs -------------------
# Ya configurado arriba; evitamos reconfigurar para no duplicar handlers y mensajes.

# ------------------- Ejecución de la aplicación -------------------

# Servir archivos de medios dinámicos desde instance/uploads
@app.route('/media/<path:filename>')
def media_file(filename):
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'uploads')
    # Seguridad básica: normalizar y restringir a carpeta
    return send_from_directory(base, filename, conditional=True)

# Manejador para archivos estáticos faltantes - proveer fallback
@app.errorhandler(404)
def handle_not_found(e):
    """Maneja archivos estáticos faltantes con fallbacks apropiados."""
    try:
        # Solo aplicar para rutas estáticas
        if request.path.startswith('/static/'):
            # Fallback para imágenes faltantes
            if any(request.path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                logger.warning(f"Imagen estática faltante: {request.path}")
                # Redirigir a imagen por defecto
                return redirect(url_for('static', filename='img/OIP.webp'))
            
            # Fallback para iconos faltantes
            elif request.path.endswith('.ico'):
                logger.warning(f"Icono faltante: {request.path}")
                return redirect(url_for('static', filename='favicon.ico'))
            
            # Para otros archivos estáticos, registrar el error
            logger.warning(f"Archivo estático faltante: {request.path}")
    
    except Exception:
        pass
    
    # Para todas las demás 404, comportamiento normal
    return make_response(
        "<h1>Página no encontrada (404)</h1>"
        "<p>La página que buscas no existe.</p>"
        f"<p><a href='{url_for('home')}'>Volver al inicio</a></p>",
        404
    )

# ------------------- Manejadores y utilidades de diagnóstico -------------------
from flask import request, make_response

@app.errorhandler(400)
def handle_bad_request(e):
    """Registra detalles cuando ocurre un 400 antes de entrar a las vistas.
    Suele deberse a cabeceras Cookie inválidas o corruptas enviadas por el navegador.
    """
    try:
        logger.warning(
            '400 BadRequest en %s UA=%s CookieLen=%s Referer=%s',
            request.path,
            request.headers.get('User-Agent'),
            len(request.headers.get('Cookie', '')),
            request.headers.get('Referer')
        )
        # No logueamos el valor completo de Cookie por privacidad; si se requiere, activar temporalmente:
        # logger.debug('Cookie completa: %r', request.headers.get('Cookie'))
    except Exception:
        pass

    html = (
        "<h1>Solicitud inválida (400)</h1>"
        "<p>Es posible que tu navegador esté enviando cookies antiguas o dañadas para este dominio. "
        "Prueba estos pasos y vuelve a intentarlo:</p>"
        "<ol>"
        "<li>Abre una ventana InPrivate/Incógnito y verifica si funciona.</li>"
        "<li><a href='/{clear}'>Haz clic aquí para limpiar cookies de este sitio</a> (no cierra tu sesión en otros sitios).</li>"
        "<li>Como alternativa, borra los datos del sitio desde la configuración del navegador.</li>"
        "</ol>"
    ).format(clear='__clear_cookies')
    resp = make_response(html, 400)
    return resp

@app.route('/__clear_cookies')
def __clear_cookies():
    """Borra cookies típicas de la app para mitigar errores 400 por cookies corruptas."""
    next_url = request.args.get('next') or url_for('home')
    resp = make_response(redirect(next_url))
    for name in ('session', 'remember_token', 'csrftoken', 'csrf_token'):
        try:
            resp.delete_cookie(name, domain=None)
            # Muchos navegadores guardan cookies con dominio de nivel superior; intentamos ambos.
            resp.delete_cookie(name, domain='.' + request.host.split(':')[0])
        except Exception:
            pass
    return resp

@app.errorhandler(500)
def handle_internal_error(e):
    """Registra el traceback para 500 y muestra un mensaje amigable con un ID de incidente."""
    import traceback, uuid
    incident = uuid.uuid4().hex[:8]
    try:
        tb = traceback.format_exc()
        logger.exception('500 Internal Server Error [%s] en %s UA=%s\n%s', incident, request.path, request.headers.get('User-Agent'), tb)
    except Exception:
        pass
    html = (
        "<h1>Internal Server Error</h1>"
        "<p>Ocurrió un error inesperado al procesar tu solicitud.</p>"
        "<p>ID de incidente: <strong>{incident}</strong></p>"
        "<p>Por favor intenta nuevamente o contacta al soporte indicando el ID.</p>"
    ).format(incident=incident)
    return make_response(html, 500)

if __name__ == '__main__':
    import os
    
    # En desarrollo usa el servidor de Flask
    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # En producción, usar Gunicorn es más seguro
        app.run(debug=False, host='0.0.0.0', port=5000)

