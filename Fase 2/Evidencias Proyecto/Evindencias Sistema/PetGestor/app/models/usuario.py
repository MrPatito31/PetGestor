"""Modelo de administradores/empleados del sistema."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id        = db.Column(db.Integer, primary_key=True)
    nombre    = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(150), unique=True, nullable=False, index=True)
    _password = db.Column("password_hash", db.String(256), nullable=False)
    rol       = db.Column(db.Enum("admin", "empleado"), nullable=False, default="empleado")
    activo    = db.Column(db.Boolean, default=True, nullable=False)

    creado_en     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ultimo_acceso = db.Column(db.DateTime, nullable=True)

    @property
    def password(self):
        raise AttributeError("La contraseña no es legible directamente.")

    @password.setter
    def password(self, plain_text: str):
        self._password = generate_password_hash(plain_text)

    def verificar_password(self, plain_text: str) -> bool:
        return check_password_hash(self._password, plain_text)

    def es_admin(self) -> bool:
        return self.rol == "admin"

    def __init__(
        self,
        nombre: str,
        email: str,
        rol: str = "empleado",
        activo: bool = True,
        password: str | None = None,
    ):
        self.nombre = nombre
        self.email = email
        self.rol = rol
        self.activo = activo
        if password:
            self.password = password

    def __repr__(self):
        return f"<Usuario {self.email} [{self.rol}]>"
