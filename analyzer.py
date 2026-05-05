"""Analyzer de cobros — combina Odoo (facturas vencidas) + Postgres (seguimientos)."""
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
import psycopg2
import psycopg2.extras

from odoo_client import odoo
from config import (
    PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD, COMPANIES
)


def pg_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB,
        user=PG_USER, password=PG_PASSWORD, sslmode="require",
    )


def days_overdue(due_str, today_d):
    if not due_str:
        return 0
    try:
        d = datetime.strptime(str(due_str)[:10], "%Y-%m-%d").date()
        return max(0, (today_d - d).days)
    except Exception:
        return 0


def aging_bucket(days):
    if days <= 0: return "Al día"
    if days <= 30: return "1-30"
    if days <= 60: return "31-60"
    if days <= 90: return "61-90"
    if days <= 120: return "91-120"
    return "120+"


# ======================================================================
# DATOS DE ODOO
# ======================================================================

def get_overdue_invoices(today_d):
    """Trae todas las facturas out_invoice posted con saldo, vencidas."""
    domain = [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ["not_paid", "partial"]),
        ("invoice_date_due", "<", today_d.isoformat()),
    ]
    invoices = odoo.search_read(
        "account.move", domain,
        fields=["id", "name", "partner_id", "invoice_date", "invoice_date_due",
                "amount_total", "amount_residual", "company_id", "payment_state",
                "user_id", "ref"],
        limit=10000, order="invoice_date_due asc",
    )
    for inv in invoices:
        inv["days_overdue"] = days_overdue(inv.get("invoice_date_due"), today_d)
        inv["bucket"] = aging_bucket(inv["days_overdue"])
        inv["score"] = round(inv.get("amount_residual", 0) * inv["days_overdue"], 2)
    return invoices


def get_recent_payments(days_back=30):
    """Pagos inbound recientes — para 'cuánto se está cobrando'.
    Incluye state='paid' (confirmados) y state='in_process' (recibidos pendientes de aplicar).
    """
    since = (date.today() - timedelta(days=days_back)).isoformat()
    pagos = odoo.search_read(
        "account.payment",
        [
            ("state", "in", ["paid", "in_process"]),
            ("payment_type", "=", "inbound"),
            ("partner_type", "=", "customer"),
            ("date", ">=", since),
        ],
        fields=["id", "name", "amount", "date", "partner_id", "company_id", "state"],
        limit=10000, order="date desc",
    )
    return pagos


# ======================================================================
# DATOS DE POSTGRES (BD del bot de cobros)
# ======================================================================

def get_seguimientos_db(days_back=90):
    """Trae seguimientos de invoice_send_checklist desde la BD del bot."""
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    conn = pg_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT odoo_invoice_id, channel, checked, checked_by,
                   invoice_name, partner_name, created_at, updated_at
            FROM invoice_send_checklist
            WHERE created_at >= %s AND checked = true
            ORDER BY created_at DESC
        """, (since,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    finally:
        conn.close()


# ======================================================================
# AGREGADOS
# ======================================================================

def kpis_overall(invoices, seguimientos, payments):
    total_residual = sum(i.get("amount_residual", 0) for i in invoices)
    partners = set(i["partner_id"][0] for i in invoices if i.get("partner_id"))
    invoices_con_seg = set(s["odoo_invoice_id"] for s in seguimientos)
    invoices_con_seg_overdue = invoices_con_seg & set(i["id"] for i in invoices)
    cobrado_30d = sum(p.get("amount", 0) for p in payments)
    return {
        "total_overdue": round(total_residual, 2),
        "n_invoices": len(invoices),
        "n_clients": len(partners),
        "n_seguimientos_total": len(seguimientos),
        "n_invoices_con_seguimiento": len(invoices_con_seg_overdue),
        "n_invoices_sin_seguimiento": len(invoices) - len(invoices_con_seg_overdue),
        "pct_cobertura_seguimiento": round(100 * len(invoices_con_seg_overdue) / len(invoices), 1) if invoices else 0,
        "cobrado_30d": round(cobrado_30d, 2),
        "n_pagos_30d": len(payments),
    }


def aging_buckets(invoices):
    out = defaultdict(lambda: {"count": 0, "amount": 0})
    for i in invoices:
        b = i["bucket"]
        out[b]["count"] += 1
        out[b]["amount"] += i.get("amount_residual", 0)
    order = ["1-30", "31-60", "61-90", "91-120", "120+"]
    return [
        {"bucket": b, "count": out[b]["count"], "amount": round(out[b]["amount"], 2)}
        for b in order
    ]


def by_company(invoices, seguimientos):
    seg_by_inv = defaultdict(int)
    for s in seguimientos:
        seg_by_inv[s["odoo_invoice_id"]] += 1
    out = defaultdict(lambda: {"count": 0, "amount": 0, "name": "", "con_seg": 0, "sin_seg": 0, "seg_total": 0})
    for i in invoices:
        cid = i["company_id"][0] if i.get("company_id") else 0
        cname = COMPANIES.get(cid, {}).get("short", str(cid))
        out[cid]["count"] += 1
        out[cid]["amount"] += i.get("amount_residual", 0)
        out[cid]["name"] = cname
        n_seg = seg_by_inv.get(i["id"], 0)
        if n_seg > 0:
            out[cid]["con_seg"] += 1
            out[cid]["seg_total"] += n_seg
        else:
            out[cid]["sin_seg"] += 1
    return sorted(
        [{"company_id": cid, **v, "amount": round(v["amount"], 2)} for cid, v in out.items()],
        key=lambda x: -x["amount"],
    )


def top_deudores(invoices, seguimientos, n=20):
    seg_by_partner = defaultdict(lambda: defaultdict(int))
    for s in seguimientos:
        # buscar partner del seg
        seg_by_partner[s.get("partner_name", "")][s["channel"]] += 1
    out = defaultdict(lambda: {"name": "", "count": 0, "amount": 0, "max_days": 0,
                               "score": 0, "company": "", "wa": 0, "email": 0})
    for i in invoices:
        if not i.get("partner_id"): continue
        pid = i["partner_id"][0]
        out[pid]["name"] = i["partner_id"][1]
        out[pid]["count"] += 1
        out[pid]["amount"] += i.get("amount_residual", 0)
        out[pid]["max_days"] = max(out[pid]["max_days"], i["days_overdue"])
        out[pid]["score"] += i.get("score", 0)
        if i.get("company_id"):
            out[pid]["company"] = COMPANIES.get(i["company_id"][0], {}).get("short", "")
    for pid, v in out.items():
        seg = seg_by_partner.get(v["name"], {})
        v["wa"] = seg.get("whatsapp", 0)
        v["email"] = seg.get("email", 0)
    deudores = [
        {"partner_id": pid, **v, "amount": round(v["amount"], 2), "score": round(v["score"], 2)}
        for pid, v in out.items()
    ]
    return sorted(deudores, key=lambda x: -x["amount"])[:n]


def por_canal(seguimientos):
    out = defaultdict(int)
    for s in seguimientos:
        out[s["channel"]] += 1
    return [{"channel": k, "count": v} for k, v in out.items()]


def timeline_seguimientos(seguimientos, days_back=30):
    """Conteo por día de seguimientos."""
    today_d = date.today()
    counts = defaultdict(lambda: {"whatsapp": 0, "email": 0, "informe": 0, "total": 0})
    for s in seguimientos:
        d = s.get("created_at")
        if not d: continue
        if isinstance(d, datetime):
            day = d.date()
        else:
            day = datetime.fromisoformat(str(d)[:10]).date()
        if (today_d - day).days > days_back: continue
        ch = s["channel"]
        if ch in counts[day]:
            counts[day][ch] += 1
        counts[day]["total"] += 1
    rows = []
    for i in range(days_back, -1, -1):
        d = today_d - timedelta(days=i)
        c = counts.get(d, {"whatsapp": 0, "email": 0, "informe": 0, "total": 0})
        rows.append({"date": d.isoformat(), **c})
    return rows


def clientes_sin_seguimiento(invoices, seguimientos):
    """Facturas vencidas SIN ningún seguimiento registrado, ordenadas por monto."""
    invoices_con_seg = set(s["odoo_invoice_id"] for s in seguimientos)
    sin = defaultdict(lambda: {"name": "", "count": 0, "amount": 0, "max_days": 0, "company": ""})
    for i in invoices:
        if i["id"] in invoices_con_seg: continue
        if not i.get("partner_id"): continue
        pid = i["partner_id"][0]
        sin[pid]["name"] = i["partner_id"][1]
        sin[pid]["count"] += 1
        sin[pid]["amount"] += i.get("amount_residual", 0)
        sin[pid]["max_days"] = max(sin[pid]["max_days"], i["days_overdue"])
        if i.get("company_id"):
            sin[pid]["company"] = COMPANIES.get(i["company_id"][0], {}).get("short", "")
    return sorted(
        [{"partner_id": pid, **v, "amount": round(v["amount"], 2)} for pid, v in sin.items()],
        key=lambda x: -x["amount"],
    )


def clientes_mas_contactados(seguimientos, n=20):
    """Top clientes con más recordatorios enviados."""
    out = defaultdict(lambda: {"total": 0, "wa": 0, "email": 0, "ultimo": None})
    for s in seguimientos:
        name = s.get("partner_name", "")
        if not name: continue
        out[name]["total"] += 1
        if s["channel"] == "whatsapp": out[name]["wa"] += 1
        elif s["channel"] == "email": out[name]["email"] += 1
        d = s.get("created_at")
        if d and (out[name]["ultimo"] is None or d > out[name]["ultimo"]):
            out[name]["ultimo"] = d
    rows = [{"name": k, **v, "ultimo": v["ultimo"].isoformat() if v["ultimo"] else None} for k, v in out.items()]
    return sorted(rows, key=lambda x: -x["total"])[:n]


def cobros_por_empresa(payments):
    out = defaultdict(lambda: {"count": 0, "amount": 0, "name": ""})
    for p in payments:
        cid = p["company_id"][0] if p.get("company_id") else 0
        cname = COMPANIES.get(cid, {}).get("short", str(cid))
        out[cid]["count"] += 1
        out[cid]["amount"] += p.get("amount", 0)
        out[cid]["name"] = cname
    return sorted(
        [{"company_id": cid, **v, "amount": round(v["amount"], 2)} for cid, v in out.items()],
        key=lambda x: -x["amount"],
    )


# ======================================================================
# ANALYZE — entrada principal
# ======================================================================

def analyze():
    today_d = date.today()
    invoices = get_overdue_invoices(today_d)
    seguimientos = get_seguimientos_db(days_back=90)
    payments = get_recent_payments(days_back=30)

    return {
        "generated_at": datetime.now().isoformat(),
        "today": today_d.isoformat(),
        "kpis": kpis_overall(invoices, seguimientos, payments),
        "aging": aging_buckets(invoices),
        "by_company": by_company(invoices, seguimientos),
        "top_deudores": top_deudores(invoices, seguimientos, n=20),
        "por_canal": por_canal(seguimientos),
        "timeline": timeline_seguimientos(seguimientos, days_back=30),
        "sin_seguimiento": clientes_sin_seguimiento(invoices, seguimientos)[:50],
        "mas_contactados": clientes_mas_contactados(seguimientos, n=20),
        "cobros_por_empresa": cobros_por_empresa(payments),
        "totales": {
            "invoices": len(invoices),
            "seguimientos_90d": len(seguimientos),
            "pagos_30d": len(payments),
        },
    }
