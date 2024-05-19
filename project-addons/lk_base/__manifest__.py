# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'LK base',
    'sequence': 121,
    'category': 'Tools',
    'description': """
Base module for all Lk module.
========================================
""",
    'depends': ['mail_bot', 'web', 'l10n_vn', 'resource', 'auth_password_policy_signup', 'base_geolocalize', 'restful', 'web_domain_field', 'intl_tel_widget'],
    'data': [
        'data/data.xml',
        'data/sample_data.xml',
        'data/res.lang.csv',
        'security/ir.model.access.csv',
        'security/lk_base_security.xml',
        'views/excel_template_views.xml',
        'views/dynamic_import_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/res_country_views.xml',
        'views/res_group_views.xml',
        'views/session_views.xml',
        'views/backup_database_views.xml',
        'views/notification_views.xml',
        'views/system_log_views.xml',
        'views/web_custom_views.xml',
        'views/web_custom_templates.xml',
        'views/sample_kanban_views.xml',
        'views/sample_other_views.xml',
        'views/sample_board_views.xml',
        'views/sample_report_views.xml',
        'views/menu_views.xml',
    ],
    'external_dependencies': {
        'python': ['zxcvbn==4.4.28', 'cryptography==3.2.1', 'paramiko==2.7.2', 'openpyxl==3.0.7', 'onesignal_sdk==2.0.0', 'docxtpl==0.15.2', 'docx==0.2.4', 'docxcompose==1.3.4'],
    },
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application': False,
}