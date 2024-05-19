# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# imports of python lib
import datetime
import logging
import json
import werkzeug.wrappers
# imports of odoo
import odoo
from odoo.http import SessionExpiredException, JsonRequest
# imports of odoo modules
from odoo.addons.restful import common, request_restful

_logger = logging.getLogger(__name__)


def valid_response(data, status=200):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {"code": status, "error_message": "", "result": data}
    return werkzeug.wrappers.Response(
        status=status, content_type="application/json; charset=utf-8",
        response=json.dumps(data, default=common.default),
    )


common.valid_response = valid_response


def invalid_response(typ, message=None, status=401):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    error_message = "%s - %s" % (typ, message if message else "")
    data = {"code": status, "error_message": error_message, "result": []}
    return werkzeug.wrappers.Response(
        status=status,
        content_type="application/json; charset=utf-8",
        response=json.dumps(data, default=datetime.datetime.isoformat),
    )


common.invalid_response = invalid_response


# fix error of restful addons, don't know why they not reply data in error message
def _handle_exception(self, exception):
    """Called within an except block to allow converting exceptions
        to arbitrary responses. Anything returned (except None) will
        be used as response."""
    if self.httprequest.headers.get("access-token", False):
        return request_restful(
            self.httprequest, **json.loads(self.httprequest.get_data().decode(self.httprequest.charset))
        )
    try:
        return super(JsonRequest, self)._handle_exception(exception)
    except Exception:
        if not isinstance(exception, (odoo.exceptions.Warning, SessionExpiredException, odoo.exceptions.except_orm,
                                      werkzeug.exceptions.NotFound)):
            _logger.exception("Exception during JSON request handling.")
        error = {
            "code": 200,
            "message": "Server Error",
            'data': odoo.http.serialize_exception(exception)
        }
        return self._json_response(error=error)


JsonRequest._handle_exception = _handle_exception


# update lang to api request
def update_lang(request, res_user=None, lang=None):
    if res_user or lang:
        context = dict(request.context)
        context['lang'] = res_user.partner_id.lang if res_user else lang
        request.context = context
    return request
