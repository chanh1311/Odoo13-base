# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ResGroups(models.Model):
    _inherit = 'res.groups'
    _rec_name = 'name'
    _order = 'id desc'

    @api.model
    def _default_function_access(self):
        available_function_lst = self.get_available_function_lst()
        return [(
            0, 0, {
                'name': line["menu_id"],
                'check_all': False,
                'perm_read': False,
                'perm_create': False,
                'perm_write': False,
                'perm_unlink': False,
            })
            for line in available_function_lst
        ]

    login_calendar_id = fields.Many2one('resource.calendar', 'System Access Schedule',
                                        company_dependent=True, help='''The user will be only allowed 
                                        to login in the calendar defined here. \nNOTE: The users will be allowed to
                                        login using a merge/union of all calendars to wich one belongs.''')
    function_access = fields.One2many('function.menu', 'group_id', 'Function', default=_default_function_access)

    multiple_sessions_block = fields.Boolean('Prevent Same Sessions', company_dependent=True,
                                             help='''Select this to prevent users of this group to start more
                                             than one session.''')
    interval_number = fields.Integer('Session Limit Duration', company_dependent=True,
                                     help='''This define the timeout for the users of this group.\nNOTE: The system
                                         will get the lowest timeout of all user groups.''')
    interval_type = fields.Selection([('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Working days'),
                                      ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
                                     'Time Type', company_dependent=True)
    is_customized = fields.Boolean('Customized Group', default=False)
    is_manager = fields.Selection([], 'Role')

    @api.model
    def create(self, vals):
        res = super(ResGroups, self).create(vals)
        self.set_ir_rule(res)
        return res

    def write(self, vals):
        res = super(ResGroups, self).write(vals)
        # if use other odoo group, we need reset role
        # if '' in vals:
        #     self.reset_role(self)
        # log out to prevent user access custom button
        # if '' in vals:
        #     self.sudo().kill_session(self.users.ids)
        if 'is_manager' in vals:
            self.set_ir_rule(self)
            # logout other session to force user login with new access control
            self.sudo().kill_session(self.users.ids)
        return res

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_('%s (copy)') % self.name)
        default['function_access'] = [(0, 0, {
                                        'name': access.name,
                                        'perm_read': access.perm_read,
                                        'perm_create': access.perm_create,
                                        'check_all': access.check_all,
                                        'perm_write': access.perm_write,
                                        'perm_unlink': access.perm_unlink,
                                    }) for access in self.function_access]
        default['users'] = False
        res = super(ResGroups, self).copy(default)
        # in case of copy, it will delete rule of old group and make error
        self.set_ir_rule(self)
        return res

    def unlink(self):
        for line in self:
            user = self.env['res.users'].search([('new_group_id', '=', line.id)], limit=1)
            if user:
                raise UserError(_('User %s is belongs to this group.') % user.name)
            rules = self.env['ir.rule'].sudo().search([('groups', 'in', [line.id])])
            rules.unlink()
        return super(ResGroups, self).unlink()

    # technical button for reset right of menu
    def action_set_visible_menu(self):
        for line in self.search([('is_customized', '=', True)]):
            for func in line.function_access:
                func.set_visible_menu(line, func, "write", func.perm_read)

    def action_reset_function(self):
        for line in self.search([('is_customized', '=', True)]):
            line.function_access = False
            line.function_access = self._default_function_access()

    def action_missing_access(self):
        function_access = self.env['function.menu']
        all_function = function_access.search_read([])
        available_function_lst = self.get_available_function_lst()
        for line in self.search([('is_customized', '=', True)]):
            function_group = list(filter(lambda x: x['group_id'][0] == line.id, all_function))
            new_access = []
            for func in available_function_lst:
                access = list(filter(lambda x: x['name'] == func['menu_id'], function_group))
                if access:
                    new_access.append({
                        'group_id': access[0]['group_id'][0],
                        'name': access[0]['name'],
                        'perm_read': access[0]['perm_read'],
                        'perm_create': access[0]['perm_create'],
                        'check_all': access[0]['check_all'],
                        'perm_write': access[0]['perm_write'],
                        'perm_unlink': access[0]['perm_unlink'],
                    })
                else:
                    new_access.append({
                        'group_id': line.id,
                        'name': func['menu_id'],
                        'perm_read': False,
                        'perm_create': False,
                        'check_all': False,
                        'perm_write': False,
                        'perm_unlink': False,
                    })
            line.function_access.unlink()
            for v in new_access:
                self.env['function.menu'].create(v)

    def action_reset_rule(self):
        for line in self.search([('is_customized', '=', True)]):
            line.set_ir_rule(line)

    @api.model
    def get_custom_button(self):
        """ Display custom button """
        user = self.env.user
        return {}

    @api.model
    def kill_session(self, user_ids):
        """ Logout other session to force user login with new access control
            :param user_ids: list of user ID in database
            :return:
        """
        ir_sessions = self.env['ir.sessions'].search([('logged_in', '=', True), ('user_id', 'in', user_ids)])
        ir_sessions.action_close_session()
        # delete token in app
        access_token = self.env['api.access_token'].sudo().search([('user_id', 'in', user_ids)])
        devices = self.env['res.users.device'].sudo().search([("token", "in", access_token.mapped('token'))])
        access_token.unlink()
        devices.unlink()

    @api.model
    def reset_role(self, group):
        """ Reset user role. Can use it or not. Example: if manager and employee access same view but only manager
        can use approve button, so we need a additional group to check.
            :param group: access control group
            :return:
        Example of usual:
            if group.is_customized:
                group_eep_manager = self.env.ref('lk_eep.group_eep_manager', False)
                group_eep_employee = self.env.ref('lk_eep.group_eep_employee', False)
                group_eep_approve = self.env.ref('lk_eep.group_eep_approve', False)
                group_lst = []
                if group_eep_manager:
                    if group.is_manager:
                        group_lst.append((4, group_eep_manager.id))
                    else:
                        group_lst.append((3, group_eep_manager.id))
                if group_lst:
                    group.users.write({'groups_id': group_lst})
        """
        pass

    @api.model
    def set_ir_rule(self, group):
        """ Restrict accessed data per group. Can use it or not. This is easier method to restrict data per group.
        Example: employee can only see current its data. Manager can see all employee.
            :param group: access control group
            :return:
        Example of usual:
            if group.is_customized:
                self.reset_role(group)
                rule_obj = self.env['ir.rule']
                ir_model_obj = self.env['ir.model']
                vals = []
                custom_fields = self.env['ir.model.fields'].search(
                    [('name', 'in', ['eep_company_id', 'eep_current_company_id']), ('model_id.transient', '!=', True)])
                model_lst = ir_model_obj.browse(custom_fields.mapped('model_id').ids)
                rules = rule_obj.search([('groups', 'in', [group.id]), ('model_id', 'in', model_lst.ids)])
                rules.unlink()
                # when use ir.rule in important model (res.groups, ir.action,...) need check carefully again
                if group.is_manager != 'super':
                    for model in model_lst:
                        field_lst = model.field_id.mapped('name')
                        if group.is_manager:
                            if model.model == 'eep.company':
                                domain_force = "[('id', 'in', user.partner_id.eep_company_ids.ids)]"
                            else:
                                domain_force = "[('eep_company_id', 'in', user.partner_id.eep_company_ids.ids)]"
                            vals.append({
                                'name': 'See all data in allowed company',
                                'model_id': model.id,
                                'domain_force': domain_force,
                                'groups': [(4, group.id)],
                            })
                        else:
                            if model.model == 'eep.company':
                                domain_force = "[('id', '=', user.partner_id.eep_current_company_id.id)]"
                            else:
                                domain_force = "[('eep_company_id', '=', user.partner_id.eep_current_company_id.id)]"
                            if domain_force:
                                vals.append({
                                    'name': 'See only employee data',
                                    'model_id': model.id,
                                    'domain_force': domain_force,
                                    'groups': [(4, group.id)],
                                })
                    if vals:
                        rule_obj.create(vals)
        """
        print('Test')
        pass
