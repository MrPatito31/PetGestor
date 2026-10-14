"""
run.py — Punto de entrada único de la aplicación Flask.

Uso:
  # Desarrollo local (SQLite, sin Docker):
  DATABASE_URL=sqlite:///petgestor_dev.db python run.py

  # Producción con Docker+MySQL (lee .env automáticamente):
  python run.py
"""
from app import create_app, db
from app.models.usuario import Usuario
from app.models.cliente import Cliente, Mascota
from app.models.cita import Cita, Servicio
from app.models.inventario import Producto, MovimientoInventario
from app.models.finanzas import Ingreso, Egreso, CategoriaFinanciera
from app.models.chat import Conversacion, Mensaje, FaqRespuesta

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Permite usar modelos directamente en `flask shell` para pruebas."""
    return {
        "db": db,
        "Usuario": Usuario,
        "Cliente": Cliente,
        "Mascota": Mascota,
        "Cita": Cita,
        "Servicio": Servicio,
        "Producto": Producto,
        "MovimientoInventario": MovimientoInventario,
        "Ingreso": Ingreso,
        "Egreso": Egreso,
        "CategoriaFinanciera": CategoriaFinanciera,
        "Conversacion": Conversacion,
        "Mensaje": Mensaje,
        "FaqRespuesta": FaqRespuesta,
    }


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✔ Tablas de base de datos verificadas/creadas.")

        # Garantizar usuario admin en desarrollo
        if app.config.get("DEBUG"):
            if not Usuario.query.filter_by(email="admin@petgestor.cl").first():
                admin = Usuario(
                    nombre="Administrador",
                    email="admin@petgestor.cl",
                    rol="admin",
                    activo=True,
                    password="admin123",
                )
                db.session.add(admin)
                db.session.commit()
                print("✔ Usuario admin creado: admin@petgestor.cl / admin123")

    is_sqlite = "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", "")
    db_label = "SQLite" if is_sqlite else "MySQL"

    print("━" * 50)
    print(f"PetGestor — Servidor ({db_label})")
    print(f"   URL:   http://localhost:5000")
    if app.config.get("DEBUG"):
        print("   Admin: admin@petgestor.cl / admin123")
    print("━" * 50)

    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
