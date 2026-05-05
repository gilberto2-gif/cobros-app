"""Login contra Odoo — valida user/password directo en pestbuster.odoo.com."""
import requests
from functools import wraps
from flask import session, request, redirect, url_for, flash
from config import ODOO_URL, ODOO_DB


def authenticate_odoo(username, password):
    """Intenta autenticar contra Odoo. Devuelve dict con uid+name si OK, None si falla."""
    if not username or not password:
        return None
    try:
        r = requests.post(
            f"{ODOO_URL}/web/session/authenticate",
            json={
                "jsonrpc": "2.0", "method": "call", "params": {
                    "db": ODOO_DB, "login": username, "password": password,
                },
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            return None
        result = data.get("result") or {}
        uid = result.get("uid")
        if not uid:
            return None
        return {
            "uid": uid,
            "name": result.get("name") or result.get("username") or username,
            "username": username,
            "is_admin": bool(result.get("is_admin")),
        }
    except Exception:
        return None


def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper
