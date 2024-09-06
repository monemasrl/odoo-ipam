###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class IpamOrganization(models.Model):
    _name = "ipam.organization"
    _description = "IPAM Organization"
    _rec_name = "complete_name"
    _parent_store = True
    _parent_name = "parent_id"

    _order = "complete_name ASC"

    name = fields.Char(
        string="Name",
        required=True,
        copy=False,
        readonly=False,
        index="trigram"
    )

    complete_name = fields.Char(
        'Complete Name', 
        compute='_compute_complete_name', 
        recursive=True, 
        store=True
    )

    description = fields.Text(string="Description")

    code = fields.Char(
        string="Code", 
        required=True,
        copy=False,
        readonly=False,
        index="trigram",
        default=lambda self: _("New"),
    )

    active = fields.Boolean(string="Active", default=True)

    parent_id = fields.Many2one(
        comodel_name="ipam.organization",
        string="Parent Organization",
        copy=False,
    )

    child_ids = fields.One2many(
        comodel_name="ipam.organization",
        inverse_name="parent_id",
        string="Child Organizations",
    )

    parent_path = fields.Char(
        string="Parent Path",
        index=True,
        unaccent=True,
        copy=False,
    )

    subnet_ids = fields.One2many(
        comodel_name="ipam.net",
        inverse_name="organization_id",
        string="Subnets",
    )

    subnet_count = fields.Integer(
        string="# Subnets",
        compute="_compute_subnet_count",
        help="Number of subnets in this organization",
        store=False,
    )

    def _compute_subnet_count(self):
        for record in self:
            _logger.debug("Compute subnet count for organization %s", record.name)
            read_group_res = self.env['ipam.net']._read_group(
                [('organization_id', 'child_of', record.id)], 
                ['organization_id'], 
                ['organization_id']
            )
            group_data = dict((data['organization_id'][0], data['organization_id_count']) for data in read_group_res)
            _logger.debug("group_data: %s", group_data)
            subnet_count = 0
            for sub_net_id in record.search([('id', 'child_of', record.id)]).ids:
                _logger.debug("sub_net_id: %s", sub_net_id)
                subnet_count += group_data.get(sub_net_id, 0)
            record.subnet_count = subnet_count

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            if record.parent_id:
                record.complete_name = '%s / %s' % (record.parent_id.complete_name, record.name)
            else:
                record.complete_name = record.name

    @api.constrains('parent_id')
    def _check_record_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive records.'))

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.name) for record in self]
        return super().name_get()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", _("New")) == _("New"):
                vals["code"] = self.env["ir.sequence"].next_by_code(
                    "ipam.organization_seq"
                ) or _("New")
        return super().create(vals_list)