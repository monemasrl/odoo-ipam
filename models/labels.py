###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, _

class IpamLabel(models.Model):
    _name = "ipam.label"
    _description = "IPAM Label"
    _rec_name = "name"
    _order = "name ASC"

    name = fields.Char(
        string="Name",
        required=True,
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: _("New"),
    )
    active = fields.Boolean(string="Active", default=True)
    color = fields.Char(string="Color", default="#FFFFFF")

    network_ids = fields.Many2many(
        comodel_name="ipam.net",
        string="Networks",
        help="Networks associated with this label",
    )