# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SystemLog(models.Model):
    _name = 'system.log'
    _rec_name = 'function'
    _order = 'id desc'

    @api.model
    def _selection_function(self):
        available_function_lst = self.get_available_function_lst()
        return [(rec['menu_id'], rec['name']) for rec in available_function_lst]

    user_id = fields.Many2one('res.users', 'User', required=1)
    company_id = fields.Many2one('res.company', 'Company', required=1, default=lambda self: self.env.company)

    type = fields.Selection([('create', 'Create'), ('write', 'Update'), ('unlink', 'Delete')], 'Type',
                            required=1)
    function = fields.Selection('_selection_function', 'Function', required=1)
    description = fields.Text('Description', required=1)
    create_date = fields.Datetime('Date')
