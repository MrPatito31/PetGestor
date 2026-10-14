"""
config.py — Configuraciones de la aplicación Flask.
Usa variables de entorno definidas en .env para no exponer credenciales.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # Carga el archivo .env del directorio raíz


class Config:
    """Configuración base compartida por todos los entornos."""

    # ── Seguridad ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key_insegura")

    # ── Base de datos ─────────────────────────────────────────────────────────
    # DATABASE_URL tiene precedencia (permite SQLite en dev local).
    # Si no está definida, construye la URI de MySQL con las variables individuales.
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        _MYSQL_HOST     = os.environ.get("MYSQL_HOST", "db")
        _MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", 3306))
        _MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "petgestor_db")
        _MYSQL_USER     = os.environ.get("MYSQL_USER", "petgestor_user")
        _MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "petgestor_pass")
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{_MYSQL_USER}:{_MYSQL_PASSWORD}"
            f"@{_MYSQL_HOST}:{_MYSQL_PORT}/{_MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,   # Evita que MySQL cierre conexiones inactivas
        "pool_pre_ping": True, # Verifica que la conexión esté viva antes de usarla
        "pool_timeout": 30,
        "max_overflow": 10,
    }

    # ── UltraMsg / WhatsApp ──────────────────────────────────────────
    # Obtener en: https://app.ultramsg.com/  (escanear QR con tu WhatsApp)
    ULTRAMSG_INSTANCE  = os.environ.get("ULTRAMSG_INSTANCE", "")
    ULTRAMSG_TOKEN     = os.environ.get("ULTRAMSG_TOKEN", "")

    # ── Datos del negocio 
    NEGOCIO_NOMBRE    = os.environ.get("NEGOCIO_NOMBRE", "PetGestor Peluquería Canina")
    NEGOCIO_TELEFONO  = os.environ.get("NEGOCIO_TELEFONO", "+56912345678")
    NEGOCIO_DIRECCION = os.environ.get("NEGOCIO_DIRECCION", "Melipilla, Región Metropolitana")

    # ── Reglas de negocio de citas 
    # Duración mínima de cada servicio en minutos (bloquea ese lapso en la agenda)
    DURACION_SERVICIO_DEFAULT = 60  # 1 hora por defecto

    # Stock mínimo antes de generar alerta de reposición
    STOCK_CRITICO = 3


class DevelopmentConfig(Config):
    """Entorno de desarrollo: debug activo."""
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    """Entorno de producción: sin debug, configuración más estricta."""
    DEBUG = False
    FLASK_ENV = "production"
    # En producción usa una SECRET_KEY larga y aleatoria desde el entorno


# Mapeo de nombres de entorno a clases de configuración
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
}

# Clase activa según FLASK_ENV
ActiveConfig = config_map.get(os.environ.get("FLASK_ENV", "development"), DevelopmentConfig)
