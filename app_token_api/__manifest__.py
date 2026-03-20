{
    'name': 'App Token API',
    'version': '18.0',
    'summary': 'API to create and delete res.users',
    'category': 'Tools',
    'author': 'Applified',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/api_access_token.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}