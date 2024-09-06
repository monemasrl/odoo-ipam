###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import ipaddress
import logging

from ipaddress import IPv4Network
from netaddr import IPNetwork, IPSet
import netaddr

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IpamNat(models.Model):
    _name = "ipam.nat"
    _description = "IPAM NAT"
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

    nat_type = fields.Selection(
        selection=[
            ("source", "Source"),
            ("destination", "Destination"),
        ],
        string="NAT Type",
        required=True,
        default="destination",
    )

    nat_subnet_id = fields.Many2one(
        comodel_name="ipam.net",
        string="NAT Network ID",
        required=True,
        ondelete="cascade",
    )

    # nat_ip = fields.Selection(
    #     selection=lambda self: self._get_available_nat_ips(),
    #     string="NAT IP",
    #     required=True,
    #     copy=False,
    #     readonly=False,
    #     index="trigram",
    # )
    nat_ip = fields.Char(
        string="NAT IP")

    dst_subnet_id = fields.Many2one(
        comodel_name="ipam.net",
        string="Destination Network ID",
        required=True,
        ondelete="cascade",
    )

    dst_ip = fields.Char(
        string="Destination IP",
        required=True,
        copy=False,
        readonly=False,
        index="trigram",
    )

    @api.constrains("nat_ip")
    def _check_nat_ip(self):
        for record in self:
            try:
                ipaddress.ip_address(record.nat_ip)
                # Check if NAT IP is in the NAT subnet
                if ipaddress.ip_address(record.nat_ip) not in ipaddress.ip_network(record.nat_subnet_id.cidr):
                    raise UserError(_("NAT IP is not in the NAT subnet"))
            except ValueError:
                raise UserError(_("Invalid Source IP address"))
            
    @api.constrains("dst_ip")
    def _check_dst_ip(self):
        for record in self:
            try:
                ipaddress.ip_address(record.dst_ip)
                # Check if Destination IP is in the Destination subnet
                if ipaddress.ip_address(record.dst_ip) not in ipaddress.ip_network(record.dst_subnet_id.cidr):
                    raise UserError(_("Destination IP is not in the Destination subnet"))
            except ValueError:
                raise UserError(_("Invalid Destination IP address"))

    @api.model
    def get_available_nat_ips(self):
        depending_on = self.env.context.get('depending_on')
        _logger.debug(f"#################  Getting available NAT IPs ################# depending_on: {depending_on}")

        if depending_on:
            nat_subnet_id = self.env["ipam.net"].browse(depending_on)
            supernet = IPNetwork(nat_subnet_id.cidr)
            net1 = IPNetwork('192.168.1.0/26')
            net2 = IPNetwork('192.168.1.128/27')

            free_ips = IPSet([supernet]) - IPSet([net1, net2])
            ips = []
            for net in free_ips.iter_cidrs():
                for ip_address in net.iter_hosts():
                    ips.append((ip_address, ip_address))
            return ips
        return []

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.nat_ip} ({record.nat_subnet_id.name})"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, values):
        if values.get("name", _("New")) == _("New"):
            values["name"] = self.env["ir.sequence"].next_by_code("ipam.nat_seq") or _("New")
        return super(IpamNat, self).create(values)