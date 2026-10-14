"""Rutas del portal público (cliente)."""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

from app import db
from app.models.cliente import Cliente, Mascota
from app.models.cita import Servicio
import app.services.citas_service as citas_service
import app.services.chat_service as chat_service

cliente_bp = Blueprint("cliente", __name__, template_folder="../templates")


@cliente_bp.route("/")
def inicio():
    """Página principal del portal público."""
    servicios = Servicio.query.filter_by(activo=True).all()
    return render_template("cliente/inicio.html", servicios=servicios)


@cliente_bp.route("/servicios")
def servicios():
    """Listado de servicios disponibles con precios."""
    servicios = Servicio.query.filter_by(activo=True).all()
    return render_template("cliente/servicios.html", servicios=servicios)


@cliente_bp.route("/horarios-disponibles")
def horarios_disponibles():
    """API: bloques horarios disponibles. Params: fecha (YYYY-MM-DD), servicio_id."""
    fecha_str    = request.args.get("fecha")
    servicio_id  = request.args.get("servicio_id", type=int)

    if not fecha_str or not servicio_id:
        return jsonify({"error": "Parámetros 'fecha' y 'servicio_id' requeridos."}), 400

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD."}), 400

    horarios = citas_service.obtener_horarios_disponibles(fecha, servicio_id)
    return jsonify({"fecha": fecha_str, "disponibles": horarios})


@cliente_bp.route("/agendar", methods=["GET", "POST"])
def agendar():
    """Formulario de agendamiento. GET muestra el form, POST lo procesa."""
    servicios = Servicio.query.filter_by(activo=True).all()

    if request.method == "POST":
        nombre        = request.form.get("nombre", "").strip()
        rut           = request.form.get("rut", "").strip()
        telefono      = request.form.get("telefono", "").strip()
        email         = request.form.get("email", "").strip()
        nombre_mascota = request.form.get("nombre_mascota", "").strip()
        especie       = request.form.get("especie", "Perro")
        raza          = request.form.get("raza", "").strip()
        servicio_id   = request.form.get("servicio_id", type=int)
        fecha_hora_str = request.form.get("fecha_hora", "").strip()
        notas         = request.form.get("notas", "").strip()

        if not all([nombre, rut, telefono, nombre_mascota, servicio_id, fecha_hora_str]):
            flash("Todos los campos marcados son obligatorios.", "danger")
            return render_template("cliente/agendar.html", servicios=servicios)

        try:
            fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Formato de fecha y hora inválido.", "danger")
            return render_template("cliente/agendar.html", servicios=servicios)

        if fecha_hora <= datetime.now():
            flash("La cita debe ser en el futuro.", "danger")
            return render_template("cliente/agendar.html", servicios=servicios)

        try:
            cliente = Cliente.query.filter_by(rut=rut).first()
            if not cliente:
                cliente = Cliente(nombre=nombre, rut=rut, telefono=telefono, email=email)
                db.session.add(cliente)
                db.session.flush()
            else:
                cliente.telefono = telefono
                if email:
                    cliente.email = email

            mascota = Mascota(
                cliente_id = cliente.id,
                nombre     = nombre_mascota,
                especie    = especie,
                raza       = raza or None,
            )
            db.session.add(mascota)
            db.session.flush()

            nueva_cita = citas_service.crear_cita(
                cliente_id        = cliente.id,
                mascota_id        = mascota.id,
                servicio_id       = servicio_id,
                fecha_hora_inicio = fecha_hora,
                notas_cliente     = notas,
            )

            db.session.commit()

            flash(
                f"Cita solicitada exitosamente para el "
                f"{nueva_cita.fecha_hora_inicio.strftime('%d/%m/%Y a las %H:%M')} hrs. "
                f"Se enviará la confirmación vía WhatsApp.",
                "success"
            )
            return redirect(url_for("cliente.inicio"))

        except citas_service.CitaConflictoError as e:
            db.session.rollback()
            flash(str(e), "danger")
        except ValueError as e:
            db.session.rollback()
            flash(f"Error en los datos ingresados: {str(e)}", "danger")
        except Exception as e:
            db.session.rollback()
            flash("Ocurrió un error inesperado. Por favor intente nuevamente.", "danger")

    return render_template("cliente/agendar.html", servicios=servicios)



@cliente_bp.route("/chat", methods=["GET", "POST"])
def chat():
    """Interfaz de chat para consultas del cliente."""
    return render_template("cliente/chat.html")


@cliente_bp.route("/chat/iniciar", methods=["POST"])
def chat_iniciar():
    """API: Inicia una nueva conversación."""
    data   = request.get_json() or request.form
    nombre = data.get("nombre", "").strip()
    asunto = data.get("asunto", "Consulta general").strip()

    if not nombre:
        return jsonify({"error": "El nombre es requerido."}), 400

    conv = chat_service.iniciar_conversacion(
        asunto           = asunto,
        nombre_visitante = nombre,
        telefono_visitante = data.get("telefono", ""),
    )

    return jsonify({"conversacion_id": conv.id, "mensaje": "Conversación iniciada."})


@cliente_bp.route("/chat/<int:conv_id>/enviar", methods=["POST"])
def chat_enviar(conv_id: int):
    """API: Envía un mensaje del cliente y obtiene respuesta automática si existe."""
    data   = request.get_json() or request.form
    texto  = data.get("mensaje", "").strip()

    if not texto:
        return jsonify({"error": "El mensaje no puede estar vacío."}), 400

    resultado = chat_service.procesar_mensaje_cliente(conv_id, texto)

    return jsonify({
        "mensaje_enviado":      True,
        "respuesta_automatica": resultado["respuesta_automatica"],
        "requiere_admin":       resultado["requiere_atencion_admin"],
        "mensaje_espera": (
            "Su consulta ha sido registrada. Un asesor le responderá a la brevedad."
            if resultado["requiere_atencion_admin"] else None
        ),
    })
