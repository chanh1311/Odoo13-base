# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    password_expiration = fields.Integer(related="company_id.password_expiration", readonly=False)
    password_minimum = fields.Integer(related="company_id.password_minimum", readonly=False)
    password_history = fields.Integer(related="company_id.password_history", readonly=False)
    password_length = fields.Integer(related="company_id.password_length", readonly=False)
    password_lower = fields.Integer(related="company_id.password_lower", readonly=False)
    password_upper = fields.Integer(related="company_id.password_upper", readonly=False)
    password_numeric = fields.Integer(related="company_id.password_numeric", readonly=False)
    password_special = fields.Integer(related="company_id.password_special", readonly=False)
    password_estimate = fields.Integer(related="company_id.password_estimate", readonly=False)
    enable_upper = fields.Boolean(related="company_id.enable_upper", readonly=False)
    enable_numeric = fields.Boolean(related="company_id.enable_numeric", readonly=False)
    enable_special = fields.Boolean(related="company_id.enable_special", readonly=False)
    pass_strength = fields.Selection(related="company_id.pass_strength", readonly=False, required=1)
    enable_reuse = fields.Boolean(related="company_id.enable_reuse", readonly=False)
    enable_change_password = fields.Selection(related="company_id.enable_change_password", readonly=False, required=1)
    enable_expiration = fields.Selection(related="company_id.enable_expiration", readonly=False, required=1)
    login_google_recaptcha = fields.Boolean("Recaptcha")
    google_recaptcha_site_key = fields.Char("Google Recaptcha Site Key")  # 6Le2xOQZAAAAAH0kR53JQp-eASwGpJxEMnQpLS3z
    google_recaptcha_secret_key = fields.Char("Google Recaptcha Secret Key")  # 6Le2xOQZAAAAAN4U_EYb9qc5YMf8TOzPAR_ocp74
    logo = fields.Binary("Logo", related="company_id.logo", readonly=False)
    favicon = fields.Binary("Favicon", related="company_id.favicon", readonly=False)
    onesignal_appid = fields.Char('Onesignal App ID')
    onesignal_apikey = fields.Char('Onesignal API Key')
    smtp_server = fields.Char('SMTP server')
    smtp_email = fields.Char('SMTP email')
    smtp_password = fields.Char('SMTP password')
    zalo_auth_code = fields.Char('Zalo Auth Code')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(logo=self.env.company.logo,
                   login_google_recaptcha=params.get_param('login_google_recaptcha'),
                   google_recaptcha_site_key=params.get_param('google_recaptcha_site_key'),
                   google_recaptcha_secret_key=params.get_param('google_recaptcha_secret_key'))
        setting = self.env['notification.setting'].search([('company_id', '=', self.env.user.company_id.id)])
        if setting:
            res.update(onesignal_appid=setting.onesignal_appid,
                       onesignal_apikey=setting.onesignal_apikey,
                       smtp_server=setting.smtp_server,
                       smtp_email=setting.smtp_email,
                       zalo_auth_code=setting.zalo_auth_code)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('login_google_recaptcha', self.login_google_recaptcha)
        params.set_param('google_recaptcha_site_key', self.google_recaptcha_site_key)
        params.set_param('google_recaptcha_secret_key', self.google_recaptcha_secret_key)
        params.set_param('auth_password_policy.minlength', self.password_length)
        setting_obj = self.env['notification.setting']
        setting = setting_obj.search([('company_id', '=', self.env.user.company_id.id)])
        values = {
            'company_id': self.env.user.company_id.id,
            'onesignal_appid': self.onesignal_apikey,
            'onesignal_apikey': self.onesignal_apikey,
            'smtp_server': self.smtp_server,
            'smtp_email': self.smtp_email,
            'smtp_password': self.smtp_password,
            'zalo_auth_code': self.zalo_auth_code,
        }
        if not setting:
            setting_obj.with_context(hide_log=True).create(values)
        else:
            setting.with_context(hide_log=True).write(values)
