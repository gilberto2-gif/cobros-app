# -*- coding: utf-8 -*-
"""Crear servicio cobros-indicador en Render via API."""
import sys, io, json, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY = 'rnd_XubHPLikQUKZ3Nk74VEHKC8Q2tLv'
BASE = 'https://api.render.com/v1'
H = {'Authorization': f'Bearer {API_KEY}', 'Accept': 'application/json',
     'Content-Type': 'application/json'}

# Owner: gilberto2@gruporapid.com workspace
OWNER_ID = 'tea-d6f242haae7s73c14f10'

payload = {
    "type": "web_service",
    "name": "cobros-indicador",
    "ownerId": OWNER_ID,
    "repo": "https://github.com/gilberto2-gif/cobros-app",
    "branch": "main",
    "autoDeploy": "yes",
    "serviceDetails": {
        "env": "python",
        "region": "oregon",
        "plan": "free",
        "envSpecificDetails": {
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "gunicorn app:app --workers 2 --threads 2 --timeout 90 --bind 0.0.0.0:$PORT",
        },
        "healthCheckPath": "/health",
        "envVars": [
            {"key": "ODOO_URL", "value": "https://pestbuster.odoo.com"},
            {"key": "ODOO_DB", "value": "psdc-inc-pestbuster-prod-20747552"},
            {"key": "ODOO_USER", "value": "It@gruporapid.com"},
            {"key": "ODOO_PASSWORD", "value": "Antonellys21"},
            {"key": "PG_HOST", "value": "dpg-d7bcup1r0fns73b2hfj0-a.oregon-postgres.render.com"},
            {"key": "PG_PORT", "value": "5432"},
            {"key": "PG_DB", "value": "gruporapid"},
            {"key": "PG_USER", "value": "gruporapid"},
            {"key": "PG_PASSWORD", "value": "6BKiJLYlNrBT1OQtgsACmLJ1jKn1td7b"},
            {"key": "SECRET_KEY", "value": "cobros-indicador-2026-render-prod"},
            {"key": "CACHE_TTL", "value": "60"},
            {"key": "PYTHON_VERSION", "value": "3.12.7"},
        ],
    },
}

r = requests.post(f'{BASE}/services', headers=H, data=json.dumps(payload), timeout=30)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2)[:2000])
