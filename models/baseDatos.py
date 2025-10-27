from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from utils.extensions import db
"""
Los modelos usan la configuración de SQLAlchemy definida en Flask (app.config['SQLALCHEMY_DATABASE_URI']).
No definir URIs aquí para permitir seleccionar MySQL o SQLite desde variables de entorno.
"""

# ------------------------------
# Tabla de Usuario
# ------------------------------
class Usuario(db.Model):
    __tablename__ = 'usuario'
    idUsuario = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(255), nullable=False)
    correo = db.Column(db.String(255), nullable=True, unique=True)
    contrasena = db.Column(db.String(255), nullable=False)  
    direccion = db.Column(db.String(255), nullable=True)
    fechaNacimiento = db.Column(db.Date, nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    rol = db.Column(db.String(20), nullable=True, default='usuario')
    # Perfil de usuario extendido
    plan_tipo = db.Column(db.String(50), nullable=True)  # Ej: Oro, Plata, Premium
    membresia_activa = db.Column(db.Boolean, default=False)
    membresia_expira = db.Column(db.Date, nullable=True)
    notif_checkin = db.Column(db.Boolean, default=True)
    notif_checkout = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Usuario {self.usuario}>"


# ------------------------------
# Tabla de nuevaHabitaciones
# ------------------------------
class nuevaHabitacion(db.Model):
    __tablename__ = "nuevaHabitacion"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    # Plan de habitación: Oro, Plata, (Bronce en futuro)
    plan = db.Column(db.String(20), nullable=True, index=True)
    # Número de habitación dentro del plan/piso
    numero = db.Column(db.Integer, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    # Características detalladas (JSON serializado o texto)
    caracteristicas = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="Disponible")
    cupo_personas = db.Column(db.Integer, nullable=False, default=1)
    imagen = db.Column(db.String(255), nullable=True)  # Ruta de la imagen
    model3d = db.Column(db.String(255), nullable=True)  # URL del modelo 3D

    def __repr__(self):
        return f"<nuevaHabitacion {self.nombre} - {self.estado}>"
    
    
# ------------------------------
# Inventario por Habitación
# ------------------------------
class InventarioHabitacion(db.Model):
    __tablename__ = 'inventario_habitacion'

    id = db.Column(db.Integer, primary_key=True)
    habitacion_id = db.Column(db.Integer, db.ForeignKey('nuevaHabitacion.id'), nullable=True)
    hotel = db.Column(db.String(100), nullable=True)
    room_number = db.Column(db.String(50), nullable=True)
    room_type = db.Column(db.String(50), nullable=True)
    inspection_date = db.Column(db.Date, nullable=True)
    inspector = db.Column(db.String(100), nullable=True)
    observations = db.Column(db.Text, nullable=True)
    rating_cleaning = db.Column(db.Integer, nullable=True)
    rating_furniture = db.Column(db.Integer, nullable=True)
    rating_equipment = db.Column(db.Integer, nullable=True)
    inspector_signature = db.Column(db.String(120), nullable=True)
    inspector_date = db.Column(db.Date, nullable=True)
    supervisor_signature = db.Column(db.String(120), nullable=True)
    supervisor_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('InventarioItem', backref='record', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f"<InventarioHabitacion {self.id} hab={self.habitacion_id} fecha={self.inspection_date}>"


class InventarioItem(db.Model):
    __tablename__ = 'inventario_item'

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('inventario_habitacion.id'), nullable=False)
    category = db.Column(db.String(60), nullable=True)
    key = db.Column(db.String(60), nullable=False)
    label = db.Column(db.String(120), nullable=True)
    checked = db.Column(db.Boolean, default=False)
    quantity = db.Column(db.Integer, nullable=True)
    value_text = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<InventarioItem {self.key} checked={self.checked} qty={self.quantity}>"


# ------------------------------
# Tabla de habitacioneHuesped
# ------------------------------
  
class habitacionHuesped(db.Model):
    __tablename__ = "habitacionHuesped"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad_personas = db.Column(db.Integer, nullable=False, default=1)
    check_in = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    check_out = db.Column(db.Date, nullable=True)
    

    def __repr__(self):
        return f"<HabitacionHuesped {self.nombre} - {self.check_in} to {self.check_out}>"
    
    
    
# ------------------------------
# Tabla de Huéspedes
# ------------------------------
class Huesped(db.Model):
    __tablename__ = "huesped"

    idHuesped = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipoDocumento = db.Column(db.String(50), nullable=False)
    numeroDocumento = db.Column(db.Integer, nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=True)
    correo = db.Column(db.String(255), nullable=True)
    procedencia = db.Column(db.String(100), nullable=True)
    nuevaHabitacion_id = db.Column(db.Integer, db.ForeignKey("nuevaHabitacion.id"), nullable=False)
    

    def __repr__(self):
        return f"<Huesped {self.nombre} en habitacionHuesped {self.habitacionHuesped_id}>"
    


class PerfilAdmin(db.Model):
    __tablename__ = 'perfil_admin'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(100), nullable=False)
    empresa = db.Column(db.String(100), nullable=False)
    supervisor = db.Column(db.String(100), nullable=True)
    suplente = db.Column(db.String(100), nullable=True)
    tipo_contrato = db.Column(db.String(100), nullable=False)
    fecha_ingreso = db.Column(db.Date, nullable=False)
    # Relación con usuario
    usuario = db.relationship('Usuario', backref='perfil_admin', uselist=False)

    def __repr__(self):
        return f"<PerfilAdmin {self.usuario_id} - {self.cargo}>"

# ------------------------------
# Métodos de Pago
# ------------------------------
class MetodoPago(db.Model):
    __tablename__ = 'metodo_pago'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    marca = db.Column(db.String(50), nullable=True)     # Visa, MasterCard, etc.
    ultimos4 = db.Column(db.String(4), nullable=True)
    tipo = db.Column(db.String(20), nullable=True)      # tarjeta, paypal, etc.
    exp_mes = db.Column(db.Integer, nullable=True)
    exp_anio = db.Column(db.Integer, nullable=True)
    provider_ref = db.Column(db.String(120), nullable=True)
    predeterminado = db.Column(db.Boolean, default=False)

# ------------------------------
# Reservas de Usuario
# ------------------------------
class Reserva(db.Model):
    __tablename__ = 'reserva'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    habitacion_id = db.Column(db.Integer, db.ForeignKey('nuevaHabitacion.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='Activa')  # Activa, Completada, Cancelada
    total = db.Column(db.Float, nullable=True)


# ------------------------------
# Datos de huéspedes capturados al reservar (antes del pago)
# ------------------------------
class ReservaDatosHospedaje(db.Model):
    __tablename__ = 'reserva_datos_hospedaje'

    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reserva.id'), nullable=False, unique=True)
    # Huésped titular
    nombre1 = db.Column(db.String(100), nullable=False)
    tipo_doc1 = db.Column(db.String(50), nullable=False)
    num_doc1 = db.Column(db.String(50), nullable=False)
    telefono1 = db.Column(db.String(20), nullable=True)
    correo1 = db.Column(db.String(255), nullable=True)
    procedencia1 = db.Column(db.String(100), nullable=True)
    # Acompañante (opcional)
    nombre2 = db.Column(db.String(100), nullable=True)
    tipo_doc2 = db.Column(db.String(50), nullable=True)
    num_doc2 = db.Column(db.String(50), nullable=True)
    telefono2 = db.Column(db.String(20), nullable=True)
    correo2 = db.Column(db.String(255), nullable=True)
    procedencia2 = db.Column(db.String(100), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


# ------------------------------
# Facturas (archivos descargables)
# ------------------------------
class Factura(db.Model):
    __tablename__ = 'factura'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reserva.id'), nullable=True)
    file_path = db.Column(db.String(255), nullable=False)  # relativo a static o ruta absoluta
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


# ------------------------------
# Ticket de Hospedaje (descargable tras pago)
# ------------------------------
class TicketHospedaje(db.Model):
    __tablename__ = 'ticket_hospedaje'

    id = db.Column(db.Integer, primary_key=True)
    ticket_numero = db.Column(db.String(50), nullable=False, unique=True, index=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reserva.id'), nullable=False, unique=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    habitacion_id = db.Column(db.Integer, db.ForeignKey('nuevaHabitacion.id'), nullable=False)
    habitacion_numero = db.Column(db.String(50), nullable=True)
    # Datos huéspedes
    nombre1 = db.Column(db.String(100), nullable=False)
    tipo_doc1 = db.Column(db.String(50), nullable=False)
    num_doc1 = db.Column(db.String(50), nullable=False)
    telefono1 = db.Column(db.String(20), nullable=True)
    correo1 = db.Column(db.String(255), nullable=True)
    procedencia1 = db.Column(db.String(100), nullable=True)
    nombre2 = db.Column(db.String(100), nullable=True)
    tipo_doc2 = db.Column(db.String(50), nullable=True)
    num_doc2 = db.Column(db.String(50), nullable=True)
    telefono2 = db.Column(db.String(20), nullable=True)
    correo2 = db.Column(db.String(255), nullable=True)
    procedencia2 = db.Column(db.String(100), nullable=True)
    # Fechas y total
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    total = db.Column(db.Float, nullable=False, default=0)
    # Archivo PDF generado
    file_ticket = db.Column(db.String(255), nullable=True)  # ruta relativa (instance/uploads/tickets_hospedaje/...)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------------------
# Notificaciones
# ------------------------------
class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # checkin, checkout, sistema, etc.
    mensaje = db.Column(db.String(255), nullable=False)
    leido = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------------------
# Actividad de Usuario
# ------------------------------
class ActividadUsuario(db.Model):
    __tablename__ = 'actividad_usuario'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=False)
    accion = db.Column(db.String(100), nullable=False)
    detalle = db.Column(db.String(255), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

# ------------------------------
# Experiencias y Reseñas
# ------------------------------
class Experiencia(db.Model):
    __tablename__ = 'experiencia'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    imagen = db.Column(db.String(255), nullable=True)  # ruta relativa (instance/uploads/ o static)
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Experiencia {self.titulo} activo={self.activo}>"


class ResenaExperiencia(db.Model):
    __tablename__ = 'resena_experiencia'

    id = db.Column(db.Integer, primary_key=True)
    experiencia_id = db.Column(db.Integer, db.ForeignKey('experiencia.id'), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=True)
    contenido = db.Column(db.Text, nullable=False)
    calificacion = db.Column(db.Integer, nullable=False, default=0)  # 1..5
    aprobado = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Resena exp={self.experiencia_id} user={self.usuario_id} calif={self.calificacion} apr={self.aprobado}>"

"""# ------------------------------
# Tabla de Restaurantes
# ------------------------------
class Restaurante(db.Model):
    __tablename__ = "restaurantes"

    idRestaurante = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_comida = db.Column(db.String(100), nullable=False)
    horario = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Restaurante {self.nombre}>"
        """

# ------------------------------
# Contenido (Nosotros/Marketing/Descuentos)
# ------------------------------
class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=True)  # marketing, descuento, noticia
    imagen = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Post {self.titulo} cat={self.categoria} activo={self.activo}>"


# ------------------------------
# Menú del Restaurante (CRUD real)
# ------------------------------
class PlatoRestaurante(db.Model):
    __tablename__ = 'plato_restaurante'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.String(300), nullable=True)
    precio = db.Column(db.Float, nullable=False, default=0)
    categoria = db.Column(db.String(50), nullable=True)  # Entradas, Principales, Postres, Bebidas
    icono = db.Column(db.String(120), nullable=True)     # emoji o nombre de icono
    imagen = db.Column(db.String(255), nullable=True)    # ruta relativa a instance/uploads (via /media) o static
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Plato {self.nombre} ${self.precio:.2f} cat={self.categoria}>"


# ------------------------------
# Reservas de Restaurante (mesas) y detalle de pedido
# ------------------------------
class ReservaRestaurante(db.Model):
    __tablename__ = 'reserva_restaurante'

    id = db.Column(db.Integer, primary_key=True)
    # usuario puede ser null si el flujo permite reserva sin login; normalmente usaremos login
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.idUsuario'), nullable=True)
    nombre_cliente = db.Column(db.String(150), nullable=True)
    telefono_cliente = db.Column(db.String(50), nullable=True)
    cupo_personas = db.Column(db.Integer, nullable=False, default=1)
    fecha_reserva = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(30), nullable=False, default='Pendiente')  # Pendiente, Confirmada, Cancelada
    ticket_numero = db.Column(db.String(50), nullable=True, unique=True, index=True)
    total = db.Column(db.Float, nullable=False, default=0)
    file_ticket = db.Column(db.String(255), nullable=True)  # ruta PDF
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('ReservaPlato', backref='reserva', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f"<ReservaRestaurante id={self.id} ticket={self.ticket_numero} total={self.total}>"


class ReservaPlato(db.Model):
    __tablename__ = 'reserva_plato'

    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reserva_restaurante.id'), nullable=False)
    plato_id = db.Column(db.Integer, db.ForeignKey('plato_restaurante.id'), nullable=True)
    nombre_plato = db.Column(db.String(200), nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False, default=0)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Float, nullable=False, default=0)

    def __repr__(self):
        return f"<ReservaPlato {self.nombre_plato} x{self.cantidad} = {self.subtotal}>"