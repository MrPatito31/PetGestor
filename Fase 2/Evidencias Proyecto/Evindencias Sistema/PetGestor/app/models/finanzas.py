"""
app/models/finanzas.py — Modelos de Ingresos, Egresos y Categorías.
Permite registrar movimientos de caja y calcular balance diario.
"""
from datetime import datetime, timezone, date
from decimal import Decimal
from app import db


class CategoriaFinanciera(db.Model):
    """
    Categorías para clasificar ingresos y egresos.
    Ejemplos de ingresos: 'Servicio peluquería', 'Venta producto'.
    Ejemplos de egresos:  'Compra insumos', 'Arriendo', 'Servicios básicos'.
    """
    __tablename__ = "categorias_financieras"

    id    = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    tipo   = db.Column(db.Enum("ingreso", "egreso"), nullable=False)

    ingresos = db.relationship("Ingreso", backref="categoria", lazy="dynamic")
    egresos  = db.relationship("Egreso",  backref="categoria", lazy="dynamic")

    def __init__(
        self,
        nombre: str,
        tipo: str,
    ):
        self.nombre = nombre
        self.tipo = tipo

    def __repr__(self):
        return f"<CategoriaFinanciera {self.nombre} [{self.tipo}]>"


class Ingreso(db.Model):
    """
    Registro de un ingreso de caja.
    Puede estar asociado a una cita (cobro por servicio) o ser independiente.
    """
    __tablename__ = "ingresos"

    id           = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_financieras.id"), nullable=True)
    cita_id      = db.Column(db.Integer, db.ForeignKey("citas.id"), nullable=True)

    monto        = db.Column(db.Numeric(12, 2), nullable=False)
    descripcion  = db.Column(db.String(255), nullable=True)
    fecha        = db.Column(db.Date, nullable=False, index=True)
    metodo_pago  = db.Column(
        db.Enum("efectivo", "transferencia", "debito", "credito", "otro"),
        nullable=False,
        default="efectivo"
    )

    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        monto: Decimal | float,
        descripcion: str | None = None,
        fecha: date | None = None,
        categoria_id: int | None = None,
        cita_id: int | None = None,
        metodo_pago: str = "efectivo",
        registrado_por_id: int | None = None,
    ):
        self.monto = monto
        self.descripcion = descripcion
        self.fecha = fecha
        self.categoria_id = categoria_id
        self.cita_id = cita_id
        self.metodo_pago = metodo_pago
        self.registrado_por_id = registrado_por_id

    def __repr__(self):
        return f"<Ingreso ${self.monto} {self.fecha}>"


class Egreso(db.Model):
    """
    Registro de un egreso o gasto operativo.
    """
    __tablename__ = "egresos"

    id           = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias_financieras.id"), nullable=True)

    monto        = db.Column(db.Numeric(12, 2), nullable=False)
    descripcion  = db.Column(db.String(255), nullable=False)
    fecha        = db.Column(db.Date, nullable=False, index=True)
    comprobante  = db.Column(db.String(200), nullable=True)  # Número de boleta/factura

    registrado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        monto: Decimal | float,
        descripcion: str,
        fecha: date | None = None,
        categoria_id: int | None = None,
        comprobante: str | None = None,
        registrado_por_id: int | None = None,
    ):
        self.monto = monto
        self.descripcion = descripcion
        self.fecha = fecha
        self.categoria_id = categoria_id
        self.comprobante = comprobante
        self.registrado_por_id = registrado_por_id

    def __repr__(self):
        return f"<Egreso ${self.monto} {self.fecha}>"
