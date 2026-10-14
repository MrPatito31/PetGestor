"""Blueprint de autenticación de administradores."""
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.usuario import Usuario

auth_bp = Blueprint("auth", __name__, template_folder="../templates")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_citas.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        usuario = Usuario.query.filter_by(email=email, activo=True).first()
        if usuario and usuario.verificar_password(password):
            usuario.ultimo_acceso = datetime.now(timezone.utc)
            db.session.commit()
            login_user(usuario, remember=False)
            flash(f"Bienvenido, {usuario.nombre}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin_citas.index"))
        else:
            flash("Correo o contraseña incorrectos.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))
