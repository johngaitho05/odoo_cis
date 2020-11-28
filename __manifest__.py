# -*- coding: utf-8 -*-
{
    'name': "Odoo CIS",

    'summary': """
         Connects Odoo to a VSDC""",

    'description': """
        A custom module that adds the RRA CIS specifications to Odoo
    """,

    'author': "Hyperthink Systems",
    'website': "http://www.hyperthinkkenya.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Hidden',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale', 'pos_reprint', 'sale', 'purchase', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/cis_assets.xml',
        'views/cis_templates_view.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml',
        'static/src/xml/reprint.xml',
    ],
    'auto_install': True,
}
