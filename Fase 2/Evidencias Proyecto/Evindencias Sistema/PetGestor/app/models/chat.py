"""Modelos de Chat: Conversaciones, Mensajes y FAQs."""
from datetime import datetime, timezone
from app import db


class Conversacion(db.Model):
    __tablename__ = "conversaciones"

    id                 = db.Column(db.Integer, primary_key=True)
    cliente_id         = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=True)
    nombre_visitante   = db.Column(db.String(100), nullable=True)
    telefono_visitante = db.Column(db.String(20), nullable=True)
    estado             = db.Column(db.Enum("abierta", "respondida", "archivada"), nullable=False, default="abierta")
    asunto             = db.Column(db.String(200), nullable=True)
    creado_en          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    actualizado_en     = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    mensajes = db.relationship(
        "Mensaje", backref="conversacion", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Mensaje.enviado_en"
    )

    def __init__(
        self,
        asunto: str | None = None,
        nombre_visitante: str | None = None,
        telefono_visitante: str | None = None,
        cliente_id: int | None = None,
        estado: str = "abierta",
    ):
        self.asunto             = asunto
        self.nombre_visitante   = nombre_visitante
        self.telefono_visitante = telefono_visitante
        self.cliente_id         = cliente_id
        self.estado             = estado

    def __repr__(self):
        return f"<Conversacion #{self.id} [{self.estado}]>"


class Mensaje(db.Model):
    __tablename__ = "mensajes"

    id              = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey("conversaciones.id"), nullable=False)
    origen          = db.Column(db.Enum("cliente", "sistema", "admin"), nullable=False, default="cliente")
    contenido       = db.Column(db.Text, nullable=False)
    es_automatico   = db.Column(db.Boolean, default=False)
    leido           = db.Column(db.Boolean, default=False)
    enviado_en      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __init__(self, conversacion_id: int, contenido: str, origen: str = "cliente", es_automatico: bool = False, leido: bool = False):
        self.conversacion_id = conversacion_id
        self.contenido       = contenido
        self.origen          = origen
        self.es_automatico   = es_automatico
        self.leido           = leido

    def __repr__(self):
        return f"<Mensaje [{self.origen}] conv:{self.conversacion_id}>"


class FaqRespuesta(db.Model):
    """Base de conocimiento para respuestas automáticas. keywords separadas por coma."""
    __tablename__ = "faq_respuestas"

    id        = db.Column(db.Integer, primary_key=True)
    pregunta  = db.Column(db.String(255), nullable=False)
    keywords  = db.Column(db.Text, nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    activo    = db.Column(db.Boolean, default=True, nullable=False)
    prioridad = db.Column(db.Integer, default=0)
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, pregunta: str, keywords: str, respuesta: str, activo: bool = True, prioridad: int = 0):
        self.pregunta  = pregunta
        self.keywords  = keywords
        self.respuesta = respuesta
        self.activo    = activo
        self.prioridad = prioridad

    @property
    def lista_keywords(self) -> list[str]:
        return [kw.strip().lower() for kw in self.keywords.split(",") if kw.strip()]

    def __repr__(self):
        return f"<FAQ '{self.pregunta[:40]}...'>"
