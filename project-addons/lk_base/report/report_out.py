# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ReportOut(models.TransientModel):
    _name = 'report.out'

    report_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Excel Report', readonly=True)
