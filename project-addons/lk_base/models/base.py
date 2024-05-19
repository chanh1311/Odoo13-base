# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _, tools
from odoo.osv import expression
from odoo.models import BaseModel
from lxml import etree
import json
import re
from odoo.exceptions import UserError, AccessError
import logging
from odoo.addons.lk_base.models import general_function as gf

_logger = logging.getLogger(__name__)
regex_object_name = re.compile(r'^[a-z_0-9]+$')
regex_field_agg = re.compile(r'(\w+)(?::(\w+)(?:\((\w+)\))?)?')


# fix wrong rec_name when rec_name is number
def name_get(self):
    """ name_get() -> [(id, name), ...]
    Returns a textual representation for the records in ``self``.
    By default this is the value of the ``display_name`` field.
    :return: list of pairs ``(id, text_repr)`` for each records
    :rtype: list(tuple)
    """
    result = []
    name = self._rec_name
    if name in self._fields:
        convert = self._fields[name].convert_to_display_name
        for record in self:
            lang_id = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
            if (isinstance(record[name], int) or isinstance(record[name], float)) and lang_id.thousands_sep:
                result.append((record.id, convert("{:,.0f}".format(record[name]).replace(",", lang_id.thousands_sep), record)))
            else:
                result.append((record.id, convert(record[name], record)))
    else:
        for record in self:
            result.append((record.id, "%s,%s" % (record._name, record.id)))
    return result


BaseModel.name_get = name_get


def is_allow_action(self, method, vals=None, is_warning=True, action_controller=False):
    """ Check user rights.
        :param method: action of user (create, update, delete).
        :param vals: additional variables.
        :param is_warning: system display warning when user not have rights.
        :param action_controller: access rights when load action
        :return: True if user has rights
    """
    func = False
    allow_create = False
    allow_write = False
    allow_unlink = False
    allow_read = False
    action_id = False
    # not check security for wizard
    if not action_controller and self._transient:
        return True
    if self.env.user.id > 5 and not self.env.su and not self.env.context.get('pass_security'):
        available_function_lst = self.env['base'].get_available_function_lst()
        not_check_lst = self.env['base'].get_not_check_lst()
        not_security_lst = self.env['base'].get_not_security_lst()
        if not action_controller:
            if self._name != 'bus.presence' and self._name != 'ir.attachment':
                current_action = self.env.context.get('params', {}).get('action')
                if current_action:
                    if str(current_action).isdigit():
                        action_id = self.env['ir.actions.act_window'].browse(int(current_action))
                    else:
                        action_id = self.env.ref(current_action)
            else:
                return
        else:
            action_id = action_controller
            # allow access some hidden menu
            if method == 'read' and action_id.xml_id in not_check_lst:
                return True
        if action_id:
            menu_ids = self.env['ir.ui.menu'].with_context({'ir.ui.menu.full_list': True}).search(
                [('action', '=', '%s,%s' % (action_id.type, str(action_id.id)))])
            if menu_ids:
                for menu in menu_ids:
                    if not func:
                        func = next(
                            (item for item in available_function_lst if self.env.ref(item["menu_id"]).id == menu.id),
                            False)
        elif not action_controller:
            model_name = self._name
            func = self.get_available_function(model_name, method, self, vals)
        if func:
            if func['menu_id'] in not_security_lst:
                if method in ["create", "write", "unlink"]:
                    return True
            if self.env.user.new_group_id:
                res_group = self.env.user.new_group_id
                function_menu = self.env['function.menu'].search([('name', '=', func['menu_id']),
                                                                  ('group_id', '=', res_group.id)], limit=1,
                                                                 order='id desc')
                if function_menu:
                    allow_read = function_menu.perm_read
                    allow_create = function_menu.perm_create
                    allow_write = function_menu.perm_write
                    allow_unlink = function_menu.perm_unlink
                # allow user update preference
                if vals and func['model'] == 'res.users' and method == "write" and not allow_write:
                    if self.id == self.env.user.id:
                        allow_write = True
                if is_warning:
                    if method == "create" and not allow_create:
                        raise UserError(_('You are not allowed to create data in function %s') % func['name'])
                    elif method == 'write' and not allow_write:
                        raise UserError(_('You are not allowed to update data in function %s') % func['name'])
                    elif method == 'unlink' and not allow_unlink:
                        raise UserError(_('You are not allowed to delete data in function %s') % func['name'])
                if method == "read":
                    return allow_read
                elif method == "create":
                    return allow_create
                elif method == "write":
                    return allow_write
                elif method == "unlink":
                    return allow_unlink
            else:
                raise UserError(_('Please contact your administrator.'))


# define position when add value to selection field
# def _setup_attrs(self, model, name):
#     super(fields.Selection, self)._setup_attrs(model, name)
#     # determine selection (applying 'selection_add' extensions)
#     values = None
#     labels = {}
#     for field in reversed(fields.resolve_mro(model, name, self._can_setup_from)):
#         # We cannot use field.selection or field.selection_add here
#         # because those attributes are overridden by ``_setup_attrs``.
#         if 'selection' in field.args:
#             selection = field.args['selection']
#             if isinstance(selection, list):
#                 if (
#                     values is not None
#                     and values != [kv[0] for kv in selection]
#                 ):
#                     _logger.warning("%s: selection=%r overrides existing selection; use selection_add instead", self, selection)
#                 values = [kv[0] for kv in selection]
#                 labels = dict(selection)
#             else:
#                 self.selection = selection
#                 values = None
#                 labels = {}
#         if 'selection_add' in field.args:
#             selection_add = field.args['selection_add']
#             assert isinstance(selection_add, list), \
#                 "%s: selection_add=%r must be a list" % (self, selection_add)
#             assert values is not None, \
#                 "%s: selection_add=%r on non-list selection %r" % (self, selection_add, self.selection)
#             values = merge_sequences(values, [kv[0] for kv in selection_add])
#             labels.update(kv for kv in selection_add if len(kv) == 2)
#         if 'selection_add_after' in field.args:
#             selection_add_after = field.args['selection_add_after']
#             new_selection = []
#             for item in self.selection:
#                 new_selection.append(item)
#                 items_to_add = selection_add_after.get(item[0], [])
#                 for item_to_add in items_to_add:
#                     new_selection.append(item_to_add)
#             self.selection = list(OrderedDict(new_selection).items())
#     if values is not None:
#         self.selection = [(value, labels[value]) for value in values]
#
#
# fields.Selection._setup_attrs = _setup_attrs


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # determine if many func same model in available function lst
    @api.model
    def get_available_function(self, model_name, method=False, record=False, vals=False):
        """ Find available function from function list. For read, create, write, unlink
            :param model_name: model name.
            :param method: create, write, unlink
            :param record: ORM record (check if create, write, unlink)
            :param vals: vals when write data
            :return: available function dictionary.
        """
        func = False
        available_function_lst = self.get_available_function_lst()
        func_lst = list(filter(lambda menu: menu['model'] == model_name, available_function_lst))
        if func_lst:
            # Example: we check data of res_partner, if data of current record has 'customer' value or not
            # if len(func_lst) > 1:
            #     if method in ['create', 'write', 'unlink'] and (record or vals):
            #         if method in ['create', 'unlink']:
            #             compare_data = record
            #         else:
            #             value = copy.deepcopy(vals)
            #             value = self.env[model_name]._add_missing_default_values(value)
            #             compare_data = value
            #         for rec in func_lst:
            #             if not func:
            #					if model_name == 'dieuchuyen.taisan' and 'loai_giam' in compare_data:
	        #                        if compare_data['loai_giam'] == 'dieu_chuyen' and rec['value'] == 'dieuchuyen_trong':
	        #                            func = rec
	        #                        elif compare_data['loai_giam'] == 'giam_khac' and rec['value'] == 'dieuchuyen_khac':
	        #                            func = rec
            if not func:
                return func_lst[0]
        return func

    # list of object function needed to set security
    @api.model
    def get_available_function_lst(self):
        return []

    # list of menu not needed to log: system.log, notification
    @api.model
    def get_not_log_lst(self):
        return []

    @api.model
    def get_log_list(self):
        available_function_lst = self.get_available_function_lst()
        not_log_lst = self.get_not_log_lst()
        return [r['model'] for r in filter(lambda x: x['menu_id'] not in not_log_lst, available_function_lst)]

    # list of menu not needed to check security: system.log, notification
    @api.model
    def get_not_security_lst(self):
        return []

    # list of action not needed to check access through url like wizard, custom button on tree view
    @api.model
    def get_not_check_lst(self):
        return []

    @api.model
    def hide_report(self, res, report_lst):
        for line in report_lst:
            for print_submenu in res.get('toolbar', {}).get('print', []):
                if print_submenu['id'] == self.env.ref(line).id:
                    res['toolbar']['print'].remove(print_submenu)
        return res

    # Override read_group to calculate the non-stored fields
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        filter_fields = []
        non_store = []
        for fspec in fields:
            match = regex_field_agg.match(fspec)
            name, func, fname = match.groups()
            if func:
                # we have either 'name:func' or 'name:func(fname)'
                fname = fname or name
                field = self._fields.get(fname)
                if not (field.base_field.store and field.base_field.column_type):
                    non_store.append({'aggre_func': func, 'field_name': fname})
                    continue
            filter_fields.append(fspec)
        fields = filter_fields
        res = super(BaseModel, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                orderby=orderby, lazy=lazy)
        model = self.env[self._name]
        for line in res:
            if '__domain' in line:
                model = model.search(line['__domain'])
            for compute_field in non_store:
                val_lst = model.mapped(compute_field['field_name'])
                if compute_field['aggre_func'] == 'max':
                    line[compute_field['field_name']] = max(val_lst)
                elif compute_field['aggre_func'] == 'min':
                    line[compute_field['field_name']] = min(val_lst)
                elif compute_field['aggre_func'] == 'sum':
                    line[compute_field['field_name']] = sum(val_lst)
                elif compute_field['aggre_func'] == 'avg':
                    line[compute_field['field_name']] = round(sum(val_lst) / len(val_lst), 2)
                else:
                    line[compute_field['field_name']] = len(val_lst)
        return res

    @api.model
    def get_record_name(self, model):
        """ Get name attribute of function.
            :param model: function.
            :return: function name if function exists
        """
        return model.name_get()[0][1] if len(model.name_get()) > 0 and model.name_get()[0][1] else ''

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        res = super(BaseModel, self).create(vals_list)
        # not create log when system update
        if len(vals_list) > 0:
            if self.env.user.id > 5:
                log_lst = self.get_log_list()
                for line in res:
                    # new security method
                    if not self._transient:
                        is_allow_action(line, "create")
                    func = self.get_available_function(res._name, "create", line)
                    if func:
                        if res._name in log_lst and not self.env.context.get('hide_log'):
                            self.env['system.log'].with_context(hide_log=True).sudo().create({
                                'user_id': self._uid,
                                'type': 'create',
                                'function': func['menu_id'],
                                'description': '%s: %s' % (func['name'], self.get_record_name(line)),
                            })
        return res

    def write(self, vals):
        # not create log when system update
        if self.env.user.id > 5:
            log_lst = self.get_log_list()
            for line in self:
                # new security method
                if not self._transient:
                    is_allow_action(line, "write", vals)
                if line._name in log_lst and not line.env.context.get('hide_log'):
                    func = self.get_available_function(line._name, "write", line, vals)
                    if func:
                        description = ""
                        for key, value in vals.items():
                            if not getattr(line._fields[key], 'compute'):
                                field_attrs = dict(self.fields_get([key]))[key]
                                if field_attrs['type'] in ['one2many', 'many2many', 'binary', 'image', 'html']:
                                    if not line[key]:
                                        description += _(", create %s") % field_attrs['string']
                                    else:
                                        description += _(", update %s") % field_attrs['string']
                                elif field_attrs['type'] == 'many2one':
                                    field_obj = self.env[field_attrs['relation']].browse(value)
                                    if not line[key]:
                                        origin_value = "\"\""
                                    else:
                                        origin_value = self.get_record_name(line[key])
                                    if origin_value != self.get_record_name(field_obj):
                                        description += ", %s: %s => %s" % (field_attrs['string'], origin_value,
                                                                           self.get_record_name(field_obj))
                                elif field_attrs['type'] == 'selection':
                                    if line[key]:
                                        origin_value = dict(self._fields[key]._description_selection(self.env)).get(line[key])
                                    else:
                                        origin_value = ''
                                    new_value = dict(self._fields[key]._description_selection(self.env)).get(value)
                                    if origin_value != new_value:
                                        description += ", %s: %s => %s" % (field_attrs['string'], str(origin_value),
                                                                           str(new_value))
                                else:
                                    if str(line[key]) != str(value):
                                        before_value = line[key]
                                        after_value = value
                                        if field_attrs['type'] in ['integer', 'float']:
                                            before_value = str(gf.format_number(self, before_value))
                                            after_value = str(gf.format_number(self, after_value))
                                        description += ", %s: %s => %s" % (field_attrs['string'], str(before_value),
                                                                           str(after_value))
                        description = description[2:]
                        if description != "":
                            self.env['system.log'].with_context(hide_log=True).sudo().create({
                                'user_id': self._uid if self._uid else 1,
                                'type': 'write',
                                'function': func['menu_id'],
                                'description': "%s: %s with %s" % (func['name'], self.get_record_name(line), description),
                            })
        res = super(BaseModel, self).write(vals)
        return res

    def unlink(self):
        # not create log when system update
        if self.env.user.id > 5:
            log_lst = self.get_log_list()
            for line in self:
                # new security method
                is_allow_action(line, "unlink")
                if line._name in log_lst and not line.env.context.get('hide_log'):
                    func = self.get_available_function(line._name, "create", line)
                    if func:
                        self.env['system.log'].with_context(hide_log=True).sudo().create({
                            'user_id': self._uid,
                            'type': 'unlink',
                            'function': func['menu_id'],
                            'description': "%s: %s" % (func['name'], self.get_record_name(line)),
                        })
        return super(BaseModel, self).unlink()

    # new access right in view
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(BaseModel, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                     submenu=submenu)
        doc = etree.XML(res['arch'])
        if self.env.user.id > 5 and view_type in ['tree', 'form', 'kanban', 'calendar']:
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if not is_allow_action(self, operation, None, False):
                    doc.set(action, 'false')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('field_description', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        obj = self.search(domain + args, limit=limit)
        return obj.name_get()

    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s' % field.field_description))
        return res


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    def get_data_from_xmlid(self, res_id, module, model):
        data_id = self.search([('res_id', '=', res_id), ('module', '=', module), ('model', '=', model)], limit=1)
        if data_id:
            return data_id
        return False


class Module(models.Model):
    _inherit = "ir.module.module"

    # restrict name, if modifying odoo report name of module can't have upper case
    @api.constrains('name')
    def valid_name(self):
        for line in self:
            if regex_object_name.match(line.name) is None:
                raise UserError('Name of module %s is not valid, only support character: [a-z_0-9]' % line.name)


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
    def _visible_menu_ids(self, debug=False):
        """ Return the ids of the menu items visible to the user. """
        # retrieve all menus, and determine which ones are visible\
        # fix factory role can't see menu
        self = self.sudo()
        context = {'ir.ui.menu.full_list': True}
        menus = self.with_context(context).search([])
        groups = self.env.user.groups_id
        if not debug:
            groups = groups - self.env.ref('base.group_no_one')
        # first discard all menus with groups the user does not have
        menus = menus.filtered(
            lambda menu: not menu.groups_id or menu.groups_id & groups)
        # take apart menus that have an action
        action_menus = menus.filtered(lambda m: m.action and m.action.exists())
        folder_menus = menus - action_menus
        visible = self.browse()
        # process action menus, check whether their action is allowed
        access = self.env['ir.model.access']
        MODEL_GETTER = {
            'ir.actions.act_window': lambda action: action.res_model,
            'ir.actions.report': lambda action: action.model,
            'ir.actions.server': lambda action: action.model_id.model,
        }

        # new restrict menu with new_group_id
        remove_menu = []
        hide_menu = []
        if self.env.user.new_group_id:
            available_function_lst = self.get_available_function_lst()
            function_access = self.env.user.new_group_id.function_access
            access_menu = [self.env.ref(function.name).id for function in function_access if
                           self.env.ref(function.name, raise_if_not_found=False)]
            remove_menu = [self.env.ref(function.name).id for function in function_access if
                           self.env.ref(function.name, raise_if_not_found=False) and not function.perm_read]
            hide_menu = [self.env.ref(function['menu_id']).id for function in available_function_lst if
                         self.env.ref(function['name'], raise_if_not_found=False) and
                         self.env.ref(function['menu_id']).id not in access_menu]

        for menu in action_menus:
            if menu.id in remove_menu + hide_menu:
                continue
            get_model = MODEL_GETTER.get(menu.action._name)
            if not get_model or not get_model(menu.action) or \
                    access.check(get_model(menu.action), 'read', False):
                # make menu visible, and its folder ancestors, too
                visible += menu
                menu = menu.parent_id
                while menu and menu in folder_menus and menu not in visible:
                    visible += menu
                    menu = menu.parent_id
        return set(visible.ids)


class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    company_id = fields.Many2one('res.company', 'Company', required=1, default=lambda self: self.env.company,
                                 ondelete='cascade')
