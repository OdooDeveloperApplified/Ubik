{
    'name': 'Ubik Sales',
    'version': '18.0.1.0',
    'author': 'Applified',
    'website': 'https://www.applified.in',
    'summary': 'Ubik By Applified',
    'depends': ['base','hr','sale','stock','sale_stock','contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_move_wizard_view.xml',
        'views/sales_template_views.xml',
        'views/free_scheme_wizard.xml',

    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
