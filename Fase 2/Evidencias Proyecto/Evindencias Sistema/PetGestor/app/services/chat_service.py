"""Motor de respuestas automáticas FAQ y gestión de chat."""
import re
import unicodedata
import logging
from typing import Optional

from app import db
from app.models.chat import Conversacion, Mensaje, FaqRespuesta
from app.models.cliente import Cliente

logger = logging.getLogger(__name__)



def _normalizar(texto: str) -> str:
    """Normaliza texto: minúsculas, sin tildes, sin caracteres especiales."""
    texto = texto.lower()
    # Descomponer caracteres acentuados (á -> a + ́)
    texto = unicodedata.normalize("NFD", texto)
    # Filtrar los caracteres de combinación (diacríticos)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # Eliminar caracteres que no sean letras, números o espacios
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    # Reducir múltiples espacios a uno
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto



def buscar_respuesta_automatica(texto_mensaje: str) -> Optional[str]:
    """Busca respuesta FAQ para el mensaje. Retorna texto o None si no hay coincidencia."""
    texto_normalizado = _normalizar(texto_mensaje)

    faqs = (
        FaqRespuesta.query
        .filter_by(activo=True)
        .order_by(FaqRespuesta.prioridad.desc())
        .all()
    )

    for faq in faqs:
        for keyword in faq.lista_keywords:
            keyword_norm = _normalizar(keyword)
            # (ej: "precio" no debe activar si el texto dice "aprecio")
            patron = r"\b" + re.escape(keyword_norm) + r"\b"
            if re.search(patron, texto_normalizado):
                logger.debug(f"FAQ match: keyword='{keyword}' en FAQ #{faq.id}")
                return faq.respuesta

    return None  # Sin coincidencia → el admin debe responder manualmente



def iniciar_conversacion(
    asunto: str,
    nombre_visitante: Optional[str] = None,
    telefono_visitante: Optional[str] = None,
    cliente_id: Optional[int] = None,
) -> Conversacion:
    """
    Crea una nueva conversación de consulta.
    Puede ser de un cliente registrado o de un visitante anónimo.
    """
    conv = Conversacion(
        asunto             = asunto,
        nombre_visitante   = nombre_visitante,
        telefono_visitante = telefono_visitante,
        cliente_id         = cliente_id,
        estado             = "abierta",
    )
    db.session.add(conv)
    db.session.commit()
    return conv


def procesar_mensaje_cliente(conversacion_id: int, texto: str) -> dict:
    """
    Procesa un mensaje enviado por un cliente:
      1. Guarda el mensaje del cliente.
      2. Busca una respuesta automática.
      3. Si hay respuesta, la guarda como mensaje del sistema.
      4. Devuelve el resultado con la respuesta (o indicador de espera).

    Returns:
        dict con:
          - 'mensaje_guardado': el Mensaje del cliente
          - 'respuesta_automatica': str o None
          - 'requiere_atencion_admin': bool
    """
    conv = Conversacion.query.get(conversacion_id)
    if not conv:
        raise ValueError(f"Conversación #{conversacion_id} no encontrada.")

    msg_cliente = Mensaje(
        conversacion_id = conversacion_id,
        origen          = "cliente",
        contenido       = texto,
        es_automatico   = False,
    )
    db.session.add(msg_cliente)

    respuesta_texto = buscar_respuesta_automatica(texto)
    requiere_admin  = True

    if respuesta_texto:
        msg_sistema = Mensaje(
            conversacion_id = conversacion_id,
            origen          = "sistema",
            contenido       = respuesta_texto,
            es_automatico   = True,
        )
        db.session.add(msg_sistema)
        conv.estado = "respondida"
        requiere_admin = False
    else:
        conv.estado = "abierta"

    db.session.commit()

    return {
        "mensaje_guardado":      msg_cliente,
        "respuesta_automatica":  respuesta_texto,
        "requiere_atencion_admin": requiere_admin,
    }


def responder_como_admin(conversacion_id: int, texto: str, admin_id: int) -> Mensaje:
    """Guarda respuesta del admin y cambia estado a respondida."""
    conv = Conversacion.query.get(conversacion_id)
    if not conv:
        raise ValueError(f"Conversación #{conversacion_id} no encontrada.")

    msg = Mensaje(
        conversacion_id = conversacion_id,
        origen          = "admin",
        contenido       = texto,
        es_automatico   = False,
    )
    db.session.add(msg)
    conv.estado = "respondida"
    db.session.commit()

    return msg


def obtener_conversaciones_pendientes() -> list[Conversacion]:
    """Devuelve las conversaciones abiertas para la bandeja del admin."""
    return (
        Conversacion.query
        .filter_by(estado="abierta")
        .order_by(Conversacion.actualizado_en.desc())
        .all()
    )


def marcar_mensajes_leidos(conversacion_id: int) -> int:
    """Marca como leídos todos los mensajes no leídos de la conversación."""
    actualizados = (
        Mensaje.query
        .filter_by(conversacion_id=conversacion_id, leido=False)
        .update({"leido": True})
    )
    db.session.commit()
    return actualizados



def crear_faq(pregunta: str, keywords: str, respuesta: str, prioridad: int = 0) -> FaqRespuesta:
    """Crea una nueva entrada en la base de conocimiento FAQ."""
    faq = FaqRespuesta(
        pregunta  = pregunta,
        keywords  = keywords,
        respuesta = respuesta,
        prioridad = prioridad,
    )
    db.session.add(faq)
    db.session.commit()
    return faq


def poblar_faqs_iniciales():
    """Carga FAQs iniciales. Llamar solo una vez al inicializar la BD."""
    faqs_iniciales = [
        {
            "pregunta":  "¿Cuáles son los precios?",
            "keywords":  "precio,costo,cuanto,cuánto,valor,cobran,cobras,tarifa",
            "respuesta": (
                "Nuestras tarifas varían según la raza, tamaño de la mascota y el servicio requerido:\n"
                "  • Baño básico: desde $8.000\n"
                "  • Corte y baño: desde $12.000\n"
                "  • Peluquería integral: desde $18.000\n\n"
                "Para una cotización exacta, por favor indique la raza y tamaño de su mascota."
            ),
            "prioridad": 10,
        },
        {
            "pregunta":  "¿Cuál es el horario de atención?",
            "keywords":  "horario,hora,atienden,abren,cierran,cuando,cuándo,dias,días",
            "respuesta": (
                "Nuestro horario de atención es:\n"
                "  • Lunes a viernes: 09:00 a 18:00 hrs\n"
                "  • Sábado: 09:00 a 14:00 hrs\n"
                "  • Domingo y festivos: Cerrado\n\n"
                "Puede agendar su hora directamente en nuestro sitio web."
            ),
            "prioridad": 9,
        },
        {
            "pregunta":  "¿Dónde están ubicados?",
            "keywords":  "donde,dónde,ubicacion,ubicación,direccion,dirección,llegar,mapa,sector",
            "respuesta": (
                "Nos encontramos en Melipilla, Región Metropolitana.\n"
                "Para indicaciones de llegada o consultas de ubicación, "
                "contáctenos directamente o encuéntrenos como 'PetGestor Melipilla'."
            ),
            "prioridad": 8,
        },
        {
            "pregunta":  "¿Cómo puedo agendar una cita?",
            "keywords":  "agendar,agenda,cita,turno,reservar,reserva,hora,appointment",
            "respuesta": (
                "Puede agendar su cita de las siguientes maneras:\n"
                "  1. A través de nuestro sitio web en la sección 'Agendar Cita'.\n"
                "  2. Mediante este canal de atención indicando sus datos de contacto y los de su mascota."
            ),
            "prioridad": 7,
        },
        {
            "pregunta":  "¿Qué servicios ofrecen?",
            "keywords":  "servicio,servicios,ofrecen,hacen,realizan,incluye,baño,corte,peluqueria,peluquería",
            "respuesta": (
                "Nuestros servicios profesionales incluyen:\n"
                "  • Baño y secado\n"
                "  • Corte de pelo estético y sanitario\n"
                "  • Corte y limado de uñas\n"
                "  • Higiene auricular\n"
                "  • Peluquería integral\n\n"
                "Todos los procedimientos son realizados por personal especializado."
            ),
            "prioridad": 6,
        },
        {
            "pregunta":  "¿Atienden gatos?",
            "keywords":  "gato,gatos,felino,felinos,minino",
            "respuesta": (
                "Sí, disponemos de atención para felinos con protocolos adaptados a su bienestar "
                "y manejo adecuado. Consulte disponibilidad y tarifas para su mascota."
            ),
            "prioridad": 5,
        },
        {
            "pregunta":  "¿Debo llevar algo para la cita?",
            "keywords":  "traer,llevar,necesito,necesita,requisito,requisitos,preparar",
            "respuesta": (
                "Requisitos para la atención:\n"
                "  • Calendario de vacunación al día.\n"
                "  • Presentarse con 5 minutos de anticipación al horario acordado.\n"
                "  • Informar oportunamente si su mascota presenta alergias o condiciones médicas preexistentes."
            ),
            "prioridad": 4,
        },
    ]

    for data in faqs_iniciales:
        existe = FaqRespuesta.query.filter_by(pregunta=data["pregunta"]).first()
        if not existe:
            faq = FaqRespuesta(**data)
            db.session.add(faq)

    db.session.commit()
    logger.info("FAQs iniciales cargadas correctamente.")
