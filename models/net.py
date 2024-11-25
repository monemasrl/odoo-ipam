###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import ipaddress

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from pprint import pformat

import logging

_logger = logging.getLogger(__name__)

class IpamNet(models.Model):
    _name = "ipam.net"
    _description = "IPAM Network"
    _rec_name = "complete_name"
    _parent_store = True
    _parent_name = "parent_id"

    _order = "complete_name ASC"

    name = fields.Char(
        string="Name",
        required=True,
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: _("New")
    )

    complete_name = fields.Char(
        'Complete Name', 
        compute='_compute_complete_name', 
        recursive=True, 
        store=True
    )

    active = fields.Boolean(string="Active", default=True)
    network_type = fields.Selection(
        selection=[
            ("range", "Range"),
            ("subnet", "Subnet"),
            ("pool", "Pool"),
        ],
        string="Network Type",
        required=True,
        default="subnet",
    )

    parent_id = fields.Many2one(
        comodel_name="ipam.net",
        string="Parent Network",
        copy=False,
    )
    child_ids = fields.One2many(
        comodel_name="ipam.net",
        inverse_name="parent_id",
        string="Child Networks",
    )
    parent_path = fields.Char(
        string="Parent Path",
        index=True,
        unaccent=True,
        copy=False,
    )

    parent_network_address = fields.Char(related="parent_id.network_address", copy=False)
    parent_mask_bits = fields.Integer(related="parent_id.mask_bits", copy=False)
    parent_gateway = fields.Char(related="parent_id.gateway", copy=False)
    parent_netmask = fields.Char(related="parent_id.netmask", copy=False)
    parent_cidr = fields.Char(related="parent_id.cidr", copy=False)

    network_address = fields.Char(string="Network Address", copy=False)
    mask_bits = fields.Integer(string="Mask Bits", copy=False)
    gateway = fields.Char(string="Gateway", copy=False)
    netmask = fields.Char(string="Netmask", compute="_compute_netmask")
    minIp = fields.Char(string="Min IP", compute="_compute_min_ip")
    maxIp = fields.Char(string="Max IP", compute="_compute_max_ip")
    numIp = fields.Integer(string="Number of IPs", compute="_compute_num_ip")
    cidr = fields.Char(string="CIDR", compute="_compute_cidr")

    organization_id = fields.Many2one(
        comodel_name="ipam.organization",
        string="Organization",
        copy=False,
    )

    vlan_id = fields.Integer(string="VLAN ID", copy=False)

    free_ip_count = fields.Integer( 
        string="Free IP Count",
        compute="_compute_free_ip_count"
    )

    available_ip_count = fields.Integer(
        string="Available IP Count",
        compute="_compute_free_ip_count"
    )

    used_ip_count = fields.Integer(
        string="Used IP Count",
        compute="_compute_free_ip_count"
    )

    used_ip_percentage = fields.Float(
        string="Used IP Percentage",
        compute="_compute_free_ip_count"
    )

    def _compute_free_ip_count(self):
        read_group_res = self.env['ipam.ip']._read_group(
            [('net_id', 'child_of', self.ids)], 
            ['net_id'], 
            ['net_id']
        )
        group_data = dict((data['net_id'][0], data['net_id_count']) for data in read_group_res)
        for net in self:
            nic_count = 0
            if not net.network_address or not net.mask_bits:
                net.free_ip_count = False
                net.available_ip_count = False
                net.used_ip_count = False
                net.used_ip_percentage = False
                continue
            network = ipaddress.IPv4Network(
                f"{net.network_address}/{net.mask_bits}"
            )
            net.available_ip_count = network.num_addresses
            free_ip_count = network.num_addresses

            # Conta il numero di subnet figlie di tipo vlan
            subnets_count = len(self.env['ipam.net'].search([
                ('parent_id', 'child_of', net.id),
                ('network_type', '=', 'subnet')
            ]))

            free_ip_count -= subnets_count * 2

            for sub_net_id in net.search([('id', 'child_of', net.id)]).ids:
                nic_count += group_data.get(sub_net_id, 0)

            free_ip_count -= nic_count

            net.free_ip_count = free_ip_count
            net.used_ip_count = net.available_ip_count - net.free_ip_count
            net.used_ip_percentage = net.used_ip_count / net.available_ip_count * 100

    nic_count = fields.Integer(
        '# NICs', compute='_compute_nic_count',
        help="The number of NICs under this network (Does not consider the children networks)")
    note = fields.Text(string="Note")

    attached_nic_count = fields.Integer(
        string="Attached NIC Count",
        compute="_compute_attached_nic_count"
    )

    nic_ids = fields.One2many(
        comodel_name="ipam.ip",
        inverse_name="net_id",
        string="NICs",
    )

    def _compute_nic_count(self):
        read_group_res = self.env['ipam.ip']._read_group(
            [('net_id', 'child_of', self.ids)], 
            ['net_id'], 
            ['net_id']
        )
        group_data = dict((data['net_id'][0], data['net_id_count']) for data in read_group_res)
        for net in self:
            nic_count = 0
            for sub_net_id in net.search([('id', 'child_of', net.ids)]).ids:
                nic_count += group_data.get(sub_net_id, 0)
            net.nic_count = nic_count

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for network in self:
            if network.parent_id:
                network.complete_name = '%s / %s' % (network.parent_id.complete_name, network.name)
            else:
                network.complete_name = network.name

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive networks.'))
        if self.parent_id and self.network_address and self.mask_bits and self.parent_id.network_address and self.parent_id.mask_bits:
            parent_network = ipaddress.ip_network(
                f"{self.parent_id.network_address}/{self.parent_id.mask_bits}"
            )
            network = ipaddress.ip_network(
                f"{self.network_address}/{self.mask_bits}"
            )
            if not network.subnet_of(parent_network):
                raise ValidationError(_("Network not in parent network"))
            
    @api.constrains("gateway", "network_address", "mask_bits")
    def _check_ip(self):
        for record in self:
            if record.parent_id and record.parent_id.network_address and record.parent_id.mask_bits and record.network_address and record.mask_bits:
                parent_network = ipaddress.ip_network(
                    f"{record.parent_id.network_address}/{record.parent_id.mask_bits}"
                )
                network = ipaddress.ip_network(
                    f"{record.network_address}/{record.mask_bits}"
                )
                if not network.subnet_of(parent_network):
                    raise ValidationError(_("Network not in parent network"))
            if record.gateway:
                try:
                    ipaddress.ip_address(record.gateway)
                except ValueError:
                    raise ValueError(_("Invalid IP address for gateway"))
                if not ipaddress.ip_address(record.gateway) in ipaddress.ip_network(
                    f"{record.network_address}/{record.mask_bits}"
                ):
                    raise ValidationError(_("IP address of gateway not in network"))


    @api.depends("network_address", "mask_bits")
    def _compute_netmask(self):
        for record in self:
            if record.network_address and record.mask_bits:
                try:
                    network = ipaddress.IPv4Network(
                        f"{record.network_address}/{record.mask_bits}"
                    )
                    record.netmask = str(network.netmask)
                except:
                    record.netmask = False
            else:
                record.netmask = False

    @api.depends("network_address", "mask_bits")
    def _compute_min_ip(self):
        for record in self:
            if record.network_address and record.mask_bits:
                try:
                    network = ipaddress.IPv4Network(
                        f"{record.network_address}/{record.mask_bits}"
                    )
                    record.minIp = str(network.network_address + 2)
                except:
                    record.minIp = False
            else:
                record.minIp = False

    @api.depends("network_address", "mask_bits")
    def _compute_max_ip(self):
        for record in self:
            if record.network_address and record.mask_bits:
                try:
                    network = ipaddress.IPv4Network(
                        f"{record.network_address}/{record.mask_bits}"
                    )
                    record.maxIp = str(network.broadcast_address - 1)
                except:
                    record.maxIp = False
            else:
                record.maxIp = False

    @api.depends("network_address", "mask_bits")
    def _compute_num_ip(self):
        for record in self:
            if record.network_address and record.mask_bits:
                try:
                    network = ipaddress.IPv4Network(
                        f"{record.network_address}/{record.mask_bits}"
                    )
                    record.numIp = network.num_addresses - 2
                except:
                    record.numIp = False
            else:
                record.numIp = False

    @api.depends("network_address", "mask_bits")
    def _compute_cidr(self):
        for record in self:
            if record.network_address and record.mask_bits:
                try:
                    record.cidr = f"{record.network_address}/{record.mask_bits}"
                except:
                    record.cidr = False
            else:
                record.cidr = False

    def _compute_attached_nic_count(self):
        for record in self:
            nics = self.env['ipam.ip'].search([('net_id', '=', record.id)])
            record.attached_nic_count = len(nics)

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.name) for record in self]
        return super().name_get()
    
    def _check_create(self, vals):
        if vals.get("network_address") and vals.get("mask_bits"):
            try:
                ipaddress.IPv4Network(
                    f"{vals['network_address']}/{vals['mask_bits']}"
                )
                # If gateway is set, check if it is a valid IP address and if it is in the network
                if vals.get("gateway"):
                    try:
                        ipaddress.ip_address(vals["gateway"])
                    except ValueError:
                        raise ValueError(_("Invalid IP address for gateway"))
                    if not ipaddress.ip_address(vals["gateway"]) in ipaddress.ip_network(
                        f"{vals['network_address']}/{vals['mask_bits']}"
                    ):
                        raise ValueError(_("IP address of gateway not in network"))
                # If parent_id is set and has network_address and mask_bits, check if network_address is in the parent network
                if vals.get("parent_id"):
                    parent = self.browse(vals["parent_id"])
                    if parent.network_address and parent.mask_bits:
                        parent_network = ipaddress.ip_network(
                            f"{parent.network_address}/{parent.mask_bits}"
                        )
                        network = ipaddress.ip_network(
                            f"{vals['network_address']}/{vals['mask_bits']}"
                        )
                        if not network.subnet_of(parent_network):
                            raise ValueError(_("Network not in parent network"))

            except ValueError:
                raise ValueError(_("Invalid network address or mask bits"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_create(vals)

            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "ipam.network_seq"
                ) or _("New")
            # Check if network_address and mask_bits are set and if so, check if they are valid

        return super().create(vals_list)
