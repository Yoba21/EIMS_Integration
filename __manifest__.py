{
    'name': 'EIMS Integration',
    'version': '1.0',
    'summary': 'Integrate Odoo with Ethiopia EIMS for e-invoicing',
    'depends': ['base', 'account'],
    'author': 'Your Name or Company',
    'category': 'Accounting',
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'data/ir_model_data.xml',
        'views/views.xml',
    ],
}