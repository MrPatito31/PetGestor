"""Envío de mensajes de WhatsApp vía UltraMsg."""
import logging
import urllib.parse

import requests
from flask import current_app

from app import db
from app.models.cita import Cita

logger = logging.getLogger(__name__)


# ── Helpers de número ─────────────────────────────────────────────────────────

def _formatear_numero_ultramsg(telefono: str) -> str:
    """Convierte un número chileno al formato internacional sin el prefijo whatsapp:."""
    tel = telefono.replace(" ", "").replace("-", "")

    if tel.startswith("whatsapp:"):
        tel = tel.replace("whatsapp:", "")

    if tel.startswith("+"):
        return tel  # Ya tiene formato +56XXXXXXXXX

    if tel.startswith("0"):
        tel = tel[1:]

    return f"+56{tel}"


def _formatear_numero_wame(telefono: str) -> str:
    """Formatea el número para usar en enlaces wa.me (sin + ni espacios)."""
    tel = _formatear_numero_ultramsg(telefono)
    return tel.replace("+", "")


# ── Construcción de mensajes ──────────────────────────────────────────────────

def _construir_mensaje_confirmacion(cita: Cita) -> str:
    """Arma el texto de confirmación con los datos de la cita."""
    negocio  = current_app.config.get("NEGOCIO_NOMBRE", "PetGestor")
    telefono = current_app.config.get("NEGOCIO_TELEFONO", "")

    fecha_str   = cita.fecha_hora_inicio.strftime("%A %d de %B de %Y")
    hora_inicio = cita.fecha_hora_inicio.strftime("%H:%M")
    hora_fin    = cita.fecha_hora_fin.strftime("%H:%M")

    return (
        f"*{negocio}* — Confirmación de Cita\n\n"
        f"Estimado(a) *{cita.cliente.nombre}*, confirmamos su cita programada:\n\n"
        f"*Detalles del servicio:*\n"
        f"  • Mascota:  {cita.mascota.nombre} ({cita.mascota.especie})\n"
        f"  • Servicio: {cita.servicio.nombre}\n"
        f"  • Fecha:    {fecha_str}\n"
        f"  • Horario:  {hora_inicio} a {hora_fin} hrs\n"
        f"  • Valor:    ${cita.precio_final:,.0f}\n\n"
        f"*Dirección:* {current_app.config.get('NEGOCIO_DIRECCION', '')}\n\n"
        f"Para modificaciones o cancelaciones, contáctenos al {telefono}.\n\n"
        f"Agradecemos su preferencia."
    )


# ── Enlace directo WhatsApp Web ───────────────────────────────────────────────

def generar_link_whatsapp_directo(cita: Cita) -> str:
    """Genera un enlace wa.me para abrir WhatsApp Web o App con el mensaje listo."""
    if not cita.cliente or not cita.cliente.telefono:
        return ""
    tel = _formatear_numero_wame(cita.cliente.telefono)
    mensaje = _construir_mensaje_confirmacion(cita)
    return f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje)}"


# ── Backend UltraMsg ──────────────────────────────────────────────────────────

def _enviar_ultramsg(numero_destino: str, mensaje: str) -> dict:
    """Envía un mensaje a través de la API REST de UltraMsg."""
    instance = current_app.config.get("ULTRAMSG_INSTANCE", "")
    token    = current_app.config.get("ULTRAMSG_TOKEN", "")

    if not instance or not token:
        return {"exito": False, "error": "UltraMsg no configurado (falta ULTRAMSG_INSTANCE o ULTRAMSG_TOKEN en .env)."}

    url = f"https://api.ultramsg.com/{instance}/messages/chat"
    payload = {
        "token": token,
        "to":    numero_destino,
        "body":  mensaje,
    }

    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # UltraMsg devuelve {"sent": "true", "id": "...", "message": "ok"}
        if str(data.get("sent", "")).lower() == "true":
            return {"exito": True, "id": data.get("id", "")}
        else:
            return {"exito": False, "error": data.get("message", "Respuesta inesperada de UltraMsg.")}

    except requests.exceptions.Timeout:
        return {"exito": False, "error": "Tiempo de espera agotado al contactar UltraMsg."}
    except requests.exceptions.RequestException as e:
        return {"exito": False, "error": f"Error de red: {e}"}
    except Exception as e:
        return {"exito": False, "error": f"Error inesperado: {e}"}


# ── Funciones públicas ────────────────────────────────────────────────────────

def enviar_confirmacion_cita(cita: Cita, forzar: bool = False) -> dict:
    """Envía confirmación de WhatsApp al cliente vía UltraMsg. Evita reenvíos salvo forzar=True."""
    if cita.whatsapp_enviado and not forzar:
        logger.info(f"WhatsApp ya enviado para cita #{cita.id}, omitiendo.")
        return {"exito": False, "error": "Mensaje ya enviado anteriormente."}

    if not cita.cliente.telefono:
        return {"exito": False, "error": "El cliente no tiene teléfono registrado."}

    numero  = _formatear_numero_ultramsg(cita.cliente.telefono)
    mensaje = _construir_mensaje_confirmacion(cita)

    resultado = _enviar_ultramsg(numero, mensaje)

    if resultado["exito"]:
        cita.whatsapp_enviado = True
        db.session.commit()
        logger.info(f"WhatsApp enviado para cita #{cita.id}. ID UltraMsg: {resultado.get('id')}")
    else:
        logger.error(f"Error UltraMsg cita #{cita.id}: {resultado.get('error')}")

    return resultado


def enviar_recordatorio_cita(cita: Cita) -> dict:
    """Envía recordatorio 24h antes de la cita (llamar desde scheduler)."""
    if not cita.cliente.telefono:
        return {"exito": False, "error": "El cliente no tiene teléfono registrado."}

    negocio = current_app.config.get("NEGOCIO_NOMBRE", "PetGestor")
    mensaje = (
        f"*{negocio}* — Recordatorio de Cita\n\n"
        f"Estimado(a) *{cita.cliente.nombre}*, le recordamos su cita para mañana:\n\n"
        f"  • Mascota: {cita.mascota.nombre} ({cita.servicio.nombre})\n"
        f"  • Horario: {cita.fecha_hora_inicio.strftime('%H:%M')} hrs\n\n"
        f"Le solicitamos presentarse con 5 minutos de anticipación."
    )

    numero = _formatear_numero_ultramsg(cita.cliente.telefono)
    return _enviar_ultramsg(numero, mensaje)
