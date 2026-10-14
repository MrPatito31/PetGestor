"""Lógica de caja y finanzas."""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func

from app import db
from app.models.finanzas import Ingreso, Egreso, CategoriaFinanciera

logger = logging.getLogger(__name__)



def registrar_ingreso(
    monto: float,
    descripcion: Optional[str] = None,
    fecha: Optional[date] = None,
    categoria_id: Optional[int] = None,
    cita_id: Optional[int] = None,
    metodo_pago: str = "efectivo",
    registrado_por_id: Optional[int] = None,
) -> Ingreso:
    """Registra un ingreso en caja. Usa la fecha de hoy si no se indica."""
    if monto <= 0:
        raise ValueError("El monto del ingreso debe ser mayor a 0.")

    ingreso = Ingreso(
        monto             = Decimal(str(monto)),
        descripcion       = descripcion,
        fecha             = fecha or date.today(),
        categoria_id      = categoria_id,
        cita_id           = cita_id,
        metodo_pago       = metodo_pago,
        registrado_por_id = registrado_por_id,
    )
    db.session.add(ingreso)
    db.session.commit()

    logger.info(f"Ingreso registrado: ${monto} — {descripcion}")
    return ingreso


def registrar_egreso(
    monto: float,
    descripcion: str,
    fecha: Optional[date] = None,
    categoria_id: Optional[int] = None,
    comprobante: Optional[str] = None,
    registrado_por_id: Optional[int] = None,
) -> Egreso:
    """Registra un egreso."""
    if monto <= 0:
        raise ValueError("El monto del egreso debe ser mayor a 0.")

    egreso = Egreso(
        monto             = Decimal(str(monto)),
        descripcion       = descripcion,
        fecha             = fecha or date.today(),
        categoria_id      = categoria_id,
        comprobante       = comprobante,
        registrado_por_id = registrado_por_id,
    )
    db.session.add(egreso)
    db.session.commit()

    logger.info(f"Egreso registrado: ${monto} — {descripcion}")
    return egreso



def calcular_balance_diario(fecha: Optional[date] = None) -> dict:
    """Balance de caja para un día. Retorna ingresos, egresos, ganancia y es_positivo."""
    dia = fecha or date.today()

    total_ingresos = (
        db.session.query(func.sum(Ingreso.monto))
        .filter(Ingreso.fecha == dia)
        .scalar() or Decimal("0")
    )

    total_egresos = (
        db.session.query(func.sum(Egreso.monto))
        .filter(Egreso.fecha == dia)
        .scalar() or Decimal("0")
    )

    ganancia = total_ingresos - total_egresos

    return {
        "fecha":          dia,
        "total_ingresos": total_ingresos,
        "total_egresos":  total_egresos,
        "ganancia":       ganancia,
        "es_positivo":    ganancia >= 0,
    }


def calcular_balance_rango(fecha_inicio: date, fecha_fin: date) -> dict:
    """Balance acumulado por rango de fechas, con desglose diario."""
    total_ingresos = (
        db.session.query(func.sum(Ingreso.monto))
        .filter(Ingreso.fecha.between(fecha_inicio, fecha_fin))
        .scalar() or Decimal("0")
    )

    total_egresos = (
        db.session.query(func.sum(Egreso.monto))
        .filter(Egreso.fecha.between(fecha_inicio, fecha_fin))
        .scalar() or Decimal("0")
    )

    ingresos_por_dia = (
        db.session.query(Ingreso.fecha, func.sum(Ingreso.monto).label("total"))
        .filter(Ingreso.fecha.between(fecha_inicio, fecha_fin))
        .group_by(Ingreso.fecha)
        .all()
    )

    egresos_por_dia = (
        db.session.query(Egreso.fecha, func.sum(Egreso.monto).label("total"))
        .filter(Egreso.fecha.between(fecha_inicio, fecha_fin))
        .group_by(Egreso.fecha)
        .all()
    )

    mapa_ingresos = {row.fecha: row.total for row in ingresos_por_dia}
    mapa_egresos  = {row.fecha: row.total for row in egresos_por_dia}

    todas_fechas = sorted(set(mapa_ingresos.keys()) | set(mapa_egresos.keys()))

    dias = []
    for dia in todas_fechas:
        ing = mapa_ingresos.get(dia, Decimal("0"))
        egr = mapa_egresos.get(dia, Decimal("0"))
        dias.append({
            "fecha":    dia.isoformat(),
            "ingresos": float(ing),
            "egresos":  float(egr),
            "ganancia": float(ing - egr),
        })

    return {
        "fecha_inicio":  fecha_inicio.isoformat(),
        "fecha_fin":     fecha_fin.isoformat(),
        "total_ingresos": float(total_ingresos),
        "total_egresos":  float(total_egresos),
        "ganancia_neta":  float(total_ingresos - total_egresos),
        "es_positivo":    total_ingresos >= total_egresos,
        "dias":           dias,
    }


def obtener_ingresos_del_dia(fecha: Optional[date] = None) -> list[Ingreso]:
    """Ingresos del día."""
    dia = fecha or date.today()
    return Ingreso.query.filter(Ingreso.fecha == dia).order_by(Ingreso.creado_en.desc()).all()


def obtener_egresos_del_dia(fecha: Optional[date] = None) -> list[Egreso]:
    """Egresos del día."""
    dia = fecha or date.today()
    return Egreso.query.filter(Egreso.fecha == dia).order_by(Egreso.creado_en.desc()).all()
