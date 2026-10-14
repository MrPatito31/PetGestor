"""Modelos de Clientes y Mascotas."""
from datetime import datetime, timezone
from app import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id        = db.Column(db.Integer, primary_key=True)
    nombre    = db.Column(db.String(100), nullable=False)
    rut       = db.Column(db.String(12), unique=True, nullable=False, index=True)
    telefono  = db.Column(db.String(20), nullable=False)
    email     = db.Column(db.String(150), nullable=True)
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    mascotas       = db.relationship("Mascota", backref="dueño", lazy="dynamic", cascade="all, delete-orphan")
    citas          = db.relationship("Cita", backref="cliente", lazy="dynamic")
    conversaciones = db.relationship("Conversacion", backref="cliente", lazy="dynamic")

    def __init__(self, nombre: str, rut: str, telefono: str, email: str | None = None):
        self.nombre   = nombre
        self.rut      = rut
        self.telefono = telefono
        self.email    = email

    def __repr__(self):
        return f"<Cliente {self.nombre} RUT:{self.rut}>"


ESPECIES_VALIDAS = ("Perro", "Gato", "Otro")


class Mascota(db.Model):
    __tablename__ = "mascotas"

    id         = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    nombre     = db.Column(db.String(80), nullable=False)
    especie    = db.Column(db.Enum(*ESPECIES_VALIDAS), nullable=False, default="Perro")
    raza       = db.Column(db.String(80), nullable=True)
    peso_kg    = db.Column(db.Numeric(5, 2), nullable=True)
    color      = db.Column(db.String(50), nullable=True)
    fecha_nac  = db.Column(db.Date, nullable=True)
    notas      = db.Column(db.Text, nullable=True)
    creado_en  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    citas = db.relationship("Cita", backref="mascota", lazy="dynamic")

    def __init__(
        self,
        cliente_id: int,
        nombre: str,
        especie: str = "Perro",
        raza: str | None = None,
        peso_kg: float | None = None,
        color: str | None = None,
        fecha_nac=None,
        notas: str | None = None,
    ):
        self.cliente_id = cliente_id
        self.nombre     = nombre
        self.especie    = especie
        self.raza       = raza
        self.peso_kg    = peso_kg
        self.color      = color
        self.fecha_nac  = fecha_nac
        self.notas      = notas

    @property
    def edad_anios(self):
        if not self.fecha_nac:
            return None
        return (datetime.now(timezone.utc).date() - self.fecha_nac).days // 365

    def __repr__(self):
        return f"<Mascota {self.nombre} ({self.especie})>"
