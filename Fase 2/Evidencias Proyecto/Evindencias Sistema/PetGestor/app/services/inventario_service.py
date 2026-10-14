"""Control de stock e inventario."""
import logging
from typing import Optional

from app import db
from app.models.inventario import Producto, MovimientoInventario

logger = logging.getLogger(__name__)


class StockInsuficienteError(Exception):
    """Se lanza cuando se intenta descontar más stock del disponible."""
    pass


def registrar_entrada(
    producto_id: int,
    cantidad: int,
    motivo: Optional[str] = None,
    registrado_por_id: Optional[int] = None,
) -> dict:
    """Registra entrada de stock (compra/reposición). Retorna producto actualizado."""
    if cantidad <= 0:
        raise ValueError("La cantidad de entrada debe ser mayor a 0.")

    producto = Producto.query.get(producto_id)
    if not producto:
        raise ValueError(f"Producto id={producto_id} no encontrado.")

    producto.stock_actual += cantidad
    stock_nuevo = producto.stock_actual

    movimiento = MovimientoInventario(
        producto_id       = producto_id,
        tipo              = "entrada",
        cantidad          = cantidad,
        stock_resultante  = stock_nuevo,
        motivo            = motivo or "Entrada de stock",
        registrado_por_id = registrado_por_id,
    )
    db.session.add(movimiento)
    db.session.commit()

    logger.info(f"Entrada: +{cantidad} a producto #{producto_id}. Stock: {stock_nuevo}")

    return {
        "producto":       producto,
        "stock_nuevo":    stock_nuevo,
        "alerta_critico": producto.en_stock_critico,
    }


def registrar_salida(
    producto_id: int,
    cantidad: int,
    motivo: Optional[str] = None,
    cita_id: Optional[int] = None,
    registrado_por_id: Optional[int] = None,
) -> dict:
    """Registra salida de stock. Lanza StockInsuficienteError si no hay stock."""
    if cantidad <= 0:
        raise ValueError("La cantidad de salida debe ser mayor a 0.")

    producto = Producto.query.get(producto_id)
    if not producto:
        raise ValueError(f"Producto id={producto_id} no encontrado.")

    if producto.stock_actual < cantidad:
        raise StockInsuficienteError(
            f"Stock insuficiente para '{producto.nombre}'. "
            f"Disponible: {producto.stock_actual}, Solicitado: {cantidad}."
        )

    producto.stock_actual -= cantidad
    stock_nuevo = producto.stock_actual

    movimiento = MovimientoInventario(
        producto_id       = producto_id,
        tipo              = "salida",
        cantidad          = cantidad,
        stock_resultante  = stock_nuevo,
        motivo            = motivo or "Consumo operativo",
        cita_id           = cita_id,
        registrado_por_id = registrado_por_id,
    )
    db.session.add(movimiento)
    db.session.commit()

    alerta = producto.en_stock_critico
    if alerta:
        logger.warning(
            f"STOCK CRITICO: '{producto.nombre}' registra {stock_nuevo} unidades "
            f"(mínimo: {producto.stock_minimo})."
        )

    return {
        "producto":       producto,
        "stock_nuevo":    stock_nuevo,
        "alerta_critico": alerta,
        "mensaje_alerta": (
            f"Nivel crítico de inventario: '{producto.nombre}' registra solo {stock_nuevo} unidad(es). "
            f"Se sugiere reabastecimiento."
        ) if alerta else None,
    }


def obtener_productos_en_alerta() -> list:
    """Productos con stock en nivel crítico (para panel de alertas del admin)."""
    return (
        Producto.query
        .filter(
            Producto.activo == True,  # noqa: E712
            Producto.stock_actual <= Producto.stock_minimo
        )
        .order_by(Producto.stock_actual.asc())
        .all()
    )


def ajustar_stock(
    producto_id: int,
    nuevo_stock: int,
    motivo: str,
    registrado_por_id: Optional[int] = None,
) -> Producto:
    """Ajuste manual de stock (corrección por inventario físico)."""
    producto = Producto.query.get(producto_id)
    if not producto:
        raise ValueError(f"Producto id={producto_id} no encontrado.")

    diferencia = nuevo_stock - producto.stock_actual
    producto.stock_actual = nuevo_stock

    movimiento = MovimientoInventario(
        producto_id       = producto_id,
        tipo              = "ajuste",
        cantidad          = abs(diferencia),
        stock_resultante  = nuevo_stock,
        motivo            = f"Ajuste manual: {motivo} (diferencia: {diferencia:+d})",
        registrado_por_id = registrado_por_id,
    )
    db.session.add(movimiento)
    db.session.commit()

    logger.info(f"Ajuste de stock: producto #{producto_id} -> {nuevo_stock} ({diferencia:+d})")
    return producto
