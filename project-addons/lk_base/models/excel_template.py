# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
import re
import os
import base64
from odoo.modules.module import get_module_path
from os.path import join as opj
from . import excel_common as co
import json


class ExcelTemplate(models.Model):
    _name = "excel.template"
    _order = "name"

    model_id = fields.Many2one("ir.model", "Report Model", required=1)
    detail_ids = fields.One2many("excel.template.detail", "template_id")

    name = fields.Char("Unique Template Name", required=1)
    report_name = fields.Char('Excel Report Name', required=1)
    fname = fields.Char("File Name", required=1)
    datas = fields.Binary("File Content")
    instruction = fields.Text("Instruction", compute="_compute_output_instruction")
    per_sheet = fields.Boolean('Record per sheet')
    manual_data = fields.Text("Manual data in list")

    # load file excel for create data from xml, loaded file will store in datas field
    @api.model
    def load_excel_template(self, template_ids, addon=False):
        """ get excel template in source
            :param:
                template_ids: list of template ID
                addon: specific module or current module name
            :return: True if find template
        """
        for template in self.browse(template_ids):
            if not addon:
                addon = os.path.dirname(os.path.join(os.path.dirname(__file__), "..", ".."))
            addon_path = get_module_path(addon)
            file_path = False
            for root, _dirs, files in os.walk(addon_path):
                for name in files:
                    if name == template.fname:
                        file_path = os.path.abspath(opj(root, name))
            if file_path:
                template.datas = base64.b64encode(open(file_path, "rb").read())
            else:
                raise UserError('Missing excel template file')
        return True

    @api.model
    def prepare_template(self, template_data, detail_data=None, manual_data=None, addon=None):
        """ prepare excel template if not found
            :param:
                template_name: unique excel template name
                detail_data: data based on record name of model
                manual_data: manual data in list
                addon: specific module or current module name
            :return: excel template and detail records
        """
        # detail_data = [
        #     {'excel_cell': "", 'section_type': "head", 'row_field': "_HEAD_", 'field_name': ""},
        #     {'excel_cell': "B3", 'section_type': "data", 'row_field': "", 'field_name': "code"},
        #     {'excel_cell': "", 'section_type': "row", 'row_field': "detail_ids", 'field_name': ""},
        #     {'excel_cell': "A10", 'section_type': "data", 'row_field': "", 'field_name': "code"},
        # ]
        if detail_data is None:
            detail_data = []
        model_id = self.env['ir.model'].search([('model', '=', template_data['model_name'])])
        if not model_id:
            raise UserError('Model name %s not found' % template_data['model_name'])
        detail_ids = []
        for line in detail_data:
            detail_dct = {}
            for k, v in line.items():
                detail_dct[k] = v
            detail_ids.append((0, 0, detail_dct))
        template_id = self.create([{
            'model_id': model_id.id,
            'fname': template_data['file_name'],
            'name': template_data['template_name'],
            'report_name': template_data['report_name'],
            'per_sheet': template_data['per_sheet'],
            'detail_ids': detail_ids,
            'manual_data': json.dumps(manual_data) if manual_data else '',
        }])
        # binding excel file to excel template
        self.load_excel_template([template_id.id], addon)

    @api.model
    def export_excel(self, ids, data, report_model, addon=None):
        """ export file
            :param:
                ids: specific record ID
                data:
                    file_name: template file
                    template_name: unique template name
                    res_model: if per_sheet
                    report_name: if not per_sheet
                    per_sheet: data displayed per sheet
                    detail_data: data based on record name of model
                    manual_data: manual data in list
                report_model: transient model to store data, usually is report.out
                addon: specific module or current module name
            :return: excel template and detail records
        """
        domain = []
        if ids:
            domain.append(('id', 'in', ids))
        record_ids = self.env[data['res_model']].search(domain, order="id")
        template = self.search([('name', '=', data['template_name'])])
        if not template:
            template_data = {
                'file_name': data['file_name'],
                'template_name': data['template_name'],
                'report_name': data['report_name'],
                'per_sheet': data['per_sheet'],
            }
            if data['per_sheet']:
                template_data['model_name'] = data['res_model']
            else:
                template_data['model_name'] = data['report_model']
            detail_data = data['detail_data']
            manual_data = data['manual_data']
            self.prepare_template(template_data, detail_data, manual_data, addon)
        else:
            if data['manual_data']:
                template.write({'manual_data':  json.dumps(data['manual_data'])})
        if data['per_sheet']:
            out_file, out_name = self.env['excel.export'].export_xlsx(data['template_name'], data['res_model'],
                                                                      record_ids.ids)
        else:
            vals = {}
            if self.env['ir.model.fields'].search([('model', '=', report_model), ('name', '=', 'results')]):
                vals['results'] = record_ids.ids
            new_export = self.env[report_model].create([vals])
            out_file, out_name = self.env['excel.export'].export_xlsx(data['template_name'], data['report_model'],
                                                                      new_export.id)
        act_id = self.env['report.out'].create({
            'report_data': out_name,
            'file_name': out_file,
        })
        return ["report.out", act_id.id, act_id.report_data]

    @api.constrains('name')
    def check_name(self):
        for line in self:
            if ' ' in line.name:
                raise UserError('Name cannot contain space')
            if not bool(re.match('^[a-zA-Z0-9._]*$', line.name)):
                raise UserError('Name can only contain a-zA-Z0-9._')
            if self.search_count([('name', '=', line.name)]) > 1:
                raise UserError('Duplicate template name')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s_copy") % self.name
        return super(ExcelTemplate, self).copy(default=default)

    def _compute_output_instruction(self):
        for rec in self:
            inst_dict = {}
            prev_row = False
            # Export Instruction
            itype = "__EXPORT__"
            inst_dict[itype] = {}
            for line in rec.detail_ids:
                if line.section_type in ("head", "row"):
                    row_field = line.row_field
                    row_dict = {row_field: {}}
                    inst_dict[itype].update(row_dict)
                    prev_row = row_field
                    continue
                if line.section_type == "data":
                    excel_cell = line.excel_cell
                    field_name = line.field_name or ""
                    if line.is_sum:
                        field_name += "@{sum}"
                    if line.merge_cell:
                        field_name += ":{%s}" % line.merge_cell
                    cell_dict = {excel_cell: field_name}
                    inst_dict[itype][prev_row].update(cell_dict)
                    continue
            rec.instruction = inst_dict


class ExcelTemplateDetail(models.Model):
    _name = "excel.template.detail"
    _order = 'sequence, id'

    template_id = fields.Many2one("excel.template", "Excel Template", index=True, ondelete="cascade", readonly=True)

    excel_cell = fields.Char("Cell")
    section_type = fields.Selection([("head", "Head"), ("row", "Row"), ("data", "Data")], "Section Type", required=True)
    row_field = fields.Char("Row Field")
    field_name = fields.Char("Field Name")
    sequence = fields.Integer("Sequence", default=10)
    merge_cell = fields.Char("Merge Cell To (Excel cell)")
    is_sum = fields.Boolean("Sum", default=False)

    @api.constrains('section_type')
    def check_section_type(self):
        for line in self:
            if line.section_type == 'head' and line.row_field != '_HEAD_':
                raise UserError('Header section name must be _HEAD_ not %s' % line.row_field)

    @api.constrains('excel_cell')
    def check_excel_cell(self):
        for line in self:
            if line.excel_cell and line.section_type != 'data':
                raise UserError('Section "Head" or "Row" cannot contain excel_cell: %s' % line.excel_cell)
            else:
                if not line.excel_cell and line.section_type == 'data':
                    raise UserError('Missing excel cell for Section "data"')
            if self.search_count([('template_id', '=', line.template_id.id), ('excel_cell', '=', line.excel_cell),
                                  ('section_type', '=', 'data')]) > 1:
                raise UserError('Duplicate Excel Cell')

    @api.constrains('merge_cell')
    def check_merge_cell(self):
        for line in self:
            if line.merge_cell and line.section_type != 'data':
                raise UserError('Section "Head" or "Row" cannot contain merge_cell: %s' % line.merge_cell)
            if line.merge_cell:
                match = re.match(r"([a-z]+)([0-9]+)", line.merge_cell, re.I)
                if not match:
                    raise UserError('Position %s is not valid. Use column in excel' % line.merge_cell)
