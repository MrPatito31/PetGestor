"""
seed.py — Script de inicialización de datos para desarrollo/prueba.

Uso:
  # Dev local (SQLite — configurar DATABASE_URL antes):
  DATABASE_URL=sqlite:///petgestor_dev.db python seed.py

  # Con MySQL (Docker corriendo, lee .env):
  python seed.py
"""
from app import create_app, db
from app.models.usuario import Usuario
from app.models.finanzas import CategoriaFinanciera
from app.services.chat_service import poblar_faqs_iniciales

app = create_app()

with app.app_context():
    db.create_all()
    print("✔ Tablas creadas/verificadas")

    # ── Crear usuario admin ────────────────────────────────────────────────────
    if not Usuario.query.filter_by(email="admin@petgestor.cl").first():
        admin = Usuario(
            nombre="Administrador",
            email="admin@petgestor.cl",
            rol="admin",
            activo=True,
            password="admin123",
        )
        db.session.add(admin)
        print("✔ Usuario admin creado: admin@petgestor.cl / admin123")

    # ── Categorías financieras ─────────────────────────────────────────────────
    categorias_data = [
        ("Servicio peluquería", "ingreso"),
        ("Venta de producto",   "ingreso"),
        ("Otro ingreso",        "ingreso"),
        ("Compra insumos",      "egreso"),
        ("Arriendo",            "egreso"),
        ("Servicios básicos",   "egreso"),
        ("Salarios",            "egreso"),
        ("Otros gastos",        "egreso"),
    ]
    nuevas = 0
    for nombre, tipo in categorias_data:
        if not CategoriaFinanciera.query.filter_by(nombre=nombre).first():
            db.session.add(CategoriaFinanciera(nombre=nombre, tipo=tipo))
            nuevas += 1

    print(f"✔ Categorías financieras: {len(categorias_data)} total, {nuevas} nuevas")

    # ── FAQs iniciales para el chatbot ─────────────────────────────────────────
    poblar_faqs_iniciales()
    print("✔ FAQs iniciales cargadas")

    db.session.commit()

    print()
    print("=" * 50)
    print("PETGESTOR — Datos iniciales cargados")
    print("   Admin: admin@petgestor.cl / admin123")
    print("   URL:   http://localhost:5000")
    print("=" * 50)
