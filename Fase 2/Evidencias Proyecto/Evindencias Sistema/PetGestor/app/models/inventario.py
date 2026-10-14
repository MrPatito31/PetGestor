"""Modelos de Productos e Inventario."""
from datetime import datetime, timezone
from app import db


class Producto(db.Model):
    __tablename__ = "productos"

    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(120), nullable=False)
    descripcion   = db.Column(db.Text, nullable=True)
    categoria     = db.Column(db.String(80), nullable=True)
    unidad        = db.Column(db.String(30), nullable=False, default="unidad")
    stock_actual  = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo  = db.Column(db.Integer, nullable=False, default=3)
    precio_compra = db.Column(db.Numeric(10, 2), nullable=True)
    activo        = db.Column(db.Boolean, default=True, nullable=False)
    creado_en     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    movimientos = db.relationship(
        "MovimientoInventario", backref="producto", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        nombre: str,
        descripcion: str | None = None,
        categoria: str | None = None,
        unidad: str = "unidad",
        stock_actual: int = 0,
        stock_minimo: int = 3,
        precio_compra: float | None = None,
        activo: bool = True,
    ):
        self.nombre        = nombre
        self.descripcion   = descripcion
        self.categoria     = categoria
        self.unidad        = unidad
        self.stock_actual  = stock_actual
        self.stock_minimo  = stock_minimo
        self.precio_compra = precio_compra
        self.activo        = activo

    @property
    def en_stock_critico(self) -> bool:
        return self.stock_actual <= self.stock_minimo

    def __repr__(self):
        return f"<Producto {self.nombre} stock:{self.stock_actual}>"


TIPOS_MOVIMIENTO = ("entrada", "salida", "ajuste")


class MovimientoInventario(db.Model):
    __tablename__ = "movimientos_inventario"

    id                = db.Column(db.Integer, primary_key=True)
    producto_id       = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    tipo              = db.Column(db.Enum(*TIPOS_MOVIMIENTO), nullable=False)
    cantidad          = db.Column(db.Integer, nullable=False)
    stock_resultante  = db.Column(db.Integer, nullable=False)
    motivo            = db.Column(db.String(200), nullable=True)
    cita_id           = db.Column(db.Integer, db.ForeignKey("citas.id"), nullable=True)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    registrado_en     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        producto_id: int,
        tipo: str,
        cantidad: int,
        stock_resultante: int,
        motivo: str | None = None,
        cita_id: int | None = None,
        registrado_por_id: int | None = None,
    ):
        self.producto_id       = producto_id
        self.tipo              = tipo
        self.cantidad          = cantidad
        self.stock_resultante  = stock_resultante
        self.motivo            = motivo
        self.cita_id           = cita_id
        self.registrado_por_id = registrado_por_id

    def __repr__(self):
        return f"<Movimiento {self.tipo} {self.cantidad}u prod:{self.producto_id}>"
