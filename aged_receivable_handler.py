# -*- coding: utf-8 -*-
from odoo import models, _


class AgedReceivableCustomHandler(models.AbstractModel):
    _inherit = "account.aged.receivable.report.handler"

    def _caret_options_initializer(self):
        caret_options = super()._caret_options_initializer()
        pdf_option = {
            "name": _("Descargar PDF Estado de Cuenta"),
            "action": "caret_option_descargar_pdf_estado_cuenta",
        }
        email_option = {
            "name": _("Enviar Estado de Cuenta"),
            "action": "caret_option_enviar_pdf_estado_cuenta",
        }
        caret_options.setdefault("res.partner", []).append(pdf_option)
        caret_options["res.partner"].append(email_option)
        return caret_options

    def _extract_partner_from_params(self, params):
        partner_id = params.get("res_id") or params.get("partner_id")
        if not partner_id and params.get("line_id"):
            for part in str(params["line_id"]).split("-"):
                if part.isdigit():
                    partner_id = int(part)
                    break
        if partner_id:
            return self.env["res.partner"].browse(int(partner_id))
        return self.env["res.partner"]

    def caret_option_descargar_pdf_estado_cuenta(self, options, params):
        partner = self._extract_partner_from_params(params)
        if not partner:
            return False
        return partner.action_print_pdf()

    def caret_option_enviar_pdf_estado_cuenta(self, options, params):
        partner = self._extract_partner_from_params(params)
        if not partner:
            return False
        return partner.action_share_pdf()
