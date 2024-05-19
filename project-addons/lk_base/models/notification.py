# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import datetime
import json
import requests
from onesignal_sdk.client import Client as OnesignalClient
from odoo.exceptions import UserError
from ast import literal_eval
import logging
from odoo.addons.lk_base.models.general_data import ar_notification_type, ar_notification_kind, ar_notification_state, \
    ar_notification_process

email_config = ['smtp_server', 'smtp_email', 'smtp_password']
onesignal_config = ['onesignal_appid', 'onesignal_apikey']
zalo_config = ['zalo_auth_code']

_logger = logging.getLogger(__name__)


class NotificationContent(models.Model):
    _name = 'notification.content'
    _rec_name = 'title'
    _order = 'id desc'

    user_id = fields.Many2one('res.users', 'User', required=1)
    company_id = fields.Many2one('res.company', 'Company', required=1, default=lambda self: self.env.company)

    res_id = fields.Integer('Notification Belongs to record ID', required=1)
    send_date = fields.Datetime('Date', required=1)
    title = fields.Char('Title', required=1)
    content = fields.Char('Content', required=1)
    type = fields.Selection(ar_notification_type, 'Type', required=1)
    kind = fields.Selection(ar_notification_kind, 'Kind', required=1)
    state = fields.Selection(ar_notification_state, 'State', required=1)
    process = fields.Selection(ar_notification_process, 'Progress', required=1)
    model = fields.Char('Model', required=1)
    res_model = fields.Char('Function', required=1)
    error_message = fields.Text('Error message', readonly=1)
    is_read = fields.Boolean('Read', default=False, readonly=True)
    is_delete = fields.Boolean('Delete', default=False, readonly=True)

    def write(self, values):
        if any(k in ['is_delete', 'is_read', 'state', 'process', 'user_id'] for k in values.keys()):
            self.handle_notification(self, values)
        return super(NotificationContent, self).write(values)

    def action_read(self):
        """ Action read notification.
            :return:
        """
        self.sudo().write({'is_read': True})

    def action_delete(self):
        """ Action delete notification.
            :return:
        """
        self.sudo().write({'is_delete': True})
        action = self.env.ref('lk_base.notification_content_action').read()[0]
        return {
            'name': action['name'],
            'view_mode': action['view_mode'],
            'res_model': action['res_model'],
            'views': action['views'],
            'type': 'ir.actions.act_window',
            'domain': action['domain'],
            'context': action['context'],
            'target': 'main'
        }

    @api.model
    def get_icon_by_menu(self, menu_id):
        if menu_id.parent_id:
            return self.get_icon_by_menu(menu_id.parent_id)
        else:
            return '/%s' % menu_id.web_icon.replace(',', '/')

    @api.model
    def get_icon_by_action(self, action_xmlid):
        action_id = self.env.ref(action_xmlid)
        context = {'ir.ui.menu.full_list': True}
        menu_obj = self.env['ir.ui.menu'].with_context(context).sudo()
        menu = menu_obj.search([('action', '=', 'ir.actions.act_window,%s' % str(action_id.id))])
        if menu:
            return {
                'web_icon': self.get_icon_by_menu(menu),
                'name': menu.name,
            }
        else:
            return {
                'web_icon': False,
                'name': _('Function'),
            }

    @api.model
    def handle_notification(self, records, values):
        """ Prepare notification data in web if user get new notification.
            :param records: list of ORM records.
            :param values: changed values.
            :return:
        """
        self = self.sudo()
        notifications = []
        for record in records:
            if not values.get('user_id'):
                if values.get('is_read'):
                    notifications.append([(self._cr.dbname, 'res.partner', record.user_id.partner_id.id),
                                          {'type': 'notification_updated', 'notification_deleted': True}])
                else:
                    if values.get('state') == 'sent' and values.get('process') == 'done':
                        notifications.append([(self._cr.dbname, 'res.partner', record.user_id.partner_id.id),
                                              {'type': 'notification_updated', 'notification_created': True}])
            else:
                user = self.env['res.users'].sudo().browse(values.get('user_id'))
                notifications.append([(self._cr.dbname, 'res.partner', record.user_id.partner_id.id),
                                      {'type': 'notification_updated', 'notification_deleted': True}])
                notifications.append([(self._cr.dbname, 'res.partner', user.partner_id.id),
                                      {'type': 'notification_updated', 'notification_created': True}])
        self.env['bus.bus'].sendmany(notifications)

    @api.model
    def systray_get_notifications(self):
        notification_data = self.sudo().search([('is_delete', '!=', True), ('is_read', '!=', True),
                                                ('state', '=', 'sent'), ('process', '=', 'done'),
                                                ('user_id', '=', self.env.user.id)])
        user_notifications = {}
        desc = [{
            'description': _('New Notification'),
            'count': len(notification_data),
            'action_xmlid': 'lk_base.notification_content_action',
            'context': 'search_default_not_read',
            'model_id': self.env.ref('lk_base.model_notification_content').id,
        }]
        count = 0
        for line in desc:
            data = self.get_icon_by_action(line['action_xmlid'])
            user_notifications[count] = {
                'name': data['name'],
                'total_count': line['count'],
                'description': [{'description': line['description'], 'count': line['count']}],
                'icon': data['web_icon'],
                'action_xmlid': line['action_xmlid'],
                'context': line['context'],
            }
            count += 1
        return list(user_notifications.values())

    @api.model
    def create_notification(self, res_model, res_id, title, content, user_lst, send_date, notify_kind,
                            notify_type, company_id):
        """ Create notification.
            :param res_model: function
            :param res_id: record ID in database
            :param title: notification title.
            :param content: notification content.
            :param user_lst: list of user ID received notifications
            :param send_date: date sent notifications
            :param notify_kind: list of kind: app, zalo, facebook,...
            :param notify_type: system or manual.
            :param company_id: company ID in database
            :return:
        """
        if not user_lst:
            return False
        try:
            users = self.env['res.users'].browse(user_lst)
            if not users:
                raise UserError(_('Can\'t find list of user received notifications.'))
        except Exception as e:
            raise UserError(_('Can\'t find list of user received notifications.'))
        if not isinstance(notify_kind, list):
            raise UserError(_('Notify kind must be a list.'))
        notify_value = []
        notify_record = self.env[res_model].browse(res_id)
        func = self.get_available_function(res_model, "create", notify_record)
        for kind in notify_kind:
            # because other channel is not done now
            if kind in ['email', 'app', 'zalo']:
                self.check_settings(kind, company_id)
                for user in users:
                    notify_data = {
                        'title': title,
                        'content': content,
                        'send_date': send_date,
                        'type': notify_type if notify_type in ar_notification_type else 'system',
                        'kind': kind,
                        'user_id': user.id,
                        'state': "queue",
                        'process': "wait",
                        'model': res_model,
                        'res_model': func['name'] if func else res_model,
                        'res_id': res_id,
                        'company_id': company_id,
                    }
                    # we check if user allow notify or not. If not we simple done notification
                    if kind == 'email':
                        valid_user = user.email
                    else:
                        valid_user = self.check_enable_notify([user.id], kind)
                    if not valid_user:
                        notify_data.update({
                            'state': "sent",
                            'process': "done",
                        })
                    notify_value.append(notify_data)
        try:
            notification = self.create(notify_value)
        except Exception as e:
            _logger.info(e)
            raise UserError(_('Can\'t create notifications.'))
        return notification

    @api.model
    def valid_notification(self, notifications):
        """ Valid notification.
            :param notifications: record set of notification
            :return: error if got exception
        """
        try:
            record = self.browse(notifications.ids)
            if not record:
                return _('Can\'t find data of notifications.')
        except Exception as e:
            return _('Can\'t find data of notifications.')
        return False

    @api.model
    def check_settings(self, notify_kind, company_id):
        """ Check if user can send notification.
            :param notify_kind: list of kind: app, zalo, facebook,...
            :param company_id: company ID in database
            :return: error if got exception
        """
        record = self.env['notification.setting'].search([('company_id', '=', company_id)])
        if record:
            if notify_kind == 'app':
                if not all(record[key] for key in onesignal_config):
                    return _('Missing app notification settings for this company %s.') % record.company_id.name
            elif notify_kind == 'email':
                if not all(record[key] for key in email_config):
                    return _('Missing email notification settings for this company %s.') % record.company_id.name
            elif notify_kind == 'zalo':
                if not all(record[key] for key in zalo_config):
                    return _('Missing zalo notification settings for this company %s.') % record.company_id.name
            else:
                return _('Can\'t find notification type.')
        else:
            return _('Missing notification settings.')

    @api.model
    def check_enable_notify(self, user_lst, notify_kind):
        """ Check if user enable notification in app.
            :param user_lst: list of user ID
            :param notify_kind: list of kind: app, zalo, facebook,...
            :return: list of user enable notification
        """
        try:
            records = self.env['res.users'].sudo().browse(user_lst)
            domain = [('user_id', 'in', user_lst)]
            if notify_kind == 'app':
                domain.append(('enable_notify', '=', True))
            elif notify_kind == 'zalo':
                domain.append(('enable_zalo', '=', True))
            else:
                return []
            users_setting = self.env['res.users.connect.setting'].search(domain)
            return users_setting.mapped('user_id').ids
        except Exception as e:
            return []

    @api.model
    def schedule_send_notification(self):
        """ Schedule send 100 notification every 2 minutes.
            :return:
        """
        self = self.sudo()
        notifications = self.search([('state', "=", "queue"), ('process', '=', "wait"),
                                     ("send_date", "<=", datetime.now())], order='send_date')
        for company in notifications.mapped('company_id').ids:
            for kind in [k[0] for k in ar_notification_kind]:
                notification = notifications.filtered(lambda x: x.kind == kind and x.company_id.id == company)
                if kind == 'app':
                    self.with_context(pass_cron_exception=True).send_app_notification(notification)
                elif kind == 'email':
                    self.with_context(pass_cron_exception=True).send_email_notification(notification)
                elif kind == 'zalo':
                    self.with_context(pass_cron_exception=True).send_zalo_notification(notification)

    @api.model
    def send_email_notification(self, notifications, company_id, email_cc=None, email_bcc=None, resend=False):
        """ Send email notification.
            :param notifications: record set of notification
            :param company_id: company ID in database
            :param list email_cc: optional list of string values for CC header (to be joined with commas)
            :param list email_bcc: optional list of string values for BCC header (to be joined with commas)
            :return:
        """
        notify_error = self.valid_notification(notifications)
        setting_error = self.check_settings('email', company_id)
        if notify_error:
            if not self.env.context.get('pass_cron_exception'):
                raise UserError(notify_error)
        elif setting_error:
            _logger.info(setting_error)
            if not self.env.context.get('pass_cron_exception'):
                raise UserError(setting_error)
        else:
            mail_server_obj = self.env['ir.mail_server']
            ir_mail_server = mail_server_obj.search([('company_id', '=', company_id)])
            if ir_mail_server:
                email_cc = email_cc or []
                email_bcc = email_bcc or []
                if not resend:
                    notifications_todo = notifications.filtered(
                        lambda x: x.send_date <= datetime.now() and x.state != 'sent'
                                  and x.process != 'done' and x.user_id.email)
                else:
                    notifications_todo = notifications.filtered(
                        lambda x: x.send_date <= datetime.now() and x.state == 'sent'
                                  and x.process == 'error' and x.user_id.email)
                for notify in notifications_todo[:100]:
                    msg = ir_mail_server.build_email(ir_mail_server.smtp_user, [notify.user_id.email], notify.title,
                                                     notify.content, email_cc, email_bcc)
                    try:
                        ir_mail_server.send_email(msg)
                        notify.write({'process': 'done', 'state': 'sent'})
                    except Exception as e:
                        notify.write({'process': 'error', 'state': 'sent', 'error_message': e})

    @api.model
    def send_app_notification(self, notifications, company_id, other_user=None, resend=False):
        """ Send app notification.
            :param notifications: record set of notification
            :param company_id: company ID in database
            :param list other_user: optional list of user ID to receive notification
            :param resend: resend error notifications
            :return:
        """

        def send_onesignal(app_id, api_key, headings, contents, include_player_ids, additional_data):
            """ Send onesignal.
                :param app_id: onesignal app id
                :param api_key: onesignal api key
                :param obj headings: headings of notifications (obj in multiple languages)
                :param obj contents: contents of notifications (obj in multiple languages)
                :param list include_player_ids: list of device player
                :param obj additional_data: additional data
                :return:
            """
            client = OnesignalClient(app_id=app_id, rest_api_key=api_key)
            payload = {
                'headings': headings,
                'contents': contents,
                'include_player_ids': include_player_ids,
                'data': additional_data,
            }
            return client.send_notification(payload)

        notify_error = self.valid_notification(notifications)
        setting_error = self.check_settings('app', company_id)
        if notify_error:
            if not self.env.context.get('pass_cron_exception'):
                raise UserError(notify_error)
        elif setting_error:
            _logger.info(setting_error)
            if not self.env.context.get('pass_cron_exception'):
                raise UserError(setting_error)
        else:
            if not resend:
                notifications_todo = notifications.filtered(
                    lambda x: x.send_date <= datetime.now() and x.state != 'sent' and x.process != 'done')
            else:
                notifications_todo = notifications.filtered(
                    lambda x: x.send_date <= datetime.now() and x.state == 'sent' and x.process == 'error')
            other_user = other_user or []
            settings = self.env['notification.setting'].search([('company_id', '=', company_id)])
            devices = self.env['res.users.device'].search(
                [('user_id', 'in', notifications_todo.mapped('user_id').ids + other_user)])
            valid_user = self.check_enable_notify(notifications_todo.mapped('user_id').ids + other_user, 'app')
            notifications_todo = notifications_todo.filtered(lambda x: x.user_id.id in valid_user)
            for notify in notifications_todo[:100]:
                player_lst = [device.player for device in devices.filtered(lambda x: x.user_id.id == notify.user_id.id)]
                if player_lst:
                    try:
                        additional_data = {'type': 'notifi', 'action': notify.res_model, 'id': notify.res_id}
                        send_onesignal(settings.onesignal_appid, settings.onesignal_apikey, {'en': notify.title},
                                       {'en': notify.content}, player_lst, additional_data)
                        notify.write({'process': 'done', 'state': 'sent'})
                    except Exception as e:
                        notify.write({'process': 'error', 'state': 'sent', 'error_message': e})
                else:
                    notify.write({'process': 'error', 'state': 'sent', 'error_message': 'User not login app yet'})

    @api.model
    def send_zalo_notification(self, notifications, company_id, resend=False):
        """ Send zalo notification.
            :param notifications: record set of notification
            :param company_id: company ID in database
            :param resend: resend error notifications
            :return:
        """
        notify_error = self.valid_notification(notifications)
        setting_error = self.check_settings('zalo', company_id)
        if notify_error:
            if not self.env.context.get('pass_cron_exception'):
                raise UserError(notify_error)
        elif setting_error:
            _logger.info(setting_error)
            if not self.env.context.get('pass_cron_exception'):
                raise UserError(setting_error)
        else:
            if not resend:
                notifications_todo = notifications.filtered(
                    lambda
                        x: x.send_date <= datetime.now() and x.state != 'sent' and x.process != 'done')
            else:
                notifications_todo = notifications.filtered(
                    lambda
                        x: x.send_date <= datetime.now() and x.state == 'sent' and x.process == 'error')
            settings = self.env['notification.setting'].search([('company_id', '=', company_id)])
            headers = {
                'access_token': settings.zalo_auth_code,
                'Content-Type': 'application/json'
            }
            users_setting = self.env['res.users.connect.setting'].search(
                [('user_id', 'in', notifications.mapped('user_id').ids)])
            valid_user = self.check_enable_notify(notifications_todo.mapped('user_id').ids, 'zalo')
            notifications_todo = notifications_todo.filtered(lambda x: x.user_id.id in valid_user)
            for notify in notifications_todo[:100]:
                zalo_error = False
                try:
                    user_connect = users_setting.filtered(lambda x: x.user_id.id == notify.user_id.id)
                    if user_connect:
                        data = {
                            "recipient": {
                                "user_id": user_connect[-1].zalo_app_user_id,
                            },
                            "message": {
                                "text": notify.content,
                            }
                        }
                        message = requests.post('https://openapi.zalo.me/v2.0/oa/message', data=json.dumps(data),
                                                headers=headers)
                        if json.loads(message.text).get('error'):
                            zalo_error = True
                            raise UserError(json.loads(message.text))
                        notify.write({'process': 'done', 'state': 'sent'})
                    else:
                        notify.write({'process': 'error', 'state': 'sent',
                                      'error_message': _('User not connect zalo in app')})
                except Exception as e:
                    if zalo_error:
                        err = _('Zalo API error: %s') % json.loads(message.text).get('message')
                        notify.write({'process': 'error', 'state': 'sent', 'error_message': err})
                    else:
                        if isinstance(e, dict) and e['message']:
                            notify.write({'process': 'error', 'state': 'sent', 'error_message': e['message']})
                        else:
                            notify.write({'process': 'error', 'state': 'sent', 'error_message': e})
                            
                            
class NotificationSetting(models.Model):
    _name = 'notification.setting'

    company_id = fields.Many2one('res.company', 'Company', required=1, default=lambda self: self.env.company)
    
    onesignal_appid = fields.Char('Onesignal App ID')  # 65eacf24-f3d2-48e4-9fb1-9d76ad0bbe59
    onesignal_apikey = fields.Char('Onesignal API Key')  # MTM1MmZkZDQtY2M3Yy00YWNmLWE0ZDUtNzY3ZWMwYjc2Mzk2
    smtp_server = fields.Char('SMTP server')  # smtp.yandex.com
    smtp_email = fields.Char('SMTP email')  # noreply@liink.vn
    smtp_password = fields.Char('SMTP password')  # Liink!@#.vn#2018
    zalo_auth_code = fields.Char('Zalo Auth Code')  # EQcYS1j3DHSxgQ1x74Wo73gZedOONqi4GRoNQWC1PKHUWhbh1X5N0a2ll6zbDIbA0g378o1BBHPr-kuG0K010qVuo0K3PY0H8V_954DzEmuHpjO_Gtaz6GsIyn5v8sTxAycqQMHy8G8JwyO7Hm4fCcJbm5yKVr4jREc5EnX8OLTQuAX4F4XCVs6lhcuV6KC2FPslQMueMdC9lSfyHma-H3gEzq5EDJfn3xB45ceGLmHAgATgD0XuS6c2ZaKlEX1_Tv_kR2KYEmHqgF1k52flQK7LiqSOJ5vKLt4MqgPV75Ks7W

    @api.constrains('company_id')
    def _check_company_id(self):
        for line in self:
            if self.search_count([('company_id', '=', line.company_id.id)]) > 1:
                raise UserError(_('Settings of company: %s is existed in system') % line.company_id.name)

    @api.model
    def create(self, vals):
        res = super(NotificationSetting, self).create(vals)
        self.check_settings_constraints(res)
        if all(vals.get(key) for key in email_config):
            self.update_mail_server(res)
        return res

    def write(self, vals):
        res = super(NotificationSetting, self).write(vals)
        self.check_settings_constraints(self)
        if any(vals.get(key) for key in email_config):
            self.update_mail_server(self)
        return res

    @api.model
    def update_mail_server(self, record):
        """ Update settings of mail_server.
            :param record: record in database
            :return:
        """
        mail_server_obj = self.env['ir.mail_server']
        mail_server_id = mail_server_obj.search([('company_id', '=', record.company_id.id)])
        if not mail_server_id:
            mail_server_obj.create({
                'name': 'Email settings',
                'smtp_host': record.smtp_server,
                'smtp_port': 25,
                'smtp_user': record.smtp_email,
                'smtp_pass': record.smtp_password,
                'smtp_encryption': 'starttls',
                'company_id': record.company_id.id,
            })
        else:
            mail_server_id.write({
                'smtp_host': record.smtp_server,
                'smtp_user': record.smtp_email,
                'smtp_pass': record.smtp_password,
            })

    @api.model
    def check_settings_constraints(self, record):
        """ Check valid value in record.
            :param record: record in database
            :return:
        """
        if any(record[key] for key in email_config) and not all(record[key] for key in email_config):
            raise UserError(_('Missing email settings for this company %s.') % record.company_id.name)
        if any(record[key] for key in onesignal_config) and not all(record[key] for key in onesignal_config):
            raise UserError(_('Missing onesignal settings for this company %s.') % record.company_id.name)
        if any(record[key] for key in zalo_config) and not all(record[key] for key in zalo_config):
            raise UserError(_('Missing zalo settings for this company %s.') % record.company_id.name)
