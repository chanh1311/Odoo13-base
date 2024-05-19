# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.web.controllers.main import Home, DataSet, clean_action, Action, Session, ReportController, ensure_db
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo import http, fields, api, SUPERUSER_ID, _
from odoo.http import request
import json
import time
import werkzeug
from odoo.addons.http_routing.models.ir_http import slugify
from odoo.tools.safe_eval import safe_eval
import logging
from datetime import datetime
import odoo
import pytz
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessDenied, AccessError
import operator
from odoo.exceptions import UserError
import requests
from odoo.service import security
from odoo.addons.lk_base.models.base import is_allow_action


_logger = logging.getLogger(__name__)

# List of content types that will be opened in browser
OPEN_BROWSER_TYPES = ['application/pdf']
LOGIN_PARAM = 'login_google_recaptcha'
SITE_KEY_PARAM = 'google_recaptcha_site_key'
SECRET_KEY_PARAM = 'google_recaptcha_secret_key'


def verify_recaptcha(captcha_data):
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', captcha_data)
    return r.json()


# restrict user session and ip
class BaseHome(Home):

    # check ip address valid, prevent unauthorized user
    def valid_ipaddress(self):
        ip_address = request.httprequest.environ['REMOTE_ADDR']
        if not request.session.uid:
            login = request.params['login']
        else:
            login = request.session.login
        user_rec = request.env['res.users'].sudo().search([('login', '=', login)])
        if not user_rec.allow_ip:
            ip_list = []
            ip_list.extend(rec.name for rec in user_rec.ip_ids)
            if ip_address in ip_list:
                return True
            else:
                return False
        else:
            return True

    # ideally, this route should be `auth="user"` but that don't work in non-monodb mode.
    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        # prevent normal user access debug mode
        debug = kw.get('debug', False) if 'debug' in kw.keys() else False
        user_id = request.context.get('uid', False)
        if debug or debug == '':
            if user_id != request.env.ref('base.user_admin').id:
                return werkzeug.utils.redirect('/web/login', 303)
        if not request.session.uid:
            return werkzeug.utils.redirect('/web/login', 303)
        else:
            ip_valid = self.valid_ipaddress()
            if not ip_valid:
                return werkzeug.utils.redirect('/web/login', 303)
        if kw.get('redirect'):
            return werkzeug.utils.redirect(kw.get('redirect'), 303)
        request.uid = request.session.uid
        try:
            context = request.env['ir.http'].webclient_rendering_context()
            response = request.render('web.webclient_bootstrap', qcontext=context)
            response.headers['X-Frame-Options'] = 'DENY'
            return response
        except AccessError:
            return werkzeug.utils.redirect('/web/login?error=access')

    @http.route()
    def web_login(self, redirect=None, **kw):
        if not request.registry.get('ir.sessions'):
            return super(BaseHome, self).web_login(redirect=redirect, **kw)
        odoo.addons.web.controllers.main.ensure_db()
        # add recaptcha
        params = request.env['ir.config_parameter'].sudo()
        login_recaptcha = params.get_param(LOGIN_PARAM)
        recaptcha_site_key = params.get_param(SITE_KEY_PARAM)
        request.params.update({
            'login_recaptcha': login_recaptcha,
            'recaptcha_site_key': recaptcha_site_key,
        })
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)
        if not request.uid:
            request.uid = odoo.SUPERUSER_ID
        values = request.params.copy()
        if not redirect:
            redirect = '/web?' + request.httprequest.query_string.decode('utf-8')
        values['redirect'] = redirect
        try:
            values['databases'] = http.db_list()
        except AccessDenied:
            values['databases'] = None
        if request.httprequest.method == 'POST':
            # verify captcha
            is_captcha_verified = False
            if recaptcha_site_key:
                captcha_data = {
                    'secret': params.get_param(SECRET_KEY_PARAM),
                    'response': request.params['field-recaptcha-response'],
                }
                response = verify_recaptcha(captcha_data)
                is_captcha_verified = response.get('success')
            if not is_captcha_verified and recaptcha_site_key:
                values['error'] = _("Invalid reCaptcha")
                response = request.render('web.login', values)
                response.headers['X-Frame-Options'] = 'DENY'
                return response
            old_uid = request.uid
            uid = False
            if request.params.get('login') and request.params.get('password'):
                try:
                    uid = request.session.authenticate(request.session.db, request.params['login'],
                                                       request.params['password'])
                except odoo.exceptions.AccessDenied as e:
                    request.uid = old_uid
                    if e.args == odoo.exceptions.AccessDenied().args:
                        values['error'] = _("Wrong Login/Password")
                    else:
                        values['error'] = e.args[0]
            ip_valid = self.valid_ipaddress()
            # check for multiple sessions block
            message = self.check_session(uid)
            if (not message or uid is SUPERUSER_ID) and ip_valid:
                current_user = request.env['res.users'].browse(uid)
                # default language of user
                if request.context.get('lang'):
                    available_lang = request.env['res.lang'].get_installed()
                    if available_lang and request.context['lang'] in [lang[0] for lang in available_lang]:
                        current_user.write({'lang': request.context['lang']})
                        session_info = request.env['ir.http'].session_info()
                        session_info.update({'lang': request.context['lang']})
                self.save_session(request.env.user.tz, request.httprequest.session.sid)
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            self.save_session(request.env.user.tz, request.httprequest.session.sid, message)
            _logger.error(message)
            request.uid = old_uid
            if not values.get('error') and message:
                values['error'] = _('''Unsuccessful Login:''')
                values['reason1'] = _('- You don\'t have allow to login with this IP.')
                values['reason2'] = _('- Account already login.')
                values['reason3'] = _('''- You can\'t login this time.''')
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employee can access this database. Please contact the administrator.')
        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')
        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True
        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    def check_session(self, uid=False):
        if not uid or uid is SUPERUSER_ID:
            return _("""Wrong Login/Password""")
        multi_ok = True
        calendar_set = 0
        calendar_ok = False
        calendar_group = ''
        now = datetime.now()
        res = False
        sessions = request.env['ir.sessions'].sudo().search([('user_id', '=', uid), ('logged_in', '=', True)])
        if sessions and request.env.user.multiple_sessions_block:
            multi_ok = False
        if multi_ok:
            # check calendars
            attendance_obj = request.env['resource.calendar.attendance']
            # GET USER LOCAL TIME
            tz = pytz.timezone('GMT')
            if request.env.user.tz:
                tz = pytz.timezone(request.env.user.tz)
            tzoffset = tz.utcoffset(now)
            now = now + tzoffset
            if request.env.user.login_calendar_id:
                calendar_set += 1
                # check user calendar
                attendances = attendance_obj.sudo().search([('calendar_id', '=', request.env.user.login_calendar_id.id),
                                                           ('dayofweek', '=', str(now.weekday())),
                                                           ('hour_from', '<=', now.hour + now.minute / 60.0),
                                                           ('hour_to', '>=', now.hour + now.minute / 60.0)])
                if not attendances:
                    res = _("""You can\'t login this time""")
            else:
                # check user groups calendar
                for group in request.env.user.groups_id:
                    if group.login_calendar_id:
                        calendar_set += 1
                        attendances = attendance_obj.sudo().search([('calendar_id', '=', group.login_calendar_id.id),
                                                                    ('dayofweek', '=', str(now.weekday())),
                                                                    ('hour_from', '<=', now.hour + now.minute / 60.0),
                                                                    ('hour_to', '>=', now.hour + now.minute / 60.0)])
                        if attendances:
                            calendar_ok = True
                        else:
                            calendar_group = group.name
                    if sessions and group.multiple_sessions_block:
                        res = _("""Account already login.""")
                        break
                if calendar_set > 0 and not calendar_ok:
                    res = _("""You can\'t login this time""")
        else:
            res = _("""Account already login.""")
        return res

    def save_session(self, tz, sid, unsuccessful_message=''):
        now = fields.datetime.now()
        session_obj = request.env['ir.sessions']
        cr = request.registry.cursor()
        # Get IP, check if it's behind a proxy
        ip = request.httprequest.headers.environ['REMOTE_ADDR']
        forwarded_for = ''
        if 'HTTP_X_FORWARDED_FOR' in request.httprequest.headers.environ and \
                request.httprequest.headers.environ['HTTP_X_FORWARDED_FOR']:
            forwarded_for = request.httprequest.headers.environ['HTTP_X_FORWARDED_FOR'].split(', ')
            if forwarded_for and forwarded_for[0]:
                ip = forwarded_for[0]
        # for GeoIP
        geo_ip_resolver = None
        ip_location = ''
        try:
            import GeoIP
            geo_ip_resolver = GeoIP.open('/usr/share/GeoIP/GeoIP.dat', GeoIP.GEOIP_STANDARD)
        except ImportError:
            geo_ip_resolver = False
        if geo_ip_resolver:
            ip_location = (str(geo_ip_resolver.country_name_by_addr(ip)) or '')
        # autocommit: our single update request will be performed atomically.
        # (In this way, there is no opportunity to have two transactions
        # interleaving their cr.execute()..cr.commit() calls and have one
        # of them rolled back due to a concurrent access.)
        cr.autocommit(True)
        user = request.env.user
        logged_in = True
        uid = user.id
        if unsuccessful_message:
            uid = SUPERUSER_ID
            logged_in = False
            sessions = False
        else:
            sessions = session_obj.sudo().search([('session_id', '=', sid), ('ip', '=', ip), ('user_id', '=', uid),
                                                  ('logged_in', '=', True)])
        if not sessions:
            date_expiration = (now + relativedelta(seconds=user.session_default_seconds)).strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
            values = {
                'user_id': uid,
                'logged_in': logged_in,
                'session_id': sid,
                'session_seconds': user.session_default_seconds,
                'multiple_sessions_block': user.multiple_sessions_block,
                'date_login': now.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'date_expiration': date_expiration,
                'ip': ip,
                'ip_location': ip_location,
                'remote_tz': tz or 'GMT',
                'unsuccessful_message': unsuccessful_message,
            }
            session_obj.sudo().create(values)
            cr.commit()
        cr.close()


class WebSession(http.Controller):

    @http.route(['/ajax/session/'], auth="public", website=True)
    def property_map(self, **kwargs):
        sessions = request.env['ir.sessions'].sudo().search([('logged_in', '=', True),
                                                             ('user_id', '=', request.session.uid)])
        if sessions:
            return json.dumps({})
        if request.session:
            request.session.logout(keep_db=True)
        return json.dumps({'Content-Type': 'application/json; charset=utf-8', 'result': 'true'})


class BaseSession(Session):

    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self, redirect='/web'):
        if request.session:
            sessions = request.env['ir.sessions'].sudo().search([('logged_in', '=', True),
                                                                 ('user_id', '=', request.session.uid)])
            if sessions:
                sessions._on_session_logout(logout_type='ul')
        request.session.logout(keep_db=True)
        return super(BaseSession, self).logout(redirect=redirect)

    # restrict user session
    @http.route('/web/session/get_session_info', type='json', auth="none")
    def get_session_info(self):
        ir_model_data_obj = request.env['ir.model.data']
        res = super(BaseSession, self).get_session_info()
        ir_model_data_ids = ir_model_data_obj.sudo().search_read(
            [('model', '=', 'res.groups'), ('res_id', 'in', request.env.user.groups_id.ids)])
        res['user_groups'] = [r['module'] + "." + r['name'] for r in ir_model_data_ids]
        return res

    # check password policy
    @http.route('/web/session/change_password', type='json', auth="user")
    def change_password(self, fields):
        new_password = operator.itemgetter('new_password')(
            dict(list(map(operator.itemgetter('name', 'value'), fields)))
        )
        user_id = request.env.user
        user_id._check_password(new_password)
        return super(BaseSession, self).change_password(fields)


# check password strength user
class BaseSignupHome(AuthSignupHome):

    def do_signup(self, qcontext):
        password = qcontext.get('password')
        user_id = request.env.user
        user_id._check_password(password)
        return super(BaseSignupHome, self).do_signup(qcontext)

    @http.route('/password_security/estimate', auth='none', type='json')
    def estimate(self, password):
        return request.env['res.users'].sudo().get_estimation(password)

    @http.route()
    def web_login(self, *args, **kw):
        ensure_db()
        response = super(BaseSignupHome, self).web_login(*args, **kw)
        if not request.params.get("login_success"):
            return response
        # Now, I'm an authenticated user
        if not request.env.user._password_has_expired():
            return response
        # My password is expired, kick me out
        request.env.user.action_expire_password()
        request.session.logout(keep_db=True)
        # I was kicked out, so set login_success in request params to False
        request.params['login_success'] = False
        redirect = request.env.user.partner_id.signup_url
        return http.redirect_with_hash(redirect)

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        try:
            return super(BaseSignupHome, self).web_auth_signup(*args, **kw)
        except UserError as e:
            qcontext['error'] = str(e)
            return request.render('auth_signup.signup', qcontext)

    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        """ It provides hook to disallow front-facing resets inside of min
        Unfortuantely had to reimplement some core logic here because of
        nested logic in parent
        """
        qcontext = self.get_auth_signup_qcontext()
        if (request.httprequest.method == 'POST' and qcontext.get('login') and 'error' not in qcontext and
                'token' not in qcontext):
            login = qcontext.get('login')
            user_ids = request.env['res.users'].sudo().search([('login', '=', login)], limit=1,)
            if not user_ids:
                user_ids = request.env['res.users'].sudo().search([('email', '=', login)], limit=1,)
            user_ids._validate_pass_reset()
        return super(BaseSignupHome, self).web_auth_reset_password(*args, **kw)


class BaseDataSet(DataSet):

    # pass security for button object
    @http.route('/web/dataset/call_button', type='json', auth="user")
    def call_button(self, model, method, args, kwargs):
        if not kwargs.get('context'):
            kwargs['context'] = {'pass_security': True}
        else:
            kwargs['context']['pass_security'] = True
        action = self._call_kw(model, method, args, kwargs)
        if isinstance(action, dict) and action.get('type') != '':
            return clean_action(action)
        return False


class BaseAction(Action):

    # pass security for action server
    @http.route('/web/action/run', type='json', auth="user")
    def run(self, action_id):
        result = request.env['ir.actions.server'].with_context(pass_security=True).browse([action_id]).run()
        return clean_action(result) if result else False

    # prevent user access url
    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        res = super(BaseAction, self).load(action_id, additional_context)
        if request.env.user.id > 5 and not request.env.su and res and res['xml_id']:
            action = request.env.ref(res['xml_id'])
            if not is_allow_action(request, 'read', None, False, action):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Warning'),
                        'message': _('404: Not found'),
                        'sticky': False,
                    }
                }
        return res


class BaseReportController(ReportController):

    # preview pdf report
    @http.route([
        '/report/<converter>/<reportname>',
        '/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env['ir.actions.report']._get_report_from_name(reportname)
        context = dict(request.env.context)

        # don't know why report not update lang (session_info) after change preference
        context.update({'lang': request.env.user.partner_id.lang})

        if docids:
            docids = [int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it.
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang'):
                del data['context']['lang']
            context.update(data['context'])
        if converter == 'html':
            html = report.with_context(context).render_qweb_html(docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf':

            # Get filename for report
            filepart = "report"
            if docids:
                if len(docids) > 1:
                    filepart = "%s (x%s)" % (
                    request.env['ir.model'].sudo().search([('model', '=', report.model)]).name, str(len(docids)))
                elif len(docids) == 1:
                    obj = request.env[report.model].browse(docids)
                    if report.print_report_name:
                        filepart = safe_eval(report.print_report_name, {'object': obj, 'time': time})

            pdf = report.with_context(context).render_qweb_pdf(docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)),
                              ('Content-Disposition', 'filename="%s.pdf"' % slugify(filepart))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context).render_qweb_text(docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)


# fix error invalid session when call api
def check_session(session, env):
    with odoo.registry(session.db).cursor() as cr:
        self = odoo.api.Environment(cr, session.uid, {})['res.users'].browse(session.uid)
        sid = self._compute_session_token(session.sid)
        if sid and session.sid and session.session_token and odoo.tools.misc.consteq(sid, session.session_token):
            return True
        self._invalidate_session_cache()
        return False


security.check_session = check_session
