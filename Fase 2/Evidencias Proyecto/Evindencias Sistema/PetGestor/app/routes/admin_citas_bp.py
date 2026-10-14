"""Rutas de administración de citas y servicios."""
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required

from app import db
from app.models.cita import Cita, Servicio
from app.models.cliente import Cliente
import app.services.citas_service as citas_service
import app.services.whatsapp_service as whatsapp_service

admin_citas_bp = Blueprint("admin_citas", __name__, template_folder="../templates")


@admin_citas_bp.route("/")
@login_required
def index():
    """Dashboard de citas — muestra todas las citas ordenadas por fecha."""
    estado_filtro = request.args.get("estado", "todas")
    fecha_filtro  = request.args.get("fecha", "")

    query = Cita.query.order_by(Cita.fecha_hora_inicio.asc())

    if estado_filtro != "todas":
        query = query.filter(Cita.estado == estado_filtro)

    if fecha_filtro:

        try:
            fecha = datetime.strptime(fecha_filtro, "%Y-%m-%d").date()
            query = query.filter(
                Cita.fecha_hora_inicio >= datetime.combine(fecha, datetime.min.time()),
                Cita.fecha_hora_inicio <  datetime.combine(fecha, datetime.max.time()),
            )
        except ValueError:
            pass

    citas = query.all()
    return render_template(
        "admin/citas/index.html",
        citas=citas,
        estado_filtro=estado_filtro,
        fecha_filtro=fecha_filtro,
    )


@admin_citas_bp.route("/<int:cita_id>")
@login_required
def detalle(cita_id: int):
    """Detalle completo de una cita."""
    cita = Cita.query.get_or_404(cita_id)
    link_whatsapp = whatsapp_service.generar_link_whatsapp_directo(cita)
    return render_template("admin/citas/detalle.html", cita=cita, link_whatsapp=link_whatsapp)


@admin_citas_bp.route("/<int:cita_id>/reenviar-whatsapp", methods=["POST"])
@login_required
def reenviar_whatsapp(cita_id: int):
    """Prueba o reenvía la notificación de Twilio para la cita."""
    cita = Cita.query.get_or_404(cita_id)
    resultado = whatsapp_service.enviar_confirmacion_cita(cita, forzar=True)
    if resultado["exito"]:
        flash(f"Notificación enviada con éxito vía Twilio (SID: {resultado.get('sid')}).", "success")
    else:
        flash(f"Error al enviar por Twilio: {resultado['error']}", "warning")
    return redirect(url_for("admin_citas.detalle", cita_id=cita_id))


@admin_citas_bp.route("/<int:cita_id>/cambiar-estado", methods=["POST"])
@login_required
def cambiar_estado(cita_id: int):
    """
    Cambia el estado de una cita.
    Si el nuevo estado es 'confirmada', dispara el envío del WhatsApp.
    """
    nuevo_estado = request.form.get("estado")
    notas_admin  = request.form.get("notas_admin", "").strip()

    try:
        cita = citas_service.cambiar_estado_cita(cita_id, nuevo_estado, notas_admin or None)

        # ── Disparar WhatsApp al confirmar ─────────────────────────────────────
        if nuevo_estado == "confirmada":
            resultado_wa = whatsapp_service.enviar_confirmacion_cita(cita)
            if resultado_wa["exito"]:
                flash("Cita confirmada y notificación de WhatsApp enviada al cliente.", "success")
            else:
                flash(
                    f"Cita confirmada. No fue posible enviar la notificación de WhatsApp: {resultado_wa['error']}",
                    "warning"
                )
        else:
            flash(f"Estado de la cita actualizado a '{nuevo_estado}'.", "success")

    except (ValueError, citas_service.CitaNoEncontradaError) as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("admin_citas.detalle", cita_id=cita_id))


@admin_citas_bp.route("/disponibilidad")
@login_required
def verificar_disponibilidad():
    """
    API JSON para verificar disponibilidad (usada por el admin al re-agendar).
    GET /admin/citas/disponibilidad?fecha_hora=2024-12-15T10:00&servicio_id=1&excluir_id=5
    """


    fecha_hora_str = request.args.get("fecha_hora", "")
    servicio_id    = request.args.get("servicio_id", type=int)
    excluir_id     = request.args.get("excluir_id", type=int)

    if not fecha_hora_str or not servicio_id:
        return jsonify({"error": "Parámetros requeridos."}), 400

    try:
        fecha_hora  = datetime.fromisoformat(fecha_hora_str)
        disponible  = citas_service.verificar_disponibilidad(fecha_hora, servicio_id, excluir_id)
        conflictos  = [] if disponible else [
            {"id": c.id, "inicio": c.fecha_hora_inicio.isoformat()}
            for c in citas_service.obtener_citas_conflicto(fecha_hora, servicio_id, excluir_id)
        ]
        return jsonify({"disponible": disponible, "conflictos": conflictos})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400



@admin_citas_bp.route("/servicios")
@login_required
def servicios():
    """Catálogo de servicios disponibles."""
    lista_servicios = Servicio.query.order_by(Servicio.nombre.asc()).all()
    return render_template("admin/citas/servicios.html", servicios=lista_servicios)


@admin_citas_bp.route("/servicios/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_servicio():
    """Registra un nuevo servicio en el catálogo."""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio = request.form.get("precio", type=float)
        duracion_min = request.form.get("duracion_min", 60, type=int)

        if not nombre or precio is None or precio <= 0 or duracion_min <= 0:
            flash("Todos los campos obligatorios deben ser válidos.", "danger")
            return render_template("admin/citas/nuevo_servicio.html")

        if Servicio.query.filter_by(nombre=nombre).first():
            flash(f"Ya existe un servicio con el nombre '{nombre}'.", "danger")
            return render_template("admin/citas/nuevo_servicio.html")

        servicio = Servicio(
            nombre=nombre,
            descripcion=descripcion or None,
            precio=precio,
            duracion_min=duracion_min,
            activo=True,
        )
        db.session.add(servicio)
        db.session.commit()
        flash(f"Servicio '{nombre}' registrado correctamente.", "success")
        return redirect(url_for("admin_citas.servicios"))

    return render_template("admin/citas/nuevo_servicio.html")


@admin_citas_bp.route("/servicios/<int:servicio_id>/editar", methods=["GET", "POST"])
@login_required
def editar_servicio(servicio_id: int):
    """Edita un servicio existente."""
    servicio = Servicio.query.get_or_404(servicio_id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio = request.form.get("precio", type=float)
        duracion_min = request.form.get("duracion_min", type=int)

        if not nombre or precio is None or precio <= 0 or duracion_min <= 0:
            flash("Todos los campos obligatorios deben ser válidos.", "danger")
            return render_template("admin/citas/editar_servicio.html", servicio=servicio)

        existente = Servicio.query.filter_by(nombre=nombre).first()
        if existente and existente.id != servicio.id:
            flash(f"Ya existe otro servicio con el nombre '{nombre}'.", "danger")
            return render_template("admin/citas/editar_servicio.html", servicio=servicio)

        servicio.nombre = nombre
        servicio.descripcion = descripcion or None
        servicio.precio = precio
        servicio.duracion_min = duracion_min
        db.session.commit()
        flash(f"Servicio '{nombre}' actualizado correctamente.", "success")
        return redirect(url_for("admin_citas.servicios"))

    return render_template("admin/citas/editar_servicio.html", servicio=servicio)


@admin_citas_bp.route("/servicios/<int:servicio_id>/toggle", methods=["POST"])
@login_required
def toggle_servicio(servicio_id: int):
    """Activa o desactiva un servicio."""
    servicio = Servicio.query.get_or_404(servicio_id)
    servicio.activo = not servicio.activo
    db.session.commit()
    estado = "activado" if servicio.activo else "desactivado"
    flash(f"Servicio '{servicio.nombre}' {estado}.", "success")
    return redirect(url_for("admin_citas.servicios"))
