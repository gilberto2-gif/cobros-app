"""Indicador de Cobros — Flask app puerto 5004 con login Odoo."""
import threading
import time
from datetime import timedelta

from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash

from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, SECRET_KEY, CACHE_TTL
from analyzer import analyze
from auth import authenticate_odoo, require_login

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=12)

_cache = {"data": None, "ts": 0}
_lock = threading.Lock()


def get_data(force=False):
    now = time.time()
    with _lock:
        if force or _cache["data"] is None or (now - _cache["ts"]) > CACHE_TTL:
            _cache["data"] = analyze()
            _cache["ts"] = now
        return _cache["data"]


# ============ AUTH ============
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        user = authenticate_odoo(u, p)
        if user:
            session.permanent = True
            session["user"] = user
            return redirect(request.args.get("next") or url_for("index"))
        flash("Credenciales incorrectas", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ============ DASHBOARD ============
@app.route("/")
@require_login
def index():
    return render_template("index.html", data=get_data(), user=session.get("user"))


@app.route("/seguimientos")
@require_login
def seguimientos():
    return render_template("seguimientos.html", data=get_data(), user=session.get("user"))


@app.route("/clientes")
@require_login
def clientes():
    return render_template("clientes.html", data=get_data(), user=session.get("user"))


@app.route("/api/data")
@require_login
def api_data():
    force = request.args.get("force") == "1"
    return jsonify(get_data(force=force))


@app.route("/api/refresh", methods=["POST"])
@require_login
def api_refresh():
    return jsonify({"status": "ok", "data": get_data(force=True)})


# Health para Render (sin auth)
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print(f"\n  Indicador de Cobros — http://localhost:{FLASK_PORT}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
