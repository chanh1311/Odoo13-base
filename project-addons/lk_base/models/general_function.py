# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import copy
from datetime import datetime, time, date
from dateutil.relativedelta import relativedelta
from num2words import num2words
from odoo import fields
from odoo.exceptions import UserError
from math import ceil
import calendar
import pytz
import os
from subprocess import Popen

# valid style for excel
# how to use: style = copy.deepcopy(excel_style), workbook.add_format(style['header']),
# if change option -> modify_excel_style
# available option: https://xlsxwriter.readthedocs.io/format.html#format
excel_style = {
    'title': {'bold': 1, 'font_name': 'Times New Roman', 'font_size': 15, 'align': 'center', 'valign': 'vcenter',
               'text_wrap': 1},
    'header': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
               'valign': 'vcenter', 'text_wrap': 1},
    'value_left': {'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left', 'valign': 'vcenter',
                   'text_wrap': 1},
    'value_left_bold': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left',
                        'valign': 'vcenter', 'text_wrap': 1},
    'value_left_italic': {'border': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left',
                          'valign': 'vcenter', 'text_wrap': 1},
    'value_left_underline': {'border': 1, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                             'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_italic': {'border': 1, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                               'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_underline': {'border': 1, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                  'font_size': 12, 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_italic_underline': {'border': 1, 'bold': 1, 'italic': 1, 'underline': 1,
                                         'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left',
                                         'valign': 'vcenter', 'text_wrap': 1},
    'value_left_no_border': {'border': 0, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left',
                             'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_no_border': {'border': 0, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                  'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_italic_no_border': {'border': 0, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                    'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_underline_no_border': {'border': 0, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                       'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_italic_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman',
                                         'font_size': 12, 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_underline_no_border': {'border': 0, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                            'font_size': 12, 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1},
    'value_left_bold_italic_underline_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'underline': 1,
                                                   'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left',
                                                   'valign': 'vcenter', 'text_wrap': 1},
    'value_center': {'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                     'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                          'valign': 'vcenter', 'text_wrap': 1},
    'value_center_italic': {'border': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                            'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_underline': {'border': 1, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                               'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_italic': {'border': 1, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_underline': {'border': 1, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                    'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_italic_underline': {'border': 1, 'bold': 1, 'italic': 1, 'underline': 1,
                                           'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                                           'valign': 'vcenter', 'text_wrap': 1},
    'value_center_no_border': {'border': 0, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                               'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_no_border': {'border': 0, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                    'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_italic_no_border': {'border': 0, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                      'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_underline_no_border': {'border': 0, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                         'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_italic_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman',
                                           'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_underline_no_border': {'border': 0, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                              'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1},
    'value_center_bold_italic_underline_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'underline': 1,
                                                     'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                                                     'valign': 'vcenter', 'text_wrap': 1},
    'value_right': {'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right', 'valign': 'vcenter',
                    'num_format': "#,###", 'text_wrap': 1},
    'value_right_bold': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right',
                         'valign': 'vcenter', 'num_format': "#,###", 'text_wrap': 1},
    'value_right_italic': {'border': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right',
                           'num_format': "#,###", 'valign': 'vcenter', 'text_wrap': 1},
    'value_right_underline': {'border': 1, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                              'num_format': "#,###", 'align': 'right', 'valign': 'vcenter', 'text_wrap': 1},
    'value_right_bold_italic': {'border': 1, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                'num_format': "#,###", 'align': 'right', 'valign': 'vcenter', 'text_wrap': 1},
    'value_right_bold_underline': {'border': 1, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                   'num_format': "#,###", 'font_size': 12, 'align': 'right', 'valign': 'vcenter',
                                   'text_wrap': 1},
    'value_right_bold_italic_underline': {'border': 1, 'bold': 1, 'italic': 1, 'underline': 1, 'num_format': "#,###",
                                          'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right',
                                          'valign': 'vcenter', 'text_wrap': 1},
    'value_right_no_border': {'border': 0, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right',
                              'valign': 'vcenter', 'num_format': "#,###", 'text_wrap': 1},
    'value_right_bold_no_border': {'border': 0, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                   'align': 'right', 'valign': 'vcenter', 'num_format': "#,###", 'text_wrap': 1},
    'value_right_italic_no_border': {'border': 0, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                     'num_format': "#,###", 'align': 'right', 'valign': 'vcenter', 'text_wrap': 1},
    'value_right_underline_no_border': {'border': 0, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                        'num_format': "#,###", 'align': 'right', 'valign': 'vcenter', 'text_wrap': 1},
    'value_right_bold_italic_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman',
                                          'num_format': "#,###", 'font_size': 12, 'align': 'right', 'valign': 'vcenter',
                                          'text_wrap': 1},
    'value_right_bold_underline_no_border': {'border': 0, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                             'num_format': "#,###", 'font_size': 12, 'align': 'right',
                                             'valign': 'vcenter', 'text_wrap': 1},
    'value_right_bold_italic_underline_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'underline': 1,
                                                    'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right',
                                                    'num_format': "#,###", 'valign': 'vcenter', 'text_wrap': 1},
    'value_date': {'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center', 'valign': 'vcenter',
                   'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_bold': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                        'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_italic': {'border': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                          'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_underline': {'border': 1, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                             'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_bold_italic': {'border': 1, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                               'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_bold_underline': {'border': 1, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                  'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY',
                                  'text_wrap': 1},
    'value_date_bold_italic_underline': {'border': 1, 'bold': 1, 'italic': 1, 'underline': 1,
                                         'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                                         'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_no_border': {'border': 0, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                             'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_bold_no_border': {'border': 0, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                  'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_italic_no_border': {'border': 0, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                    'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_underline_no_border': {'border': 0, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                       'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY',
                                       'text_wrap': 1},
    'value_date_bold_italic_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman',
                                         'font_size': 12, 'align': 'center', 'valign': 'vcenter',
                                         'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_bold_underline_no_border': {'border': 0, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                            'font_size': 12, 'align': 'center', 'valign': 'vcenter',
                                            'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_date_bold_italic_underline_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'underline': 1,
                                                   'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                                                   'valign': 'vcenter', 'num_format': 'DD/MM/YY', 'text_wrap': 1},
    'value_datetime': {'border': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                       'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_bold': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                            'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_italic': {'border': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                              'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss',
                              'text_wrap': 1},
    'value_datetime_underline': {'border': 1, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                 'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss',
                                 'text_wrap': 1},
    'value_datetime_bold_italic': {'border': 1, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                   'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss',
                                   'text_wrap': 1},
    'value_datetime_bold_underline': {'border': 1, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                      'font_size': 12, 'align': 'center', 'valign': 'vcenter',
                                      'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_bold_italic_underline': {'border': 1, 'bold': 1, 'italic': 1, 'underline': 1,
                                             'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                                             'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_no_border': {'border': 0, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                                 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_bold_no_border': {'border': 0, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                      'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss',
                                      'text_wrap': 1},
    'value_datetime_italic_no_border': {'border': 0, 'italic': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                        'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss',
                                        'text_wrap': 1},
    'value_datetime_underline_no_border': {'border': 0, 'underline': 1, 'font_name': 'Times New Roman', 'font_size': 12,
                                           'align': 'center', 'valign': 'vcenter', 'num_format': 'DD/MM/YY hh:mm:ss',
                                           'text_wrap': 1},
    'value_datetime_bold_italic_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'font_name': 'Times New Roman',
                                             'font_size': 12, 'align': 'center', 'valign': 'vcenter',
                                             'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_bold_underline_no_border': {'border': 0, 'bold': 1, 'underline': 1, 'font_name': 'Times New Roman',
                                                'font_size': 12, 'align': 'center', 'valign': 'vcenter',
                                                'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_datetime_bold_italic_underline_no_border': {'border': 0, 'bold': 1, 'italic': 1, 'underline': 1,
                                                       'font_name': 'Times New Roman', 'font_size': 12,
                                                       'align': 'center', 'valign': 'vcenter',
                                                       'num_format': 'DD/MM/YY hh:mm:ss', 'text_wrap': 1},
    'value_group_center': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center',
                           'font_color': '#FF0000', 'valign': 'vcenter', 'text_wrap': 1},
    'value_group_left': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left',
                         'num_format': "#,###", 'font_color': '#FF0000', 'valign': 'vcenter', 'text_wrap': 1},
    'value_group_right': {'border': 1, 'bold': 1, 'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right',
                          'num_format': "#,###", 'font_color': '#FF0000', 'valign': 'vcenter', 'text_wrap': 1},
}


denom = ('',
         u'nghìn', u'triệu', u'tỷ', u'nghìn tỷ', u'trăm nghìn tỷ',
         'Quintillion', 'Sextillion', 'Septillion', 'Octillion', 'Nonillion',
         'Decillion', 'Undecillion', 'Duodecillion', 'Tredecillion',
         'Quattuordecillion', 'Sexdecillion', 'Septendecillion',
         'Octodecillion', 'Novemdecillion', 'Vigintillion')


def modify_excel_style(base_style, modify_attr=None):
    base_style = copy.deepcopy(base_style)
    if modify_attr:
        for key, value in modify_attr.items():
            base_style[key] = value
    return base_style


# convert str to bool
def str2bool(value):
    return value.lower() not in ('0', 'false', 'off')


# return format data for excel
def get_valid_data(data, number_format=None, datetime_format=None):
    if data:
        if number_format:
            try:
                res = number_format.format(data)
            except:
                return str(data)
            return res
        elif datetime_format:
            try:
                res = data.strftime(datetime_format)
            except:
                return str(data)
            return res
        else:
            return data
    else:
        return ''


# set auto width for column excel
def set_autowidth(worksheet, len_lst, start_col=1, width=0):
    def colnum_string(n):
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

    c = start_col
    for x in range(1, len_lst + 1):
        worksheet.set_column('{0}:{0}'.format(colnum_string(c)), width)
        c += 1


# generate sequence name
def increase_name(x, number):
    return str(x).zfill(number)

# generate sequence name: model_name, prefix (Ex: <HS>00001), number_fill, reset_number, field (default is name)
def generate_name(self, model_name, prefix, number_fill=5, reset_number=None, field=None):
    name = str(prefix) + "%"
    field_search = field if field else 'name'
    last_name = self.env[model_name].search([(field_search, '=ilike', name)], order='id desc', limit=1)
    if reset_number:
        text = increase_name(reset_number, number_fill)
    else:
        try:
            new_number = int(last_name[field_search].replace(str(prefix), ""))
        except Exception:
            new_number = 0
        text = increase_name((new_number + 1) if last_name else 1, number_fill)
    res = str(prefix) + text
    return res


# format number with thousand separator
def format_number(self, number):
    try:
        int(number)
        lang_id = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
        return "{:,.0f}".format(number).replace(",", lang_id.thousands_sep)
    except Exception as e:
        return number


# customize num2words (from money to word)
def modify_num2words(number, word):
    if number > 1000000:
        for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
            if dval > number:
                mod = 1000 ** didx
                lval = number // mod
                r = number - (lval * mod)
                if 99 >= r / 1000 ** (didx - 1) > 10:
                    word = word.replace(denom[didx], denom[didx] + u" không trăm")
                elif 9 >= r / 1000 ** (didx - 1) > 0:
                    word = word.replace(denom[didx], denom[didx] + u" không trăm lẻ")
                if r > 0:
                    return modify_num2words(r, word)
                else:
                    return word
    return word


# convert number to text (vietnamese)
def currency2text(number, lang='vi_VN'):
    word = num2words(abs(number), lang=lang)
    res = modify_num2words(abs(number), word)
    minus = u"Âm " if number < 0 else ""
    return minus + res.capitalize() + u" đồng"


# use date_utils to get_month, start_of (week, year), date_range,...
# return datetime (without timezone) by user timezone
def get_datetime_wo_tz(value, granularity, duration=1, user_tz='UTC'):
    if not isinstance(value, datetime) and not isinstance(value, date):
        raise UserError('Function get_datetime_wo_tz only accepts datetime/date.')
    current_tz = datetime.now(pytz.timezone(user_tz))
    utc_offset = current_tz.utcoffset().total_seconds() / 60 / 60
    hour = int(utc_offset)
    minute = 0
    if not duration or duration < 0:
        duration = 1
    if isinstance(utc_offset, float):
        minute = int(float(str(utc_offset - int(utc_offset))[1:]) * 60)
    if granularity == 'day':
        if isinstance(value, datetime):
            start_time = value.replace(hour=0, minute=0, second=1, microsecond=100)
            if duration > 1:
                start_time = start_time - relativedelta(days=duration - 1)
            end_time = value.replace(hour=23, minute=59, second=59, microsecond=100)
        else:
            start_time = end_time = value
    elif granularity == 'week':
        start_time = value - relativedelta(days=calendar.weekday(value.year, value.month, value.day))
        if duration > 1:
            start_time = start_time - relativedelta(weeks=duration - 1)
        end_time = value + relativedelta(days=6-calendar.weekday(value.year, value.month, value.day))
    elif granularity == 'month':
        start_time = value.replace(day=1)
        if duration > 1:
            start_time = start_time - relativedelta(months=duration - 1)
        end_time = value + relativedelta(day=1, months=1, days=-1)
    elif granularity == 'year':
        start_time = value.replace(month=1, day=1)
        if duration > 1:
            start_time = start_time - relativedelta(years=duration - 1)
        end_time = value.replace(month=12, day=31)
    else:
        raise UserError('Function get_datetime_wo_tz only accepts granularity: day, week, month, year')
    if isinstance(value, datetime):
        return [start_time - relativedelta(hours=hour, minutes=minute),
                end_time - relativedelta(hours=hour, minutes=minute)]
    else:
        return [start_time, end_time]


# get datetime now with server timezone
def get_datetime_tz(self, value=None):
    if value:
        try:
            fields.Datetime.context_timestamp(self, value)
        except Exception as e:
            try:
                value = datetime.combine(value, time(0, 0))
            except Exception as e:
                raise UserError('Function get_datetime_tz only accepts datetime/date.')
        return fields.Datetime.context_timestamp(self, value)
    return fields.Datetime.context_timestamp(self, datetime.now())


# subtract datetime if use datetime.datetime, can use relativedelta instead
def get_timedelta(date1, date2, return_type='second'):
    if return_type == 'second':
        return (date1 - date2).total_seconds()
    elif return_type == 'minute':
        return (date1 - date2).total_seconds() / 60
    elif return_type == 'hour':
        return (date1 - date2).total_seconds() / 3600
    else:
        return 0


# get no_week of month
def no_week_of_month(datetime_value):
    try:
        datetime_value.strftime("%d/%m/%Y")
    except Exception as e:
        raise UserError('Value must be datetime.')
    year = int(datetime_value.strftime("%Y"))
    month = int(datetime_value.strftime("%m"))
    return calendar.Calendar().monthdatescalendar(year, month)


# determine week of month based on date
def get_week_of_month(datetime_value):
    try:
        datetime_value.strftime("%d/%m/%Y")
    except Exception as e:
        raise UserError('Value must be datetime.')
    first_day = datetime_value.replace(day=1)
    dom = datetime_value.day
    adjusted_dom = dom + first_day.weekday()
    return int(ceil(adjusted_dom/7.0))


# get timezone based on country
def get_tz_country(country):
    if len(pytz.country_timezones.get(country.code, [])) == 1:
        return pytz.country_timezones[country.code][0]
    return 'UTC'


# simple encrypt password
def encode(string, key='password'):
    encoded_chars = []
    for i in range(len(string)):
        key_c = key[i % len(key)]
        encoded_c = chr(ord(string[i]) + ord(key_c) % 128)
        encoded_chars.append(encoded_c)
    encoded_string = "".join(encoded_chars)
    arr2 = bytes(encoded_string, 'utf-8')
    return base64.urlsafe_b64encode(arr2)


# simple decrypt password
def decode(string, key='password'):
    encoded_chars = []
    string = base64.urlsafe_b64decode(string)
    string = string.decode('utf-8')
    for i in range(len(string)):
        key_c = key[i % len(key)]
        encoded_c = chr(ord(string[i]) - ord(key_c) % 128)
        encoded_chars.append(encoded_c)
    encoded_string = "".join(encoded_chars)
    return encoded_string


LIBRE_OFFICE = r"C:\Program Files\LibreOffice\program\swriter.exe"


def convert_report(directory_path, report_id, export_type='pdf', export_js=None):
    """
    Convert report extension to other extension
    @param directory_path: path to store new file
    @param report_id: ORM report.out record
    @param export_type: new extension
    @param export_js: return data for js export button
    @return: data for export button
    """
    out_folder = "%s/report/" % directory_path

    # create tmp file and convert to new extension
    stamp = datetime.utcnow().strftime("%H%M%S%f")[:-3]
    ftemp = "temp{}.{}".format(stamp, report_id.report_data.split('.')[-1])
    template_name = "{}{}".format(out_folder, ftemp)
    f = open(template_name, "wb")
    f.write(base64.decodebytes(report_id.file_name))
    f.close()
    p = Popen([LIBRE_OFFICE, '--headless', '--convert-to', export_type, '--outdir', out_folder, template_name])
    p.communicate()
    os.remove(template_name)

    # update new file to report.out
    template_name = template_name.replace(template_name.split('.')[-1], export_type)
    fp = open(template_name, "rb")
    out = base64.encodebytes(fp.read())
    fp.close()
    report_id.write({
        'report_data': '{}.{}'.format(report_id.report_data.split('.')[0], export_type),
        'file_name': out,
    })
    os.remove(template_name)

    if export_js:
        return ['report.out', report_id.id, report_id.report_data]
    else:
        return {
            'type': 'ir.actions.act_url',
            'name': 'report',
            'url': '/web/content/report.out/%s/file_name/%s' % (report_id.id, report_id.report_data),
        }
