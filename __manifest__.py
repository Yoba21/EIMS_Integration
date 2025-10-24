{
    'name': 'EIMS Integration',
    'version': '1.0',
    'summary': 'Integrate Odoo with Ethiopia EIMS for e-invoicing',
    'depends': ['base', 'account'],
    'author': 'Eyob Zelalem',
    'category': 'Accounting',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_model_data.xml',
        'data/ir_cron_data.xml',
        
        
        'views/views.xml',
        'views/eims_master_views.xml',
        'views/eims_certificate_views.xml',
        'views/eims_log_views.xml',
        'views/eims_menus.xml',
        'views/eims_settings_views.xml',
        'views/eims_configuration_wizard_views.xml',
        'views/report_invoice_document_eims.xml',
        # 'views/report_invoice_document_eims_enhanced.xml',
    ],
    'images': ['static/description/icon.png'],
    'external_dependencies': {
        'python': ['qrcode', 'cryptography', 'Pillow'],
    },
}