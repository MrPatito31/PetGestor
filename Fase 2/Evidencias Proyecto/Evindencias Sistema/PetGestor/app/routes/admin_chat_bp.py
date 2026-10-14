"""Rutas de bandeja de chat del administrador."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.models.chat import Conversacion, Mensaje, FaqRespuesta
import app.services.chat_service as chat_service
from app import db

admin_chat_bp = Blueprint("admin_chat", __name__, template_folder="../templates")


@admin_chat_bp.route("/")
@login_required
def index():
    """Bandeja de entrada — muestra conversaciones abiertas primero."""
    estado = request.args.get("estado", "abierta")

    if estado == "todas":
        conversaciones = Conversacion.query.order_by(Conversacion.actualizado_en.desc()).all()
    else:
        conversaciones = (
            Conversacion.query
            .filter_by(estado=estado)
            .order_by(Conversacion.actualizado_en.desc())
            .all()
        )

    pendientes_count = Conversacion.query.filter_by(estado="abierta").count()

    return render_template(
        "admin/chat/index.html",
        conversaciones=conversaciones,
        estado_filtro=estado,
        pendientes_count=pendientes_count,
    )


@admin_chat_bp.route("/<int:conv_id>")
@login_required
def detalle(conv_id: int):
    """Vista de conversación completa con todos sus mensajes."""
    conv = Conversacion.query.get_or_404(conv_id)
    chat_service.marcar_mensajes_leidos(conv_id)
    mensajes = conv.mensajes.order_by(Mensaje.enviado_en.asc()).all()
    return render_template("admin/chat/detalle.html", conv=conv, mensajes=mensajes)


@admin_chat_bp.route("/<int:conv_id>/responder", methods=["POST"])
@login_required
def responder(conv_id: int):
    """Responde manualmente a una conversación del cliente."""
    texto = request.form.get("mensaje", "").strip()

    if not texto:
        flash("El mensaje de respuesta no puede estar vacío.", "danger")
        return redirect(url_for("admin_chat.detalle", conv_id=conv_id))

    try:
        chat_service.responder_como_admin(conv_id, texto, current_user.id)
        flash("Respuesta enviada correctamente.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("admin_chat.detalle", conv_id=conv_id))


@admin_chat_bp.route("/<int:conv_id>/archivar", methods=["POST"])
@login_required
def archivar(conv_id: int):
    """Archiva una conversación resuelta."""
    conv = Conversacion.query.get_or_404(conv_id)
    conv.estado = "archivada"
    db.session.commit()
    flash("Conversación archivada exitosamente.", "success")
    return redirect(url_for("admin_chat.index"))



@admin_chat_bp.route("/faqs")
@login_required
def faqs():
    """Lista de respuestas automáticas configuradas."""
    faqs = FaqRespuesta.query.order_by(FaqRespuesta.prioridad.desc()).all()
    return render_template("admin/chat/faqs.html", faqs=faqs)


@admin_chat_bp.route("/faqs/nueva", methods=["GET", "POST"])
@login_required
def nueva_faq():
    """Formulario para agregar una nueva respuesta automática al bot."""
    if request.method == "POST":
        pregunta  = request.form.get("pregunta", "").strip()
        keywords  = request.form.get("keywords", "").strip()
        respuesta = request.form.get("respuesta", "").strip()
        prioridad = request.form.get("prioridad", 0, type=int)

        if not all([pregunta, keywords, respuesta]):
            flash("Todos los campos son obligatorios.", "danger")
            return render_template("admin/chat/nueva_faq.html")

        chat_service.crear_faq(pregunta, keywords, respuesta, prioridad)
        flash(f"Respuesta automática '{pregunta}' agregada al sistema.", "success")
        return redirect(url_for("admin_chat.faqs"))

    return render_template("admin/chat/nueva_faq.html")


@admin_chat_bp.route("/faqs/<int:faq_id>/toggle", methods=["POST"])
@login_required
def toggle_faq(faq_id: int):
    """Activa/desactiva una FAQ sin eliminarla."""
    faq = FaqRespuesta.query.get_or_404(faq_id)
    faq.activo = not faq.activo
    db.session.commit()
    estado = "activada" if faq.activo else "desactivada"
    flash(f"Respuesta automática '{faq.pregunta[:40]}...' {estado}.", "success")
    return redirect(url_for("admin_chat.faqs"))
