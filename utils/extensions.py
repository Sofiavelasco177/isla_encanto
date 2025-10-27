from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer

db = SQLAlchemy()
bcrypt = Bcrypt()
serializer = None  # se inicializa en run.py después de crear app
