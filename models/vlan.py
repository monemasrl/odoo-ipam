###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import ipaddress

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class IpamVlan(models.Model):
    _name = "ipam.vlan"
    _description = "IPAM Network"
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
    vlan_id = fields.Integer(string="VLAN ID", required=True)
    description = fields.Text(string="Description")
    subnet_ids = fields.One2many(
        comodel_name="ipam.net",
        inverse_name="vlan_id",
        string="Subnets",
    )

    def name_get(self):
        return [(record.id, f"{record.name} (ID: {record.vlan_id})") for record in self]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ipam.vlan_seq"
                ) or _("New")
        return super().create(vals_list)