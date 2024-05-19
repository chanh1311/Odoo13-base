# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# -- Purpose:
# -- Create date:
# -- Author:
# -- Update date
# -- Update by
# -- Update content

# imports of python lib

# imports of odoo
from odoo import api, fields, models, _
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError

# imports of odoo modules
from odoo.addons.restful import common
from odoo.addons.lk_base.controllers import restful_common
from odoo.addons.restful.controllers.main import APIController, validate_token


class APIReporting(APIController):

    # We use validate_token to check user authorization so we need use auth = 'none'
    @validate_token
    @http.route('/get_report', methods=["GET"], type='http', auth='none', csrf=False)
    def get_report(self, **kw):
        """ Purpose:
            :param
            :header
                token: Token string
            :return:
        """
        try:
            if request.httprequest.method == 'GET':
                access_token = request.httprequest.headers.get("access_token")
                access_token_data = (
                    request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC",
                                                                  limit=1)
                )
                res_user = request.env["res.users"].sudo().search(
                    [('id', '=', access_token_data.user_id.id)])
                if res_user:
                    result = []
                    # update translation based on current user
                    restful_common.update_lang(request, res_user)
                    return common.valid_response(result)
                else:
                    return common.invalid_response(_("Error"), _("Error"))
            else:
                return common.invalid_response(_("Error"), _("Incomplete param"))
        except AccessError as e:
            return common.invalid_response(_("Access error"), _("Error: %s" % e.name))
        except Exception as e:
            return common.invalid_response(_("Access error"), _("Error: There was an error during processing"))
