# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons.base.models.ir_cron import _intervalTypes
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
import logging
import re
_logger = logging.getLogger(__name__)
try:
    import zxcvbn
    zxcvbn.feedback._ = _
except ImportError:
    _logger.debug('Could not import zxcvbn. Please make sure this library is available in your environment.')


def delta_now(**kwargs):
    dt = datetime.now() + timedelta(**kwargs)
    return fields.Datetime.to_string(dt)


class ResUsers(models.Model):
    _inherit = 'res.users'

    new_group_id = fields.Many2one('res.groups', 'Access Control', domain="[('is_customized', '=', True)]")
    login_calendar_id = fields.Many2one('resource.calendar', 'System Access Schedule',
                                        company_dependent=True, help='''The user will be only allowed
                                        to login in the calendar defined here. \nNOTE: The users will be allowed to
                                        login using a merge/union of all calendars to wich one belongs.''')
    session_ids = fields.One2many('ir.sessions', 'user_id', 'User Session')
    ip_ids = fields.One2many('res.users.ip', 'user_id', 'Allowed IP address')
    password_history_ids = fields.One2many('res.users.pass.history', 'user_id', 'Password History', readonly=True)

    password_write_date = fields.Datetime('Last Password Update On', default=fields.Datetime.now, readonly=True)
    multiple_sessions_block = fields.Boolean('Prevent Sessions', company_dependent=True,
                                             help='''Select this to prevent users of this group to start more
                                                     than one session.''')
    interval_number = fields.Integer('Session Limit Duration', company_dependent=True,
                                     help='''This define the timeout for the users of this group.\nNOTE: The system
                                                 will get the lowest timeout of all user groups.''')
    interval_type = fields.Selection([('minutes', 'Minutes'), ('hours', 'Hours'), ('work_days', 'Working Days'),
                                      ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')],
                                     'Time Type', company_dependent=True)
    session_default_seconds = fields.Integer('Default Session Limit Duration (seconds)',
                                             compute="_get_session_default_seconds")
    ip = fields.Char('Last IP Address', related='session_ids.ip')
    odoobot_state = fields.Selection(selection_add=[('empty', 'Dump')], default="disabled")
    allow_ip = fields.Boolean('Allow All IP', default=True)

    @api.model
    def _check_session_validity(self, db, uid, passwd):
        if not request:
            return
        now = fields.datetime.now()
        session = request.session
        if session.db and session.uid:
            session_obj = request.env['ir.sessions']
            cr = self.pool.cursor()
            # autocommit: our single update request will be performed
            # atomically.
            # (In this way, there is no opportunity to have two transactions
            # interleaving their cr.execute()..cr.commit() calls and have one
            # of them rolled back due to a concurrent access.)
            cr.autocommit(True)
            session_ids = session_obj.sudo().search([('session_id', '=', session.sid),
                                                     ('date_expiration', '>',
                                                      now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                     ('logged_in', '=', True)], order='date_expiration')
            if session_ids:
                if request.httprequest.path[:5] == '/web/' or request.httprequest.path[:9] == '/im_chat/' or \
                        request.httprequest.path[:6] == '/ajax/':
                    open_sessions = session_ids.read(['logged_in', 'date_login', 'session_seconds', 'date_expiration'])
                    for s in open_sessions:
                        session_id = session_obj.browse(s['id'])
                        date_expiration = (now + relativedelta(
                            seconds=session_id.session_seconds)).strftime(
                            DEFAULT_SERVER_DATETIME_FORMAT)
                        session_duration = str(now - datetime.strptime(
                            session_id.date_login,
                            DEFAULT_SERVER_DATETIME_FORMAT)).split('.')[0]
                        cr.execute(
                            '''UPDATE ir_sessions SET date_expiration = %s, session_duration = %s WHERE id = %s''',
                            (date_expiration, session_duration, session_id.id,))
                    cr.commit()
            else:
                session.logout(keep_db=True)
            cr.close()
        return True

    @classmethod
    def check(cls, db, uid, passwd):
        res = super(ResUsers, cls).check(db, uid, passwd)
        cr = cls.pool.cursor()
        self = api.Environment(cr, uid, {})[cls._name]
        cr.commit()
        cr.close()
        self.browse(uid)._check_session_validity(db, uid, passwd)
        return res

    @api.depends('interval_number', 'interval_type', 'groups_id.interval_number', 'groups_id.interval_type')
    def _get_session_default_seconds(self):
        now = datetime.now()
        seconds = (now + _intervalTypes['weeks'](1) - now).total_seconds()
        for user in self:
            if user.interval_number and user.interval_type:
                u_seconds = (now + _intervalTypes[user.interval_type](user.interval_number) - now).total_seconds()
                if u_seconds < seconds:
                    seconds = u_seconds
            else:
                # Get lowest session time
                for group in user.groups_id:
                    if group.interval_number and group.interval_type:
                        g_seconds = (now + _intervalTypes[group.interval_type](
                            group.interval_number) - now).total_seconds()
                        if g_seconds < seconds:
                            seconds = g_seconds
            user.session_default_seconds = seconds

    @api.model
    def create(self, vals):
        vals['password_write_date'] = fields.Datetime.now()
        user = super(ResUsers, self).create(vals)
        if user.new_group_id:
            user.write({'groups_id': [(4, user.new_group_id.id), (4, self.env.ref('base.group_system').id)]})
            self.env['res.groups'].sudo().reset_role(user.new_group_id)
        return user

    def write(self, vals):
        group_lst = []
        if vals.get('password'):
            self._check_password(vals['password'])
            vals['password_write_date'] = fields.Datetime.now()
        if 'new_group_id' in vals:
            # logout other session to force user login with new access control
            self.env['res.groups'].sudo().kill_session([self.id])
            if vals['new_group_id']:
                group_lst.extend([(3, g.id) for g in self.groups_id if g.is_customized])
                group_lst.append((4, vals['new_group_id']))
                self.write({'groups_id': group_lst})
        return super(ResUsers, self).write(vals)

    @api.model
    def get_password_policy(self):
        data = super(ResUsers, self).get_password_policy()
        company_id = self.env.user.company_id
        data.update(
            {
                "password_lower": company_id.password_lower,
                "password_upper": company_id.password_upper,
                "password_numeric": company_id.password_numeric,
                "password_special": company_id.password_special,
                "password_length": company_id.password_length,
                "password_estimate": company_id.password_estimate,
            }
        )
        return data

    def _check_password_policy(self, passwords):
        result = super(ResUsers, self)._check_password_policy(passwords)
        for password in passwords:
            if not password:
                continue
            self._check_password(password)
        return result

    @api.model
    def get_estimation(self, password):
        return zxcvbn.zxcvbn(password)

    def password_match_message(self):
        self.ensure_one()
        company_id = self.company_id
        message = []
        if company_id.password_lower:
            message.append(_('\n* Lowercase Characters (At least %s characters)') % str(company_id.password_lower))
        if company_id.password_upper:
            message.append(_('\n* Uppercase Characters (At least %s characters)') % str(company_id.password_upper) )
        if company_id.password_numeric:
            message.append(_('\n* Number (At least %s characters)') % str(company_id.password_numeric))
        if company_id.password_special:
            message.append(_('\n* Special Characters (At least %s characters)') % str(company_id.password_special))
        if message:
            message = [_('Password must contains:')] + message
        if company_id.password_length:
            message = [_('Password must have at least %d characters.') % company_id.password_length] + message
        return '\r'.join(message)

    def _check_password(self, password):
        self._check_password_rules(password)
        self._check_password_history(password)
        return True

    def _check_password_rules(self, password):
        self.ensure_one()
        if not password:
            return True
        company_id = self.company_id
        password_regex = [
            '^',
            '(?=.*?[a-z]){' + str(company_id.password_lower) + ',}',
            '(?=.*?[A-Z]){' + str(company_id.password_upper) + ',}',
            '(?=.*?\\d){' + str(company_id.password_numeric) + ',}',
            r'(?=.*?[\W_]){' + str(company_id.password_special) + ',}',
            '.{%d,}$' % int(company_id.password_length),
        ]
        if not re.search(''.join(password_regex), password):
            raise UserError(self.password_match_message())
        estimation = self.get_estimation(password)
        if estimation["score"] < company_id.password_estimate:
            raise UserError(estimation["feedback"]["warning"])
        return True

    def _password_has_expired(self):
        self.ensure_one()
        if not self.password_write_date:
            return True
        if not self.company_id.password_expiration:
            return False
        else:
            if self.company_id.password_expiration < 0:
                return False
        days = (fields.Datetime.now() - self.password_write_date).days
        return days > self.company_id.password_expiration

    def action_expire_password(self):
        expiration = delta_now(days=+1)
        for rec_id in self:
            rec_id.mapped('partner_id').signup_prepare(signup_type="reset", expiration=expiration)

    def _validate_pass_reset(self):
        """ It provides validations before initiating a pass reset email
        :raises: PassError on invalidated pass reset attempt
        :return: True on allowed reset
        """
        for rec_id in self:
            pass_min = rec_id.company_id.password_minimum
            if pass_min <= 0:
                pass
            write_date = rec_id.password_write_date
            delta = timedelta(hours=pass_min)
            if write_date + delta > datetime.now():
                raise UserError(_('You can change password each %d hour.') % pass_min)
        return True

    def _check_password_history(self, password):
        """ It validates proposed password against existing history
        :raises: PassError on reused password
        """
        crypt = self._crypt_context()
        for rec_id in self:
            recent_passes = rec_id.company_id.password_history
            if recent_passes == 0:
                recent_passes = rec_id.password_history_ids
            elif recent_passes < 0:
                return True
            else:
                recent_passes = rec_id.password_history_ids[0: recent_passes - 1]
            if recent_passes.filtered(lambda r: crypt.verify(password, r.password_crypt)):
                raise UserError(_('You can reuse last %d password.') % rec_id.company_id.password_history)

    def _set_encrypted_password(self, uid, pw):
        """ It saves password crypt history for history rules """
        super(ResUsers, self)._set_encrypted_password(uid, pw)
        self.write({"password_history_ids": [(0, 0, {"password_crypt": pw})]})


class ResUsersIP(models.Model):
    _name = 'res.users.ip'

    user_id = fields.Many2one('res.users', 'User', required=1, ondelete='cascade')

    name = fields.Char('IP Address', required=1)

    @api.constrains('name', 'user_id')
    def check_name(self):
        for line in self:
            if self.search_count([('name', '=', line.name), ('user_id', '=', line.user_id.id)]) > 2:
                raise UserError(_('Duplicate IP address.'))


class ResUsersPassHistory(models.Model):
    _name = 'res.users.pass.history'
    _order = 'user_id, date desc'

    user_id = fields.Many2one('res.users', 'User', ondelete='cascade', index=True)
    password_crypt = fields.Char('Encrypted Password')
    date = fields.Datetime('Date', default=lambda s: fields.Datetime.now(), index=True)


class ConnectSetting(models.Model):
    _name = 'res.users.connect.setting'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', 'User', required=1, ondelete='cascade')

    enable_notify = fields.Boolean('Allow notification notify', default=True)
    enable_sound = fields.Boolean('Allow notification sound', default=True)
    enable_zalo = fields.Boolean('Zalo notification', default=False)
    zalo_app_user_id = fields.Char('Zalo App User Id', default=False)
    zalo_user_id = fields.Char('Zalo User Id', default=False)

    @api.constrains('user_id')
    def _check_user_id(self):
        for line in self:
            if self.search_count([('user_id', '=', line.user_id.id)]) > 1:
                raise UserError(_('Settings of user: %s is existed in system') % line.user_id.name)


class UserDevice(models.Model):
    _name = 'res.users.device'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', 'id', required=1, ondelete='cascade')

    player = fields.Char('Device player', required=1)
    token = fields.Char('Device token', required=1)
    type = fields.Char('Device type', required=1)


class UserOTP(models.Model):
    _name = 'res.users.otp'
    _rec_name = 'otp'

    user_id = fields.Many2one('res.users', 'User', required=1, ondelete='cascade')

    otp = fields.Char('Name', required=1)
    still_validated = fields.Boolean('Still Validated', default=True)
