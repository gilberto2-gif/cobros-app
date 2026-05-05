# Indicador de Cobros — Grupo Rapid

Dashboard ejecutivo de cuentas por cobrar con seguimiento de cobranza en tiempo real.

**Stack:** Flask + Bootstrap 5 + Chart.js
**Datos:**
- Odoo 18 Enterprise (facturas vencidas, pagos)
- Postgres del bot de cobros (seguimientos enviados)

## Pestañas

1. **Dashboard** — KPIs, aging, top deudores, cobros 30d
2. **Seguimientos** — actividad de mensajes, urgentes sin contactar
3. **Clientes** — listado completo con filtros

## Deploy local
```bash
pip install -r requirements.txt
cp .env.example .env  # editar con credenciales
python app.py  # http://localhost:5004
```

## Variables de entorno

| Variable | Descripción |
|---|---|
| ODOO_USER | Usuario Odoo |
| ODOO_PASSWORD | Password Odoo |
| PG_PASSWORD | Password Postgres bot cobros |
| SECRET_KEY | Flask secret |
| CACHE_TTL | Segundos cache (default 30) |
