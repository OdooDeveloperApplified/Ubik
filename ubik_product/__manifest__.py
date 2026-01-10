{
    'name': 'Ubik Product',
    'version': '18.0.1.0',
    'author': 'Applified',
    'website': 'https://www.applified.in',
    'summary': 'Ubik By Applified',
    'depends': [
        'base',
        'hr',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/group_name_views.xml',
        'views/parameter_master_views.xml',
        'views/product_template_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
