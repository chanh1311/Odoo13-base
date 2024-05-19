# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
import copy
from odoo import api, models, fields, _
from odoo.exceptions import Warning, UserError
import tempfile
import binascii
import xlrd
import logging
from odoo.addons.lk_base.models import general_function

_logger = logging.getLogger(__name__)
try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class DynamicImportExecute(models.TransientModel):
    _name = 'dynamic.import.execute'

    import_id = fields.Many2one('dynamic.import', 'Dynamic Import', required=1)

    template = fields.Binary('Template', related='import_id.template', readonly=1)
    template_name = fields.Char(related='import_id.template_name')
    import_file = fields.Binary('File Import', required=1)
    import_filename = fields.Char()

    @api.model
    def filter_values(self, new_values):
        # filter values again, in case function cannot handle difficult case
        return new_values

    def read_import(self):
        """ File excel fmt:
            field Index only for import sub model same time
            Row 1: ID, field1, field2, field3,..., subfield1, subfield2, subfield3
            Row 2: ID, "", "", "" ,..., subfield1, subfield2, subfield3
        """
        try:
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.import_file))
            fp.seek(0)
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
        except:
            raise Warning(_("Excel format must be .xlsx or .xls!"))
        is_sub = 0 if not self.import_id.sub_model_id else 1
        if sheet.ncols != len(self.import_id.line_ids) + len(self.import_id.sub_model_ids) + is_sub:
            raise Warning(_("Wrong Excel Format!"))
        all_values = []
        for row_no in range(sheet.nrows):
            # append value per excel_id (determine multiple row with same parent)
            # Ex: [{'excel_id': 1.0, 'values': [{'title': 'Policy company', 'sub_data': [], 'row_no': 1}]}]
            if row_no > 0:
                if not is_sub:
                    main_value = self.prepare_field(workbook, row_no, self.import_id.line_ids, 0)
                    new_excel = {'values': [main_value]}
                    all_values.append(new_excel)
                else:
                    excel_id = str(sheet.cell_value(row_no, 0)).strip().replace("'", "''")
                    if not excel_id:
                        raise Warning(_('First column value cannot be empty at {}.'.format(row_no + 1)))
                    else:
                        try:
                            excel_id = float(excel_id)
                        except Exception:
                            raise Warning(
                                _('Invalid value {} at {}. First column value must be integer.'.format(
                                    excel_id, row_no + 1)))
                    exist_excel = list(filter(lambda x: x['excel_id'] == excel_id, all_values))
                    if not exist_excel:
                        new_excel = {'excel_id': excel_id, 'values': []}
                    else:
                        new_excel = exist_excel[0]
                    main_value = self.prepare_field(workbook, row_no, self.import_id.line_ids, 1)
                    sub_value = self.prepare_field(workbook, row_no, self.import_id.sub_model_ids,
                                                   len(self.import_id.line_ids) + is_sub)
                    if sub_value:
                        if 'sub_data' not in main_value:
                            main_value['sub_data'] = []
                        if not exist_excel:
                            main_value['sub_data'].append(sub_value)
                        else:
                            new_excel['values'][-1]['sub_data'].append(sub_value)
                    if not exist_excel:
                        new_excel['values'].append(main_value)
                        all_values.append(new_excel)
        new_values = self.validate_field(all_values, workbook)
        new_values = self.filter_values(new_values)
        self.execute_import(new_values)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def prepare_field(self, workbook, row_no, data, col_index):
        # get data of cell from excel and return field name and field value. Ex: {'title': 'Title'}
        sheet = workbook.sheet_by_index(0)
        row_values = {'row_no': row_no + 1}
        for rec in data.sorted(key=lambda r: r.sequence):
            if isinstance(sheet.cell_value(row_no, col_index), int) or \
                    isinstance(sheet.cell_value(row_no, col_index), float):
                if rec.field_type in ('char', 'text', 'html'):
                    value = str(int(float(sheet.cell_value(row_no, col_index)))).strip().replace("'", "''")
                else:
                    value = float(sheet.cell_value(row_no, col_index))
            else:
                value = str(sheet.cell_value(row_no, col_index)).strip().replace("'", "''")
            row_values.update({
                rec.field_id.name: value,
            })
            col_index += 1
        return row_values

    @api.model
    def validate_cell(self, value, d_value, row_no, workbook, is_sub=False):
        all_fields = [{
            'required': f.is_required,
            'type': f.field_type,
            'name': f.field_id.name,
            'relation': f.field_id.relation,
            'description': f.field_id.field_description,
        } for f in (self.import_id.line_ids if not is_sub else self.import_id.sub_model_ids)]
        user_lang = self.sudo().env['res.lang']._lang_get(self.env.user.lang)
        for k, v in value.items():
            if k not in ['row_no', 'sub_data']:
                current_field = list(filter(lambda x: x['name'] == k, all_fields))[0]
                if current_field["required"] and not v:
                    raise Warning(_('Missing value {} at {}.'.format(current_field["description"], row_no)))
                if current_field['type'] == 'many2one' and v:
                    search_field = self.env[current_field['relation']]._rec_name
                    if not search_field:
                        search_field = 'name'
                    relation_id = self.env[current_field['relation']].search_read([(search_field, '=ilike', v)],
                                                                                  ['id'], limit=1)
                    if not relation_id:
                        raise Warning(_('{} not exist in database at {}.'.format(v, row_no)))
                    d_value[k] = relation_id[0]['id']
                elif current_field['type'] in ('integer', 'float', 'monetary'):
                    try:
                        d_value[k] = float(v)
                    except Exception:
                        raise Warning(_('{} must contains only number at {}.'.format(
                            current_field["description"], row_no)))
                elif current_field['type'] == 'boolean':
                    try:
                        d_value[k] = general_function.str2bool(str(v))
                    except Exception:
                        raise Warning(_('Invalid value {} at {}. Valid values are: "True"/1, "False"/0'.format(
                            current_field["description"], row_no)))
                elif current_field['type'] == 'date':
                    if isinstance(v, str):
                        try:
                            d_value[k] = datetime.strptime(v, user_lang.date_format)
                        except Exception as e:
                            raise Warning(_('Invalid value {} at {}.'.format(v, row_no)))
                    else:
                        try:
                            d_value[k] = xlrd.xldate.xldate_as_datetime(v, workbook.datemode)
                        except Exception as e:
                            raise Warning(_('Invalid value {} at {}.'.format(v, row_no)))
                elif current_field['type'] == 'datetime':
                    if isinstance(v, str):
                        try:
                            d_value[k] = datetime.strptime(v, "%s %s" % (
                                user_lang.date_format, user_lang.time_format))
                        except Exception as e:
                            raise Warning(_('Invalid value {} at {}.'.format(v, row_no)))
                    else:
                        try:
                            d_value[k] = xlrd.xldate.xldate_as_datetime(v, workbook.datemode)
                        except Exception as e:
                            raise Warning(_('Invalid value {} at {}.'.format(v, row_no)))
                elif current_field['type'] == 'selection':
                    selections = self.env['ir.model.fields.selection'].search_read([
                        ('field_id.name', '=', k), ('name', '=ilike', v)], ['id'], limit=1)
                    if not selections:
                        raise Warning(
                            _('Invalid value %s at %s.'.format(current_field["description"], row_no)))
                    d_value[k] = selections[0]['id']

    @api.model
    def validate_field(self, values, workbook):
        # validate field based on field_id
        # Ex: [{'excel_id': 1.0, 'values': [{'title': 'Policy company', 'sub_data': [], 'row_no': 1}]}]
        d_values = copy.deepcopy(values)
        for index, row in enumerate(values):
            d_row = d_values[index]
            for i, value in enumerate(row['values']):
                d_value = d_row['values'][i]
                self.validate_cell(value, d_value, value['row_no'], workbook)
                if 'sub_data' in value:
                    for si, sd in enumerate(value['sub_data']):
                        s_value = d_value['sub_data'][si]
                        self.validate_cell(sd, s_value, sd['row_no'], workbook, True)
        return d_values

    def execute_import(self, values):
        # We import main and sub value same time
        # Ex: [{'excel_id': 1.0, 'values': [{'title': 'Policy company', 'sub_data': [], 'row_no': 1}]}]
        model = self.env[self.import_id.model_id.model]
        new_values = []
        for row in values:
            for m in row['values']:
                main_value = {k: v for k, v in m.items() if k not in ['row_no', 'sub_data']}
                if self.import_id.sub_model_id:
                    sub_values = []
                    for s in m['sub_data']:
                        sub_values.append((0, 0, {k: v for k, v in s.items() if k not in ['row_no']}))
                    main_value[self.import_id.sub_field_name] = sub_values
                new_values.append(main_value)
        if new_values:
            model.create(new_values)
        return {'type': 'ir.actions.act_window_close'}
