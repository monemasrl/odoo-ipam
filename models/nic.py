###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import ipaddress

from odoo import api, fields, models, _


class IpamNic(models.Model):
    _name = "ipam.nic"
    _description = "IPAM NIC"
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

    net_id = fields.Many2one(
        comodel_name="ipam.net",
        string="Network ID",
        required=True,
        ondelete="cascade",
    )

    ip = fields.Char(string="IP")
    fqdn = fields.Char(string="DNS")
    network_address = fields.Char(related="net_id.network_address", copy=False)
    mask_bits = fields.Integer(related="net_id.mask_bits", copy=False)
    gateway = fields.Char(related="net_id.gateway", copy=False)
    netmask = fields.Char(related="net_id.netmask", copy=False)
    cidr = fields.Char(related="net_id.cidr", copy=False)

    note = fields.Text(string="Note")

    @api.constrains("ip", "network_address", "mask_bits")
    def _check_ip(self):
        for record in self:
            if record.ip:
                try:
                    ipaddress.ip_address(record.ip)
                except ValueError:
                    raise ValueError(_("Invalid IP address"))
                if not ipaddress.ip_address(record.ip) in ipaddress.ip_network(
                    f"{record.network_address}/{record.mask_bits}"
                ):
                    raise ValueError(_("IP address not in network"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ipam.nic_seq"
                ) or _("New")
        return super().create(vals_list)