# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
import base64
import os
from datetime import datetime, date
from docxtpl import DocxTemplate
from odoo.addons.lk_base.models import general_function as gf


class SampleKanban(models.Model):
    _name = 'sample.kanban'
    _rec_name = 'title'

    user_id = fields.Many2one('res.users', 'User', required=1)
    category_ids = fields.Many2many('sample.kanban.category', 'kanban_category_ref', 'kanban_id', 'category_id',
                                    'Category')

    from_date = fields.Date('From Date', required=1)
    to_date = fields.Date('To Date', required=1)
    no_user = fields.Integer('No User', readonly=True)
    no_like = fields.Integer('No Like', readonly=True)
    no_answer = fields.Integer('No Answer', readonly=True)
    title = fields.Char('Title', required=1)
    author = fields.Char('Author', required=1)
    no_view = fields.Integer('No View', readonly=True)
    is_feature = fields.Boolean('Featured', default=False)
    image = fields.Image("Image", max_width=1920, max_height=1920)
    image_128 = fields.Image("Image 128", related="image", max_width=128, max_height=128, store=True)
    state = fields.Selection([('new', 'New'), ('request', 'To be Approved'), ('publish', 'Approved'),
                              ('reject', 'Rejected')], 'State', default='new', group_expand='_expand_states')
    color = fields.Integer('Color Index', default=0, help='Used to decorate kanban view')

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def send_request(self):
        pass

    def sign_now(self):
        pass

    @api.model
    def prepare_excel_data(self):
        self = self.sudo()
        report_obj = self.env['sample.kanban']
        template_obj = self.env['excel.template']
        detail_data = []
        row_data = [
            {'excel_cell': "A11", 'value': '1'},
            {'excel_cell': "B11", 'value': 'Lê Huy Trường Giang'},
            {'excel_cell': "C11", 'value': ''},
            {'excel_cell': "D11", 'value': 'Maritime Bank'},
            {'excel_cell': "E11", 'value': 10000000},
            {'excel_cell': "F11", 'value': ''},
            {'excel_cell': "A12", 'value': '2'},
            {'excel_cell': "B12", 'value': 'Cao Thanh Thi'},
            {'excel_cell': "C12", 'value': ''},
            {'excel_cell': "D12", 'value': 'Maritime Bank'},
            {'excel_cell': "E12", 'value': 9000000},
            {'excel_cell': "F12", 'value': ''},
            {'excel_cell': "A13", 'value': '3'},
            {'excel_cell': "B13", 'value': 'Ngô Hoài Hận'},
            {'excel_cell': "C13", 'value': ''},
            {'excel_cell': "D13", 'value': 'Maritime Bank'},
            {'excel_cell': "E13", 'value': 8000000},
            {'excel_cell': "F13", 'value': ''},
            {'excel_cell': "A14", 'value': '4'},
            {'excel_cell': "B14", 'value': 'Phùng Gia Hạo'},
            {'excel_cell': "C14", 'value': ''},
            {'excel_cell': "D14", 'value': 'Maritime Bank'},
            {'excel_cell': "E14", 'value': 6000000},
            {'excel_cell': "F14", 'value': ''},
            {'excel_cell': "A15", 'value': '5'},
            {'excel_cell': "B15", 'value': 'Cao Cẩm Tú'},
            {'excel_cell': "C15", 'value': ''},
            {'excel_cell': "D15", 'value': 'Maritime Bank'},
            {'excel_cell': "E15", 'value': 5000000},
            {'excel_cell': "F15", 'value': ''},
        ]
        start_row = 16
        header_data = [
            {'excel_cell': "A2", "merge_cell": "F2", 'value': 'DANH SÁCH CHI HỘ LƯƠNG VÀ THƯỞNG THÁNG %s' %
                                                              datetime.now().strftime("%m")},
            {'excel_cell': "A7", "merge_cell": "F7", 'value': 'Chi hộ lương và thưởng tháng %s '
                                                              'cho NV theo danh sách cụ thể như sau :' %
                                                              datetime.now().strftime("%m")},
            {'excel_cell': "A%s" % start_row, 'value': '', "border": {"bottom": {"style": "thin"}}},
            {'excel_cell': "B%s" % start_row, 'value': '', "border": {"bottom": {"style": "thin"}}},
            {'excel_cell': "C%s" % start_row, 'value': '', "border": {"bottom": {"style": "thin"}}},
            {'excel_cell': "D%s" % start_row, 'value': '', "border": {"bottom": {"style": "thin"}}},
            {'excel_cell': "A%s" % start_row, "merge_cell": "D%s" % start_row, 'value': 'TỔNG CỘNG: ',
             'font': {'bold': True}, 'alignment': {'horizontal': 'center'}, 'copy_format': "A6",
             "border": {"top": {"style": "thin"}, "right": {"style": "thin"}, "bottom": {"style": "thin"},
                        "left": {"style": "thin"}}},
            {'excel_cell': "E%s" % start_row, 'value': "{:,.0f}".format(abs(380000000)), 'copy_format': "A10"},
            {'excel_cell': "F%s" % start_row, 'value': "", 'copy_format': "A10", 'font': {'bold': False}},
            {'excel_cell': "A%s" % (start_row + 1), 'value': 'Bằng chữ: %s' % gf.currency2text(abs(380000000)),
             'font': {'italic': True}},
        ]
        detail_data.append({'header': header_data, 'row': row_data})
        data = {
            'file_name': 'MẪU DS CHI HỘ LƯƠNG.xlsx',
            'report_name': 'MẪU DS CHI HỘ LƯƠNG',
            'template_name': 'export_payslip',
            'res_model': "report.out",
            'report_model': 'report.out',
            'per_sheet': False,
            'detail_data': [],
            'manual_data': detail_data,
        }
        return template_obj.export_excel(False, data, 'report.out', 'lk_base')

    def export_excel(self):
        data = self.prepare_excel_data()
        # return excel file when using python, if in js use get_file function instead
        return {
            'type': 'ir.actions.act_url',
            'name': 'doanhthu',
            'url': '/web/content/%s/%s/file_name/%s?download=true' % (data[0], data[1], data[2]),
        }

    def export_word(self):
        """
        - Create word template
        - In word template, add some variable with {}
        """
        for line in self:
            name_file = "Phiếu Chi" + " " + str(line.author)
            template_name = "PCNV.docx"

            directory_path = os.path.dirname(os.path.join(os.path.dirname(__file__), "..", ".."))
            doc = DocxTemplate("%s/report/%s" % (directory_path, template_name))
            money_text = gf.currency2text(abs(1000000000))
            context = {
                "employee_name": line.author.upper(),
                "id_card_location": "Cần Thờ",
                "date": date.today().day,
                "note": "",
                "money_text": money_text,
                "month": date.today().month,
                "year": date.today().year,
                "money": "{:,.0f}".format(abs(1000000000)),
            }
            new_context = {k: v if v else '' for k, v in context.items()}
            doc.render(new_context)
            doc.save(template_name)
            fp = open(template_name, "rb")
            out = base64.encodebytes(fp.read())
            attach_vals = {
                'report_data': name_file,
                'file_name': out,
            }
            act_id = self.env['report.out'].create(attach_vals)
            fp.close()
            # return excel file when using python, if in js use get_file function instead
            return {
                'type': 'ir.actions.act_url',
                'name': 'report',
                'url': '/web/content/report.out/%s/file_name/%s?download=true' % (act_id.id, act_id.report_data),
            }

    @api.model
    def get_dashboard_data(self):
        return {
            'earning_value': '$40,000',
            'request_value': '20',
            'sale_value': '$100,000',
            'user_value': '23',
            'line_chart_label': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'line_chart1_label': 'Target',
            'line_chart1_value': [10000, 20000, 15000, 18000, 12000, 18000],
            'line_chart1_color': '#a6b9ef',
            'line_chart2_label': 'Actual',
            'line_chart2_value': [12000, 18000, 15000, 20000, 12000, 15000],
            'line_chart2_color': '#28a745',
            'line_chart_max': 25000,
            'doughnut_label': ['Evaluate', 'Report'],
            'doughnut_value': [44, 56],
            'doughnut_color': ['#24bcfe', '#f5803f'],
            'bar_chart_label': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
            'bar_chart_value': [8000, 14000, 1100, 5500, 7500],
            'bar_chart_color': ['rgba(255, 99, 132)', 'rgba(255, 159, 64)', 'rgba(255, 205, 86)',
                                'rgba(75, 192, 192)', 'rgba(153, 102, 255)'],
            'pie_chart_label': ["To Do", "Doing", "Done", "Error", "Finish"],
            'pie_chart_value': [3000, 4000, 1000, 500, 1500],
            'pie_chart_color': ['#ebbf80', '#4c73b3', '#e38634', '#f42828', '#dcdfe9'],
            'table_body': [{
                'name': 'Phân quyền lại các website BV, cập nhật module hỏi đáp chống spam',
                'customer': 'LIINK CO.,LTD',
                'project': 'HELPDESK',
                'date': '01/04/2022',
                'deadline': '01/04/2022',
                'employee': 'Ngô Hoài Hận',
                'state': 'Doing',
                'completion_date': '',
                'hour': '4',
            }, {
                'name': 'KSTD - Hỗ trợ khách hàng sử dụng phần mềm',
                'customer': 'Đại học Tây Đô',
                'project': 'HELPDESK',
                'date': '29/03/2022',
                'deadline': '01/04/2022',
                'employee': 'Cao Thanh Thi',
                'state': 'Done',
                'completion_date': '29/03/2022',
                'hour': '8',
            }, {
                'name': 'KSTD - Ẩn danh sách phiếu khảo sát môn học nếu như không có cuộc khảo sát',
                'customer': 'Đại học Tây Đô',
                'project': 'HELPDESK',
                'date': '29/03/2022',
                'deadline': '01/04/2022',
                'employee': 'Cao Thanh Thi',
                'state': 'Mới',
                'completion_date': '',
                'hour': '0',
            }, {
                'name': 'KSTD - Sinh viên không thể khảo sát',
                'customer': 'LIINK CO.,LTD',
                'project': 'HELPDESK',
                'date': '28/03/2022',
                'deadline': '28/03/2022',
                'employee': 'Cao Thanh Thi',
                'priority': 'Cao',
                'state': 'Doing',
                'completion_date': '',
                'hour': '2',
            }],
            'table_total_hour': 14,
        }


class SampleKanbanCategory(models.Model):
    _name = 'sample.kanban.category'

    name = fields.Char('Name', required=1)
    color = fields.Integer('Color Index', default=0, help='Used to decorate kanban view')
