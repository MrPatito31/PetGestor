"""Lógica de negocio para gestión de citas.

Detección de solapamiento: A solapa B <=> A.inicio < B.fin AND A.fin > B.inicio
"""
from datetime import datetime, timedelta
from typing import Optional

from app import db
from app.models.cita import Cita, Servicio, ESTADOS_CITA
from app.models.cliente import Cliente, Mascota


ESTADOS_BLOQUEANTES = ("pendiente", "confirmada", "en_proceso")


class CitaConflictoError(Exception):
    """Se lanza cuando el turno solicitado se solapa con una cita existente."""
    pass


class CitaNoEncontradaError(Exception):
    """Se lanza cuando no se encuentra la cita solicitada."""
    pass



def verificar_disponibilidad(
    fecha_hora_inicio: datetime,
    servicio_id: int,
    excluir_cita_id: Optional[int] = None
) -> bool:
    """Devuelve True si el horario está libre, False si hay conflicto."""
    servicio = Servicio.query.get(servicio_id)
    if not servicio:
        raise ValueError(f"Servicio con id={servicio_id} no encontrado.")

    fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=servicio.duracion_min)

    query = Cita.query.filter(
        Cita.estado.in_(ESTADOS_BLOQUEANTES),
        Cita.fecha_hora_inicio < fecha_hora_fin,
        Cita.fecha_hora_fin    > fecha_hora_inicio,
    )

    if excluir_cita_id is not None:
        query = query.filter(Cita.id != excluir_cita_id)

    return query.first() is None


def obtener_citas_conflicto(
    fecha_hora_inicio: datetime,
    servicio_id: int,
    excluir_cita_id: Optional[int] = None
) -> list[Cita]:
    """
    Devuelve la lista de citas que entran en conflicto con el horario propuesto.
    Útil para mostrar un mensaje de error informativo al cliente/admin.
    """
    servicio = Servicio.query.get(servicio_id)
    if not servicio:
        return []

    fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=servicio.duracion_min)

    query = Cita.query.filter(
        Cita.estado.in_(ESTADOS_BLOQUEANTES),
        Cita.fecha_hora_inicio < fecha_hora_fin,
        Cita.fecha_hora_fin    > fecha_hora_inicio,
    )
    if excluir_cita_id is not None:
        query = query.filter(Cita.id != excluir_cita_id)

    return query.all()


def crear_cita(
    cliente_id: int,
    mascota_id: int,
    servicio_id: int,
    fecha_hora_inicio: datetime,
    notas_cliente: Optional[str] = None
) -> Cita:
    """Crea una cita tras validar disponibilidad. Lanza CitaConflictoError si hay conflicto."""
    cliente  = Cliente.query.get(cliente_id)
    mascota  = Mascota.query.get(mascota_id)
    servicio = Servicio.query.get(servicio_id)

    if not cliente:
        raise ValueError(f"Cliente id={cliente_id} no encontrado.")
    if not mascota or mascota.cliente_id != cliente_id:
        raise ValueError("La mascota no pertenece al cliente indicado.")
    if not servicio or not servicio.activo:
        raise ValueError("El servicio no existe o no está disponible.")

    if not verificar_disponibilidad(fecha_hora_inicio, servicio_id):
        conflictos = obtener_citas_conflicto(fecha_hora_inicio, servicio_id)
        raise CitaConflictoError(
            f"El horario {fecha_hora_inicio.strftime('%d/%m/%Y %H:%M')} "
            f"está ocupado. Hay {len(conflictos)} cita(s) en conflicto."
        )

    fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=servicio.duracion_min)

    nueva_cita = Cita(
        cliente_id        = cliente_id,
        mascota_id        = mascota_id,
        servicio_id       = servicio_id,
        fecha_hora_inicio = fecha_hora_inicio,
        fecha_hora_fin    = fecha_hora_fin,
        precio_final      = servicio.precio,
        notas_cliente     = notas_cliente,
        estado            = "pendiente",
    )

    db.session.add(nueva_cita)
    # No hacer commit aquí — el caller controla la transacción para atomicidad
    # (ej: en cliente_bp.agendar se crean cliente + mascota + cita en una sola transacción)

    return nueva_cita


def cambiar_estado_cita(cita_id: int, nuevo_estado: str, notas_admin: Optional[str] = None) -> Cita:
    """Cambia el estado con validación de transiciones (pendiente→confirmada→en_proceso→finalizada)."""
    TRANSICIONES = {
        "pendiente":  ["confirmada", "cancelada"],
        "confirmada": ["en_proceso", "cancelada"],
        "en_proceso": ["finalizada", "cancelada"],
        "finalizada": [],
        "cancelada":  [],
    }

    cita = Cita.query.get(cita_id)
    if not cita:
        raise CitaNoEncontradaError(f"Cita id={cita_id} no encontrada.")

    if nuevo_estado not in ESTADOS_CITA:
        raise ValueError(f"Estado '{nuevo_estado}' no es válido.")

    if nuevo_estado not in TRANSICIONES.get(cita.estado, []):
        raise ValueError(
            f"No se puede pasar de '{cita.estado}' a '{nuevo_estado}'."
        )

    cita.estado = nuevo_estado
    if notas_admin:
        cita.notas_admin = notas_admin

    db.session.commit()
    return cita


def obtener_horarios_disponibles(fecha: datetime.date, servicio_id: int) -> list[dict]:
    """Bloques horarios disponibles para un día (09:00–18:00, intervalos por duracion_min)."""
    servicio = Servicio.query.get(servicio_id)
    if not servicio:
        return []

    horario_inicio = datetime.combine(fecha, datetime.min.time()).replace(hour=9,  minute=0)
    horario_fin    = datetime.combine(fecha, datetime.min.time()).replace(hour=18, minute=0)

    disponibles = []
    bloque_actual = horario_inicio

    while bloque_actual + timedelta(minutes=servicio.duracion_min) <= horario_fin:
        if verificar_disponibilidad(bloque_actual, servicio_id):
            disponibles.append({
                "inicio": bloque_actual.strftime("%H:%M"),
                "fin":    (bloque_actual + timedelta(minutes=servicio.duracion_min)).strftime("%H:%M"),
                "datetime_iso": bloque_actual.isoformat(),
            })
        bloque_actual += timedelta(minutes=servicio.duracion_min)

    return disponibles
