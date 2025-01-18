###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import ipaddress

from odoo import api, fields, models, _


class IpamIp(models.Model):
    _name = "ipam.ip"
    _description = "IPAM IP"
    _rec_name = "name"

    _order = "name ASC"

    name = fields.Char(
        string="name",
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

    fqdn = fields.Char(string="DNS")
    note = fields.Text(string="Note")
    ip = fields.Char(string="IP", copy=False)

    network_address = fields.Char(related="net_id.network_address", copy=False)
    mask_bits = fields.Integer(related="net_id.mask_bits", copy=False)
    gateway = fields.Char(related="net_id.gateway", copy=False)
    netmask = fields.Char(related="net_id.netmask", copy=False)
    cidr = fields.Char(related="net_id.cidr", copy=False)

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.ip))
        return result

    @api.constrains("name", "network_address", "mask_bits")
    def _check_ip(self):
        for record in self:
            if record.ip:
                try:
                    ipaddress.ip_address(record.ip)
                except ValueError:
                    raise ValueError(_("Invalid IP address"))
                if not (record.network_address and record.mask_bits):
                    # Skip network check if network is not set
                    continue
                if not ipaddress.ip_address(record.ip) in ipaddress.ip_network(
                    f"{record.network_address}/{record.mask_bits}"
                ):
                    raise ValueError(_(
                        ("IP address %s not in network %s\n"
                         "Network Name: %s\n"
                         "IP Name: %s\n"
                         "FQDN: %s\n"
                         "CIDR: %s\n"
                         )) % (
                                record.ip, 
                                f"{record.network_address}/{record.mask_bits}", 
                                record.net_id.name, 
                                record.name,
                                record.fqdn,
                                record.cidr
                            )
                        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ipam.ip_seq"
                ) or _("New")
        return super().create(vals_list)