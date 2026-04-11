{
    'name': 'Ubik Purchase Vendor Bills',
    'version': '18.0.1.0',
    'category': '',
    'author': 'Applified contacts',
    'website': 'https://www.ubik.com',
    'depends': ['base', 'mail','contacts','web','account'],
    'data': [
       
        'security/ir.model.access.csv',
        'views/vendor_bill_template_views.xml',
        
    ],
    
    'assets': {},
    'installable': True,
    'auto_install': False,
}