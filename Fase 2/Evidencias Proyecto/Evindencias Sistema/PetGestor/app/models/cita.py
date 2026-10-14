"""Modelos de Citas y Servicios."""
from datetime import datetime, timezone
from app import db


class Servicio(db.Model):
    __tablename__ = "servicios"

    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(100), nullable=False, unique=True)
    descripcion  = db.Column(db.Text, nullable=True)
    precio       = db.Column(db.Numeric(10, 2), nullable=False)
    duracion_min = db.Column(db.Integer, nullable=False, default=60)
    activo       = db.Column(db.Boolean, default=True, nullable=False)

    citas = db.relationship("Cita", backref="servicio", lazy="dynamic")

    def __init__(self, nombre: str, precio: float, duracion_min: int = 60, descripcion: str | None = None, activo: bool = True):
        self.nombre       = nombre
        self.precio       = precio
        self.duracion_min = duracion_min
        self.descripcion  = descripcion
        self.activo       = activo

    def __repr__(self):
        return f"<Servicio {self.nombre} ${self.precio}>"


ESTADOS_CITA = ("pendiente", "confirmada", "en_proceso", "finalizada", "cancelada")


class Cita(db.Model):
    __tablename__ = "citas"

    id          = db.Column(db.Integer, primary_key=True)
    cliente_id  = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    mascota_id  = db.Column(db.Integer, db.ForeignKey("mascotas.id"), nullable=False)
    servicio_id = db.Column(db.Integer, db.ForeignKey("servicios.id"), nullable=False)

    fecha_hora_inicio = db.Column(db.DateTime, nullable=False, index=True)
    fecha_hora_fin    = db.Column(db.DateTime, nullable=False)

    estado = db.Column(db.Enum(*ESTADOS_CITA), nullable=False, default="pendiente")

    notas_cliente    = db.Column(db.Text, nullable=True)
    notas_admin      = db.Column(db.Text, nullable=True)
    precio_final     = db.Column(db.Numeric(10, 2), nullable=True)
    whatsapp_enviado = db.Column(db.Boolean, default=False)

    creado_en      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    actualizado_en = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.Index("ix_citas_fecha_estado", "fecha_hora_inicio", "estado"),
    )

    def __init__(
        self,
        cliente_id: int,
        mascota_id: int,
        servicio_id: int,
        fecha_hora_inicio: datetime,
        fecha_hora_fin: datetime,
        precio_final: float | None = None,
        notas_cliente: str | None = None,
        notas_admin: str | None = None,
        estado: str = "pendiente",
        whatsapp_enviado: bool = False,
    ):
        self.cliente_id       = cliente_id
        self.mascota_id       = mascota_id
        self.servicio_id      = servicio_id
        self.fecha_hora_inicio = fecha_hora_inicio
        self.fecha_hora_fin   = fecha_hora_fin
        self.precio_final     = precio_final
        self.notas_cliente    = notas_cliente
        self.notas_admin      = notas_admin
        self.estado           = estado
        self.whatsapp_enviado = whatsapp_enviado

    @property
    def esta_activa(self) -> bool:
        return self.estado in ("pendiente", "confirmada", "en_proceso")

    def __repr__(self):
        return f"<Cita #{self.id} {self.fecha_hora_inicio} [{self.estado}]>"
