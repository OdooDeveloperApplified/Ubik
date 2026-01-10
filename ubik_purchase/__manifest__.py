{
    'name': 'Ubik Purchase',
    'version': '18.0.1.0',
    'author': 'Applified',
    'website': 'https://www.applified.in',
    'summary': 'Ubik By Applified',
    'depends': [
        'base',
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_template_views.xml',
        'reports/po_report_views.xml',

    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
