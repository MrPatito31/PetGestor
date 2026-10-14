"""App Factory de Flask."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

from config import ActiveConfig

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_class=ActiveConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder a esta página."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.usuario import Usuario
        return Usuario.query.get(int(user_id))

    # ── Registrar todos los blueprints (imports centralizados) ────────────────
    from app.routes import (
        auth_bp,
        cliente_bp,
        admin_citas_bp,
        admin_inventario_bp,
        admin_finanzas_bp,
        admin_chat_bp,
    )

    app.register_blueprint(auth_bp,             url_prefix="/auth")
    app.register_blueprint(cliente_bp,          url_prefix="/")
    app.register_blueprint(admin_citas_bp,      url_prefix="/admin/citas")
    app.register_blueprint(admin_inventario_bp, url_prefix="/admin/inventario")
    app.register_blueprint(admin_finanzas_bp,   url_prefix="/admin/finanzas")
    app.register_blueprint(admin_chat_bp,       url_prefix="/admin/chat")

    return app
