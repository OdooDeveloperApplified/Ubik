{
    'name': 'Ubik Inventory',
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
        'data/data.xml',
        'views/stock_picking_views.xml',
        'views/inspection_report_views.xml',
        

    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
}
