{
    'name': 'Ubik Invoice',
    'version': '18.0.1.0',
    'author': 'Applified',
    'website': 'https://www.applified.in',
    'summary': 'Ubik By Applified',
    'depends': ['base','sale','stock','sale_stock','contacts','account'],
    'data': [
        'security/ir.model.access.csv',
        'views/invoice_template_views.xml',
        'reports/packaging_invoice_report_views.xml',
        'reports/invoice_report_views.xml',

    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
