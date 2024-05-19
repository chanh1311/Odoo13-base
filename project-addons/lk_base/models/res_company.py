# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    password_expiration = fields.Integer('Password Expiration Date', default=-1,
                                         help='How many days until passwords expire - use 0 to disable')
    password_length = fields.Integer('Minimum Characters', default=5, help='Minimum number of characters')
    password_lower = fields.Integer('Lowercase Characters', default=0, help='Minimum lowercase letters')
    password_upper = fields.Integer('Uppercase Characters', default=0, help='Minimum uppercase letters')
    password_numeric = fields.Integer('Numbers Characters', default=0, help='Minimum number of numeric digits')
    password_special = fields.Integer('Special Characters', default=0,
                                      help='Minimum number of unique special characters')
    password_estimate = fields.Integer('Password Strength', default=0,
                                       help='Required score for the strength estimation. Between 0 and 4')
    password_history = fields.Integer('Reuse Latest Old Password (Number)', default=-1,
                                      help='Disallow reuse of this many previous passwords - use negative '
                                           'number for infinite, or 0 to don\'t allow reuse old password')
    password_minimum = fields.Integer('Can Change Password Each ', default=-1,
                                      help='Amount of hours until a user may change password again - use negative '
                                           'number to disable, or 0 to don\'t allow change password')

    # simple policy
    enable_upper = fields.Boolean('Contain Uppercase', default=False, help='Password must contain uppercase letters')
    enable_numeric = fields.Boolean('Contain Numbers', default=False, help='Password must contain numeric digits')
    enable_special = fields.Boolean('Contain Special Characters', default=False,
                                    help='Password must contain special characters')
    pass_strength = fields.Selection([('0', 'None'), ('1', 'Low'), ('2', 'Fair'), ('3', 'Good'), ('4', 'Excellent')],
                                     'Password Strength', default='0', required=1)
    enable_reuse = fields.Boolean('Reuse Old Password', default=True, help='Allow reuse Old Password')
    enable_change_password = fields.Selection([('0', 'Anytime'), ('1', '1 Hour'), ('3', '3 Hours'), ('6', '6 Hours'),
                                               ('9', '9 Hours'), ('12', '12 Hours'), ('24', '24 Hours')],
                                              'Allow Change Password Every', default='0', required=1,
                                              help='Amount of hours until a user may change password again.')
    enable_expiration = fields.Selection([('0', 'No expire'), ('1', '1 month'), ('3', '3 months'), ('6', '6 months'),
                                          ('9', '9 months'), ('12', '12 months'), ('24', '24 months')],
                                         'Password Expiration', default='0', required=1,
                                         help='How many months until passwords expire')

    @api.constrains('password_estimate')
    def _check_password_estimate(self):
        if 0 > self.password_estimate > 4:
            raise ValidationError(_('Password Strength must be between 0 and 4.'))

    @api.model
    def simple_password_policy(self, vals, is_create=False):
        if is_create:
            vals.update({
                'enable_upper': False,
                'enable_numeric': False,
                'enable_special': False,
                'pass_strength': '0',
                'enable_reuse': True,
                'enable_change_password': '0',
                'enable_expiration': '0',
            })
        if 'enable_upper' in vals:
            vals['password_upper'] = 1 if vals.get('enable_upper') else 0
        if 'enable_numeric' in vals:
            vals['password_numeric'] = 1 if vals.get('enable_numeric') else 0
        if 'enable_special' in vals:
            vals['password_special'] = 1 if vals.get('enable_special') else 0
        if vals.get('pass_strength'):
            vals['password_estimate'] = int(vals.get('pass_strength'))
        if 'enable_reuse' in vals:
            vals['password_history'] = -1 if vals.get('enable_reuse') else 0
        if vals.get('enable_change_password'):
            enable_change_password = int(vals.get('enable_change_password'))
            vals['password_minimum'] = enable_change_password if enable_change_password else -1
        if vals.get('enable_expiration'):
            enable_expiration = int(vals.get('enable_expiration'))
            vals['password_expiration'] = enable_expiration * 30 if enable_expiration else -1
        return vals

    @api.model
    def create(self, vals):
        vals = self.simple_password_policy(vals, True)
        return super(ResCompany, self).create(vals)

    def write(self, vals):
        vals = self.simple_password_policy(vals)
        return super(ResCompany, self).write(vals)
