# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
from datetime import datetime
from odoo import SUPERUSER_ID, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


LOGOUT_TYPES = [('ul', 'Log Out'), ('to', 'Session Timeout'), ('sk', 'Session Kill')]


class IrSessions(models.Model):
    _name = 'ir.sessions'
    _order = 'logged_in desc, date_expiration desc'
    _rec_name = 'ip'

    user_id = fields.Many2one('res.users', 'User', ondelete='cascade', required=True)
    logged_in = fields.Boolean('Logged In', required=True, index=True)
    session_id = fields.Char('Session ID', size=100, required=True)
    session_seconds = fields.Integer('Session Duration (seconds)')
    multiple_sessions_block = fields.Boolean('Prevent Same Session')
    date_login = fields.Datetime('Login at', required=True)
    date_logout = fields.Datetime('Logout at')
    date_expiration = fields.Datetime('Date Expiration', required=True, index=True,
                                      default=lambda *a: fields.Datetime.now())
    logout_type = fields.Selection(LOGOUT_TYPES, 'Logout Type')
    session_duration = fields.Char('Session Duration')
    user_kill_id = fields.Many2one('res.users', 'User kill session')
    unsuccessful_message = fields.Char('Message', size=252)
    ip = fields.Char('Remote IP', size=15)
    ip_location = fields.Char('IP Address')
    remote_tz = fields.Char('Remote Time Zone', size=32, required=True)

    # scheduler function to validate users session
    @api.model
    def validate_sessions(self):
        sessions = self.sudo().search([('date_expiration', '<=', fields.datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT)), ('logged_in', '=', True)])
        if sessions:
            sessions._close_session(logout_type='to')
        return True

    def action_close_session(self):
        redirect = self._close_session(logout_type='sk')
        if redirect:
            return werkzeug.utils.redirect('/web/login?db=%s' % self.env.cr.dbname, 303)

    def _on_session_logout(self, logout_type=None):
        now = datetime.now()
        cr = self.pool.cursor()
        # autocommit: our single update request will be performed atomically.
        # (In this way, there is no opportunity to have two transactions
        # interleaving their cr.execute()..cr.commit() calls and have one
        # of them rolled back due to a concurrent access.)
        cr.autocommit(True)
        for session in self:
            session_duration = str(now - session.date_login).split('.')[0]
            session.sudo().write({
                'logged_in': False,
                'date_logout': now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'logout_type': logout_type,
                'user_kill_id': SUPERUSER_ID,
                'session_duration': session_duration,
            })
        cr.commit()
        cr.close()
        return True

    def _close_session(self, logout_type=None):
        redirect = False
        for session in self:
            if session.user_id.id == self.env.user.id:
                redirect = True
            session._on_session_logout(logout_type)
        return redirect
