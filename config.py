"""Config Indicador de Cobros."""
import os
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

# Odoo
ODOO_URL = os.environ.get("ODOO_URL", "https://pestbuster.odoo.com")
ODOO_DB = os.environ.get("ODOO_DB", "psdc-inc-pestbuster-prod-20747552")
ODOO_USER = os.environ["ODOO_USER"]
ODOO_PASSWORD = os.environ["ODOO_PASSWORD"]

# Postgres (Render — bot de cobros gruporapid-2.web.app)
PG_HOST = os.environ.get("PG_HOST", "dpg-d7bcup1r0fns73b2hfj0-a.oregon-postgres.render.com")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DB = os.environ.get("PG_DB", "gruporapid")
PG_USER = os.environ.get("PG_USER", "gruporapid")
PG_PASSWORD = os.environ["PG_PASSWORD"]

# Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("COBROS_PORT", 5004))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "cobros-indicador-2026")

# Empresas del grupo (IDs reales de res.company en Odoo)
COMPANIES = {
    1:  {"name": "DISTRIBUIDORA GURU, S.A.",            "short": "GURU"},
    2:  {"name": "FUMIPEST, Inc.",                      "short": "FUMIPEST"},
    3:  {"name": "KITCHEN TOTAL SOLUTIONS (KTS) CORP.", "short": "KTS"},
    5:  {"name": "GSU HOLDINGS, SA",                    "short": "GSU"},
    6:  {"name": "MUNDO DE PARTES AMERICANAS S.A.",     "short": "MUPASA"},
    7:  {"name": "RAPID FRIO, S.A.",                    "short": "RAPID FRIO"},
    8:  {"name": "RAPID POOLS, S.A.",                   "short": "RAPID POOLS"},
    9:  {"name": "DINO FUMIGACIONES, S.A. (XTERMINA)",  "short": "DINO"},
    10: {"name": "ALFA CONTRACTOR, S.A.",               "short": "ALFA"},
}

# Cache TTL (segundos)
CACHE_TTL = int(os.environ.get("CACHE_TTL", "30"))
