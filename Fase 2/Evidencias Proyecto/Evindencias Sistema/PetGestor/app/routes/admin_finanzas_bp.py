"""
app/routes/admin_finanzas_bp.py — Blueprint de gestión de caja y finanzas.
Rutas: /admin/finanzas/
"""
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

import app.services.finanzas_service as finanzas_service

admin_finanzas_bp = Blueprint("admin_finanzas", __name__, template_folder="../templates")


@admin_finanzas_bp.route("/")
@login_required
def index():
    """Dashboard de caja con balance del día actual."""
    balance = finanzas_service.calcular_balance_diario()
    ingresos_hoy = finanzas_service.obtener_ingresos_del_dia()
    egresos_hoy  = finanzas_service.obtener_egresos_del_dia()

    return render_template(
        "admin/finanzas/index.html",
        balance=balance,
        ingresos=ingresos_hoy,
        egresos=egresos_hoy,
    )


@admin_finanzas_bp.route("/ingreso", methods=["POST"])
@login_required
def registrar_ingreso():
    """Registra un nuevo ingreso de caja."""
    try:
        monto       = request.form.get("monto", 0, type=float)
        descripcion = request.form.get("descripcion", "").strip()
        metodo_pago = request.form.get("metodo_pago", "efectivo")
        fecha_str   = request.form.get("fecha", "")

        fecha = date.fromisoformat(fecha_str) if fecha_str else None

        finanzas_service.registrar_ingreso(
            monto             = monto,
            descripcion       = descripcion,
            fecha             = fecha,
            metodo_pago       = metodo_pago,
            registrado_por_id = current_user.id,
        )
        flash(f"Ingreso de ${monto:,.0f} registrado correctamente.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("admin_finanzas.index"))


@admin_finanzas_bp.route("/egreso", methods=["POST"])
@login_required
def registrar_egreso():
    """Registra un nuevo egreso de caja."""
    try:
        monto       = request.form.get("monto", 0, type=float)
        descripcion = request.form.get("descripcion", "").strip()
        fecha_str   = request.form.get("fecha", "")
        comprobante = request.form.get("comprobante", "").strip()

        if not descripcion:
            flash("La descripción del egreso es obligatoria.", "danger")
            return redirect(url_for("admin_finanzas.index"))

        fecha = date.fromisoformat(fecha_str) if fecha_str else None

        finanzas_service.registrar_egreso(
            monto             = monto,
            descripcion       = descripcion,
            fecha             = fecha,
            comprobante       = comprobante or None,
            registrado_por_id = current_user.id,
        )
        flash(f"Egreso de ${monto:,.0f} registrado correctamente.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("admin_finanzas.index"))


@admin_finanzas_bp.route("/balance-rango")
@login_required
def balance_rango():
    """
    API JSON con balance para un rango de fechas.
    GET /admin/finanzas/balance-rango?desde=2024-12-01&hasta=2024-12-31
    """
    desde_str = request.args.get("desde", "")
    hasta_str = request.args.get("hasta", "")

    try:
        desde = date.fromisoformat(desde_str)
        hasta = date.fromisoformat(hasta_str)
    except ValueError:
        return jsonify({"error": "Formato de fechas inválido. Use YYYY-MM-DD."}), 400

    balance = finanzas_service.calcular_balance_rango(desde, hasta)
    return jsonify(balance)


@admin_finanzas_bp.route("/reporte")
@login_required
def reporte():
    """Vista de reporte mensual con gráfico de ingresos vs egresos."""
    desde_str = request.args.get("desde", "")
    hasta_str = request.args.get("hasta", "")

    hoy   = date.today()
    desde = date.fromisoformat(desde_str) if desde_str else date(hoy.year, hoy.month, 1)
    hasta = date.fromisoformat(hasta_str) if hasta_str else hoy

    balance = finanzas_service.calcular_balance_rango(desde, hasta)

    return render_template(
        "admin/finanzas/reporte.html",
        balance=balance,
        desde=desde,
        hasta=hasta,
    )
