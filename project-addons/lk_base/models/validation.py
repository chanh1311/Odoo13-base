# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from lxml import etree
from odoo import tools
from odoo.tools.view_validation import _relaxng_cache
from contextlib import closing
from functools import wraps
import logging
from psycopg2 import IntegrityError, OperationalError, errorcodes
import random
import time
import odoo
from odoo.exceptions import UserError, ValidationError, QWebException
from odoo.tools.translate import translate, translate_sql_constraint
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY, MAX_TRIES_ON_CONCURRENCY_FAILURE

_logger = logging.getLogger(__name__)


def custom_relaxng(view_type):
    """
    Inherit the rng validation process to include custom rng files which include our custom attributes.
    """
    rng_name = os.path.join("base", "rng", "%s_view.rng" % view_type)
    if view_type == "tree":
        rng_name = os.path.join("lk_base", "rng", "tree_view.rng")

    if view_type not in _relaxng_cache:
        with tools.file_open(rng_name) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception("Failed to load RelaxNG XML schema for views validation %s" % (view_type))
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


odoo.tools.view_validation.relaxng = custom_relaxng


# we change error notifications of odoo then normal user can read it
def check(f):
    @wraps(f)
    def wrapper(___dbname, *args, **kwargs):
        """ Wraps around OSV functions and normalises a few exceptions
        """
        dbname = ___dbname      # NOTE: this forbid to use "___dbname" as arguments in http routes

        def tr(src, ttype):
            # We try to do the same as the _(), but without the frame
            # inspection, since we aready are wrapping an osv function
            # trans_obj = self.get('ir.translation') cannot work yet :(
            ctx = {}
            if not kwargs:
                if args and isinstance(args[-1], dict):
                    ctx = args[-1]
            elif isinstance(kwargs, dict):
                if 'context' in kwargs:
                    ctx = kwargs['context']
                elif 'kwargs' in kwargs and kwargs['kwargs'].get('context'):
                    # http entry points such as call_kw()
                    ctx = kwargs['kwargs'].get('context')
                else:
                    try:
                        from odoo.http import request
                        ctx = request.env.context
                    except Exception:
                        pass

            lang = ctx and ctx.get('lang')
            if not (lang or hasattr(src, '__call__')):
                return src

            # We open a *new* cursor here, one reason is that failed SQL
            # queries (as in IntegrityError) will invalidate the current one.
            with closing(odoo.sql_db.db_connect(dbname).cursor()) as cr:
                if ttype == 'sql_constraint':
                    res = translate_sql_constraint(cr, key=key, lang=lang)
                else:
                    res = translate(cr, name=False, source_type=ttype,
                                    lang=lang, source=src)
                return res or src

        def _(src):
            return tr(src, 'code')

        tries = 0
        while True:
            try:
                if odoo.registry(dbname)._init and not odoo.tools.config['test_enable']:
                    raise odoo.exceptions.Warning('Currently, this database is not fully loaded and can not be used.')
                return f(dbname, *args, **kwargs)
            except (OperationalError, QWebException) as e:
                if isinstance(e, QWebException):
                    cause = e.qweb.get('cause')
                    if isinstance(cause, OperationalError):
                        e = cause
                    else:
                        raise
                # Automatically retry the typical transaction serialization errors
                if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                if tries >= MAX_TRIES_ON_CONCURRENCY_FAILURE:
                    _logger.info("%s, maximum number of tries reached" % errorcodes.lookup(e.pgcode))
                    raise
                wait_time = random.uniform(0.0, 2 ** tries)
                tries += 1
                _logger.info("%s, retry %d/%d in %.04f sec..." % (errorcodes.lookup(e.pgcode), tries, MAX_TRIES_ON_CONCURRENCY_FAILURE, wait_time))
                time.sleep(wait_time)
            except IntegrityError as inst:
                registry = odoo.registry(dbname)
                key = inst.diag.constraint_name
                if key in registry._sql_constraints:
                    raise ValidationError(tr(key, 'sql_constraint') or inst.pgerror)
                if inst.pgcode in (errorcodes.NOT_NULL_VIOLATION, errorcodes.FOREIGN_KEY_VIOLATION, errorcodes.RESTRICT_VIOLATION):
                    msg = _('The operation cannot be completed')
                    _logger.debug("IntegrityError", exc_info=True)
                    try:
                        # Get corresponding model and field
                        model = field = None
                        for name, rclass in registry.items():
                            if inst.diag.table_name == rclass._table:
                                model = rclass
                                field = model._fields.get(inst.diag.column_name)
                                break
                        if inst.pgcode == errorcodes.NOT_NULL_VIOLATION:
                            # This is raised when a field is set with `required=True`. 2 cases:
                            # - Create/update: a mandatory field is not set.
                            # - Delete: another model has a not nullable using the deleted record.
                            msg = _(
                                'Operation can\'t completed because: \n'
                                '- A mandatory data is missing.\n'
                                '- Function requires this data. If possible, archive it instead.'
                            )
                            if model:
                                func = self.get_available_function(model._name)
                                func_name = func['name'] if func else model._description
                                msg += '\n{}, {} {}'.format(
                                    _('Function %s') % func_name,
                                    _('Value:'), field.string if field else _('Unknown')
                                )
                        elif inst.pgcode == errorcodes.FOREIGN_KEY_VIOLATION:
                            # This is raised when a field is set with `ondelete='restrict'`, at
                            # unlink only.
                            msg = _('Another function requires this data. If possible, archive it instead.')
                            constraint = inst.diag.constraint_name
                            if model:
                                func = self.get_available_function(model._name)
                                func_name = func['name'] if func else model._description
                                msg = '{} {}'.format(
                                    _('Function %s') % func_name, _('requires this data. If possible, archive it instead.')
                                )
                    except Exception:
                        pass
                    raise ValidationError(msg)
                else:
                    raise ValidationError(inst.args[0])

    return wrapper


odoo.service.model.check = check
