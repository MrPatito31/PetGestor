# app/routes/__init__.py
"""Blueprints de la aplicación — importar aquí para registro centralizado."""

from app.routes.auth_bp import auth_bp
from app.routes.cliente_bp import cliente_bp
from app.routes.admin_citas_bp import admin_citas_bp
from app.routes.admin_inventario_bp import admin_inventario_bp
from app.routes.admin_finanzas_bp import admin_finanzas_bp
from app.routes.admin_chat_bp import admin_chat_bp

__all__ = [
    "auth_bp",
    "cliente_bp",
    "admin_citas_bp",
    "admin_inventario_bp",
    "admin_finanzas_bp",
    "admin_chat_bp",
]
