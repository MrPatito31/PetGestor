"""
app/routes/admin_inventario_bp.py — Blueprint de gestión de inventario.
Rutas: /admin/inventario/
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.models.inventario import Producto, MovimientoInventario
import app.services.inventario_service as inventario_service

admin_inventario_bp = Blueprint("admin_inventario", __name__, template_folder="../templates")


@admin_inventario_bp.route("/")
@login_required
def index():
    """Dashboard de inventario con alertas de stock crítico."""
    productos          = Producto.query.filter_by(activo=True).order_by(Producto.nombre).all()
    productos_en_alerta = inventario_service.obtener_productos_en_alerta()
    return render_template(
        "admin/inventario/index.html",
        productos=productos,
        alertas=productos_en_alerta,
    )


@admin_inventario_bp.route("/alertas")
@login_required
def alertas():
    """Lista solo los productos en stock crítico."""
    productos = inventario_service.obtener_productos_en_alerta()
    return render_template("admin/inventario/alertas.html", productos=productos)


@admin_inventario_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_producto():
    """Formulario para registrar un nuevo producto/insumo."""
    if request.method == "POST":
        nombre       = request.form.get("nombre", "").strip()
        descripcion  = request.form.get("descripcion", "").strip()
        categoria    = request.form.get("categoria", "").strip()
        unidad       = request.form.get("unidad", "unidad").strip()
        stock_actual = request.form.get("stock_actual", 0, type=int)
        stock_minimo = request.form.get("stock_minimo", 3, type=int)
        precio_compra = request.form.get("precio_compra", type=float)

        if not nombre:
            flash("El nombre del producto es obligatorio.", "danger")
            return render_template("admin/inventario/nuevo.html")

        producto = Producto(
            nombre        = nombre,
            descripcion   = descripcion or None,
            categoria     = categoria or None,
            unidad        = unidad,
            stock_actual  = stock_actual,
            stock_minimo  = stock_minimo,
            precio_compra = precio_compra,
        )
        db.session.add(producto)
        db.session.commit()
        flash(f"Producto '{nombre}' registrado con inventario inicial de {stock_actual} {unidad}(s).", "success")
        return redirect(url_for("admin_inventario.index"))

    return render_template("admin/inventario/nuevo.html")


@admin_inventario_bp.route("/<int:producto_id>/entrada", methods=["POST"])
@login_required
def registrar_entrada(producto_id: int):
    """Registra una entrada de stock (reposición)."""
    cantidad = request.form.get("cantidad", 0, type=int)
    motivo   = request.form.get("motivo", "").strip()

    try:
        resultado = inventario_service.registrar_entrada(
            producto_id       = producto_id,
            cantidad          = cantidad,
            motivo            = motivo or None,
            registrado_por_id = current_user.id,
        )
        flash(f"Entrada registrada. Inventario actual: {resultado['stock_nuevo']}.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("admin_inventario.index"))


@admin_inventario_bp.route("/<int:producto_id>/salida", methods=["POST"])
@login_required
def registrar_salida(producto_id: int):
    """Registra una salida de stock (consumo)."""
    cantidad = request.form.get("cantidad", 0, type=int)
    motivo   = request.form.get("motivo", "").strip()

    try:
        resultado = inventario_service.registrar_salida(
            producto_id       = producto_id,
            cantidad          = cantidad,
            motivo            = motivo or None,
            registrado_por_id = current_user.id,
        )
        flash(f"Salida registrada. Inventario actual: {resultado['stock_nuevo']}.", "success")
        if resultado["alerta_critico"]:
            flash(resultado["mensaje_alerta"], "warning")
    except (ValueError, inventario_service.StockInsuficienteError) as e:
        flash(str(e), "danger")

    return redirect(url_for("admin_inventario.index"))
