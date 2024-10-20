{
    "name": "Odoo IPAM",
    "summary": """
        Odoo IPAM Module""",
    "description": """
        Odoo IPAM Module
    """,
    "author": "Monema S.r.l.",
    "website": "https://monema.it/",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "projects",
    "version": "16.0.0.0.1",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "operating_unit",
        "base_automation",
        "report_xlsx_helper",
        "report_xlsx",
        "web_field_numeric_formatting",
        "web_remember_tree_column_width",
        # "firstname"
        # web_responsive
        # calssi ctheeme
        # "semver"
    ],
    # always loaded
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/sequence2.xml",
        "views/organization_views.xml",
        "views/nic_views.xml",
        "views/net_views.xml",
        "views/nat_views.xml",
        "views/menu.xml",
    ],
    "application": True,
}
