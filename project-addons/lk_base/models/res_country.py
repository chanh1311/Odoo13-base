# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.addons.base.models.res_country import location_name_search


def generate_code(string, index):
    words = string.split()
    letters = []
    for word in words:
        if word.isdigit():
            letters.append(word)
        else:
            if len(word) - 1 >= index:
                letters.append(word[index])
            else:
                letters.append(word[-1])
    return "".join(letters)


def generate_state_code(model, state_name, parent_name):
    res = ''
    index = 0
    while model.search([('code', '=', res)]) or not res:
        main_name = generate_code(parent_name, index)
        sub_name = generate_code(state_name, index)
        res = main_name + "-" + sub_name
        index += 1
    return res


class CountryState(models.Model):
    _inherit = 'res.country.state'

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{}".format(record.name)))
        return result


class CountryStateDistrict(models.Model):
    _name = 'res.country.state.district'

    @api.model
    def _default_state_id(self):
        country = self.env['res.country'].search([('code', '=', 'VN')], limit=1)
        return self.env['res.country.state'].search([('country_id', '=', country.id)], limit=1)

    @api.model
    def _state_id_domain(self):
        country = self.env['res.country'].search([('code', '=', 'VN')], limit=1)
        return [('country_id', '=', country.id)]

    state_id = fields.Many2one('res.country.state', 'State', required=True, default=_default_state_id,
                               domain=_state_id_domain)
    commune_ids = fields.One2many('res.country.state.commune', "district_id", "Commune")

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)

    name_search = location_name_search

    _sql_constraints = [
        ('code_uniq', 'unique(state_id, code)', 'Duplicate district code in same state!')
    ]

    def unlink(self):
        for line in self:
            if self.env['res.country.state.commune'].search([('district_id', '=', line.id)], limit=1):
                raise UserError("Không thể xóa dữ liệu do có Xã/phường/tt thuộc Huyện này.")
        return super(CountryStateDistrict, self).unlink()


class CountryStateCommune(models.Model):
    _name = 'res.country.state.commune'

    district_id = fields.Many2one('res.country.state.district', 'District', required=True)

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)

    name_search = location_name_search

    _sql_constraints = [
        ('code_uniq', 'unique(district_id, code)', 'Duplicate commune code in same district!')
    ]

    def unlink(self):
        for line in self:
            if self.env['res.country.state.hamlet'].search([('commune_id', '=', line.id)], limit=1):
                raise UserError("Không thể xóa dữ liệu do có Khóm/ấp thuộc Xã/phường/tt này.")
        return super(CountryStateCommune, self).unlink()


class CountryStateHamlet(models.Model):
    _name = 'res.country.state.hamlet'

    commune_id = fields.Many2one('res.country.state.commune', 'Commune', required=True)
    district_id = fields.Many2one('res.country.state.district', 'District', related='commune_id.district_id', store=True)

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)

    name_search = location_name_search

    _sql_constraints = [
        ('code_uniq', 'unique(commune_id, code)', 'Duplicate hamlet code in same commune!')
    ]
