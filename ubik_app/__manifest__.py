{
    'name': 'Ubik Application',
    'version': '18.0.1.0',
    'category': '',
    'author': 'Applified contacts',
    'website': 'https://www.ubik.com',
    'depends': ['base', 'mail','contacts','web','sale','stock'],
    'data': [
       
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/sequence.xml',
        'wizard/asm_reject_wizard.xml',
       
        'views/mr_doctor_views.xml',
        'wizard/bulk_lock_unlock_wizard.xml',
        'views/doctorwise_sales_report.xml',
        'views/doctorwise_division_sales.xml',
        'views/yearwise_sales_comparison.xml',
        'views/final_sales_report.xml',
        # 'views/productwise_yearly_comparison.xml',
        'views/target_achievement.xml',
        
        
    ],
    
    'assets': {
        'web.assets_backend': [
            'ubik_app/static/src/js/mr_doctor_readonly.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}