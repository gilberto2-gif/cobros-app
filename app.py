"""Indicador de Cobros — Flask app puerto 5004."""
import threading
import time
from datetime import date

from flask import Flask, render_template, jsonify, request

from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, SECRET_KEY, CACHE_TTL
from analyzer import analyze

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

_cache = {"data": None, "ts": 0}
_lock = threading.Lock()


def get_data(force=False):
    now = time.time()
    with _lock:
        if force or _cache["data"] is None or (now - _cache["ts"]) > CACHE_TTL:
            _cache["data"] = analyze()
            _cache["ts"] = now
        return _cache["data"]


@app.route("/")
def index():
    return render_template("index.html", data=get_data())


@app.route("/seguimientos")
def seguimientos():
    return render_template("seguimientos.html", data=get_data())


@app.route("/clientes")
def clientes():
    return render_template("clientes.html", data=get_data())


@app.route("/api/data")
def api_data():
    force = request.args.get("force") == "1"
    return jsonify(get_data(force=force))


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    return jsonify({"status": "ok", "data": get_data(force=True)})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print(f"\n  Indicador de Cobros — http://localhost:{FLASK_PORT}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
