# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FunctionMenu(models.Model):
    _name = 'function.menu'

    @api.model
    def _selection_name(self):
        available_function_lst = self.get_available_function_lst()
        return [(rec['menu_id'], rec['name']) for rec in available_function_lst]

    group_id = fields.Many2one('res.groups', ondelete='cascade')

    name = fields.Selection('_selection_name', 'Function', required=True)
    perm_read = fields.Boolean('Read')
    perm_create = fields.Boolean('Create')
    perm_write = fields.Boolean('Update')
    perm_unlink = fields.Boolean('Delete')
    is_disable = fields.Boolean('Is Disable?', compute='_compute_is_disable')
    check_all = fields.Boolean('Check All')

    # @api.constrains('name')
    # def check_name(self):
    #     for line in self:
    #         print(self.search_count([('name', '=', line.name)]))
    #         if self.search_count([('name', '=', line.name)]) > 1:
    #             raise UserError('Duplicate function menu name')

    @api.depends('name')
    def _compute_is_disable(self):
        for line in self:
            line.is_disable = False
            available_function_lst = self.get_available_function_lst()
            func = next((item for item in available_function_lst if item["menu_id"] == line.name), False)
            if func and func['type'] == 'view':
                line.is_disable = True

    @api.onchange('check_all')
    def _onchange_check_all(self):
        self.perm_read = self.check_all
        self.perm_create = self.check_all
        self.perm_write = self.check_all
        self.perm_unlink = self.check_all

    @api.onchange('perm_read')
    def _onchange_perm_read(self):
        if self.is_disable:
            if self.perm_read:
                self.perm_create = True
                self.perm_write = True
                self.perm_unlink = True
            else:
                self.perm_create = False
                self.perm_write = False
                self.perm_unlink = False

    @api.model
    def create(self, vals):
        res = super(FunctionMenu, self).create(vals)
        self.set_visible_menu(res.group_id, res, "create", res.perm_read)
        return res

    def write(self, vals):
        res = super(FunctionMenu, self).write(vals)
        for line in self:
            self.set_visible_menu(line.group_id, line, "write", line.perm_read)
        return res

    # action methods

    # business methods
    @api.model
    def set_visible_menu(self, group, line, method, is_read=None):
        """ Check if function menu is visible.
            :param group: access control.
            :param line: function.
            :param method: action of user (create, update, delete).
            :param is_read: read permission of group.
            :return:
        """
        visible_group = 'lk_base.make_invisible'
        menu = self.env.ref(line.name, False)
        if menu:
            if method == "create" or method == "write":
                if is_read:
                    menu.write({'groups_id': [(4, group.id), (3, self.env.ref(visible_group).id)]})
                else:
                    menu.write({'groups_id': [(3, group.id), (4, self.env.ref(visible_group).id)]})
            elif method == "unlink":
                menu.write({'groups_id': [(3, group.id), (4, self.env.ref(visible_group).id)]})
