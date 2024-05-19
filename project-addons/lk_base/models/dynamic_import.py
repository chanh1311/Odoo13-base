# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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


class DynamicImport(models.Model):
    _name = 'dynamic.import'
    _description = 'Dynamic Import'

    model_id = fields.Many2one('ir.model', 'Model', required=1)
    sub_model_id = fields.Many2one('ir.model', 'Sub Model')
    line_ids = fields.One2many('dynamic.import.line', 'import_id', 'Import Line')
    sub_model_ids = fields.One2many('dynamic.import.sub.model', 'import_id', 'Import Sub Model')

    name = fields.Char('Name', required=1)
    template = fields.Binary('Template', required=1)
    template_name = fields.Char('Template Name')
    is_update = fields.Boolean('Update record?')
    sub_field_name = fields.Char('Sub Field Relation', compute='compute_sub_field_name', store=1)

    @api.model
    def get_import_list(self, model_name):
        res = {}
        model = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
        if model:
            import_list = self.search([('model_id', '=', model.id)])
            res = {
                'import_len': len(import_list),
                'name_lst': [{"name": rec.name, "id": rec.id} for rec in import_list]
            }
        return res

    @api.onchange('model_id')
    def change_model(self):
        if self.model_id:
            self.line_ids = False

    @api.onchange('sub_model_id')
    def change_sub_model(self):
        if self.sub_model_id:
            self.sub_model_ids = False

    @api.constrains('sub_model_id', 'sub_model_ids')
    def check_sub_model(self):
        for line in self:
            if not line.sub_model_id and len(line.sub_model_ids) > 0:
                raise UserError('Missing relation for Sub Model')

    @api.constrains('sub_model_id', 'sub_field_name')
    def check_field_relation(self):
        for line in self:
            if line.sub_model_id and not line.sub_field_name:
                raise UserError('Missing relation between Model and Sub Model')

    @api.depends('model_id', 'sub_model_id')
    def compute_sub_field_name(self):
        for line in self:
            relation_field = self.env['ir.model.fields'].search_read([
                ('ttype', '=', 'one2many'), ('model', '=', line.model_id.model),
                ('relation', '=', line.sub_model_id.model)], ['name'], limit=1)
            line.sub_field_name = relation_field[0]['name'] if relation_field else False

    @api.model
    def create(self, vals):
        if 'is_update' in vals and vals.get('is_update'):
            raise UserError('Function update record will coming soon')
        return super(DynamicImport, self).create(vals)

    @api.model
    def execute_import(self, import_id):
        new_import = self.env['dynamic.import.execute'].create({'import_id': import_id})
        return {
            'name': new_import.import_id.name,
            'res_id': new_import.id,
        }


class DynamicImportLine(models.Model):
    _name = 'dynamic.import.line'
    _description = 'Dynamic Import Line'
    _order = 'sequence, id'

    import_id = fields.Many2one('dynamic.import', 'Dynamic Import')
    field_id = fields.Many2one('ir.model.fields', 'Field Name', required=1,
                               domain="[('model_id', '=', model_id), ('related', '=', False), ('compute', '=', False),"
                                      "('ttype', 'not in', ('one2many', 'many2many', 'many2one_reference', 'reference'))]")
    model_id = fields.Many2one('ir.model', 'Model')

    sequence = fields.Integer('Sequence')
    field_type = fields.Selection('Field Type', related='field_id.ttype', readonly=1)
    is_required = fields.Boolean('Is Required?')

    @api.constrains('is_required')
    def check_required(self):
        for line in self:
            if not line.is_required and line.field_id.required:
                raise UserError('Field {} must be required'.format(line.field_id.name))

    @api.onchange('field_id')
    def change_required(self):
        if self.field_id:
            self.is_required = self.field_id.required


class DynamicImportSubModel(models.Model):
    _name = 'dynamic.import.sub.model'
    _description = 'Dynamic Import Sub Model'
    _order = 'sequence, id'

    import_id = fields.Many2one('dynamic.import', 'Dynamic Import')
    model_id = fields.Many2one('ir.model', 'Model')
    field_id = fields.Many2one('ir.model.fields', 'Field Name', required=1,
                               domain="[('model_id', '=', model_id), ('related', '=', False), ('compute', '=', False),"
                                      "('ttype', 'not in', ('one2many', 'many2many', 'many2one_reference', 'reference'))]")

    sequence = fields.Integer('Sequence')
    field_type = fields.Selection('Field Type', related='field_id.ttype', readonly=1)
    is_required = fields.Boolean('Is Required?')

    @api.onchange('field_id')
    def change_required(self):
        if self.field_id:
            self.is_required = self.field_id.required

    @api.constrains('is_required')
    def check_required(self):
        for line in self:
            if not line.is_required and line.field_id.required:
                raise UserError('Field {} must be required'.format(line.field_id.name))
