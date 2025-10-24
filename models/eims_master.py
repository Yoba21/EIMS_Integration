# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class EimsMaster(models.Model):
    _name = 'eims.master'
    _description = 'EIMS Master Data'
    _order = 'type, code'
    _rec_name = 'display_name'
    
    name = fields.Char(
        string='Name',
        required=True,
        help='Descriptive name for this master data entry'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='EIMS code for this entry'
    )
    type = fields.Selection([
        ('uom', 'Unit of Measure'),
        ('region', 'Region'),
        ('tax_code', 'Tax Code'),
        ('payment_mode', 'Payment Mode'),
        ('transaction_type', 'Transaction Type'),
        ('document_type', 'Document Type'),
        ('nature_of_supply', 'Nature of Supply'),
        ('payment_term', 'Payment Term'),
    ], string='Type', required=True, help='Type of master data')
    
    description = fields.Text(
        string='Description',
        help='Detailed description of this master data entry'
    )
    
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this master data entry is active'
    )
    
    # Computed fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    # Additional fields for specific types
    parent_id = fields.Many2one(
        'eims.master',
        string='Parent',
        help='Parent master data entry (e.g., region for wereda)'
    )
    child_ids = fields.One2many(
        'eims.master',
        'parent_id',
        string='Children',
        help='Child master data entries'
    )
    
    # For regions
    region_code = fields.Char(
        string='Region Code',
        help='Official region code'
    )
    wereda_code = fields.Char(
        string='Wereda Code',
        help='Official wereda code'
    )
    
    # For tax codes
    tax_rate = fields.Float(
        string='Tax Rate (%)',
        digits=(5, 2),
        help='Tax rate percentage'
    )
    
    # For UoM
    uom_category = fields.Char(
        string='UoM Category',
        help='Unit of measure category'
    )
    
    @api.depends('name', 'code', 'type')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"
    
    @api.constrains('code', 'type')
    def _check_unique_code_per_type(self):
        """Ensure unique code per type"""
        for record in self:
            existing = self.search([
                ('code', '=', record.code),
                ('type', '=', record.type),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    _("Code '%s' already exists for type '%s'") % 
                    (record.code, dict(record._fields['type'].selection)[record.type])
                )
    
    @api.model
    def get_by_code(self, code, data_type):
        """Get master data entry by code and type"""
        return self.search([
            ('code', '=', code),
            ('type', '=', data_type),
            ('is_active', '=', True)
        ], limit=1)
    
    @api.model
    def get_all_by_type(self, data_type):
        """Get all active master data entries by type"""
        return self.search([
            ('type', '=', data_type),
            ('is_active', '=', True)
        ])
    
    def action_deactivate(self):
        """Deactivate master data entry"""
        self.write({'is_active': False})
    
    def action_activate(self):
        """Activate master data entry"""
        self.write({'is_active': True})
    
    @api.model
    def load_default_data(self):
        """Load default master data entries"""
        default_data = [
            # Regions
            {'name': 'Addis Ababa', 'code': '11', 'type': 'region', 'region_code': '11'},
            {'name': 'Dire Dawa', 'code': '12', 'type': 'region', 'region_code': '12'},
            {'name': 'Harari', 'code': '13', 'type': 'region', 'region_code': '13'},
            {'name': 'Oromia', 'code': '14', 'type': 'region', 'region_code': '14'},
            {'name': 'Amhara', 'code': '15', 'type': 'region', 'region_code': '15'},
            {'name': 'Tigray', 'code': '16', 'type': 'region', 'region_code': '16'},
            {'name': 'SNNPR', 'code': '17', 'type': 'region', 'region_code': '17'},
            {'name': 'Afar', 'code': '18', 'type': 'region', 'region_code': '18'},
            {'name': 'Somali', 'code': '19', 'type': 'region', 'region_code': '19'},
            {'name': 'Gambela', 'code': '20', 'type': 'region', 'region_code': '20'},
            {'name': 'Benishangul-Gumuz', 'code': '21', 'type': 'region', 'region_code': '21'},
            {'name': 'Sidama', 'code': '22', 'type': 'region', 'region_code': '22'},
            
            # Transaction Types
            {'name': 'Business to Business', 'code': 'B2B', 'type': 'transaction_type'},
            {'name': 'Business to Consumer', 'code': 'B2C', 'type': 'transaction_type'},
            {'name': 'Business to Government', 'code': 'B2G', 'type': 'transaction_type'},
            {'name': 'Government to Business', 'code': 'G2B', 'type': 'transaction_type'},
            {'name': 'Government to Consumer', 'code': 'G2C', 'type': 'transaction_type'},
            
            # Document Types
            {'name': 'Invoice', 'code': 'INV', 'type': 'document_type'},
            {'name': 'Credit Note', 'code': 'CRE', 'type': 'document_type'},
            {'name': 'Debit Note', 'code': 'DEB', 'type': 'document_type'},
            {'name': 'Interest Note', 'code': 'INT', 'type': 'document_type'},
            {'name': 'Final Note', 'code': 'FIN', 'type': 'document_type'},
            
            # Payment Modes
            {'name': 'Cash', 'code': 'Cash', 'type': 'payment_mode'},
            {'name': 'Bank Transfer', 'code': 'Bank Transfer', 'type': 'payment_mode'},
            {'name': 'Check', 'code': 'Check', 'type': 'payment_mode'},
            {'name': 'Credit Card', 'code': 'Credit Card', 'type': 'payment_mode'},
            {'name': 'Mobile Payment', 'code': 'Mobile Payment', 'type': 'payment_mode'},
            
            # Payment Terms
            {'name': 'Immediate', 'code': 'IMMEDIATE', 'type': 'payment_term'},
            {'name': 'Net 15', 'code': 'NET15', 'type': 'payment_term'},
            {'name': 'Net 30', 'code': 'NET30', 'type': 'payment_term'},
            {'name': 'Net 60', 'code': 'NET60', 'type': 'payment_term'},
            
            # Nature of Supply
            {'name': 'Goods', 'code': 'GOODS', 'type': 'nature_of_supply'},
            {'name': 'Services', 'code': 'SERVICES', 'type': 'nature_of_supply'},
            {'name': 'Mixed', 'code': 'MIXED', 'type': 'nature_of_supply'},
            
            # Tax Codes
            {'name': 'VAT 15%', 'code': 'VAT15', 'type': 'tax_code', 'tax_rate': 15.0},
            {'name': 'VAT 0%', 'code': 'VAT0', 'type': 'tax_code', 'tax_rate': 0.0},
            {'name': 'Exempt', 'code': 'EXEMPT', 'type': 'tax_code', 'tax_rate': 0.0},
            
            # Common UoM
            {'name': 'Piece', 'code': 'PCS', 'type': 'uom', 'uom_category': 'Count'},
            {'name': 'Kilogram', 'code': 'KG', 'type': 'uom', 'uom_category': 'Weight'},
            {'name': 'Liter', 'code': 'L', 'type': 'uom', 'uom_category': 'Volume'},
            {'name': 'Meter', 'code': 'M', 'type': 'uom', 'uom_category': 'Length'},
            {'name': 'Hour', 'code': 'H', 'type': 'uom', 'uom_category': 'Time'},
            {'name': 'Day', 'code': 'D', 'type': 'uom', 'uom_category': 'Time'},
        ]
        
        created_count = 0
        for data in default_data:
            existing = self.search([
                ('code', '=', data['code']),
                ('type', '=', data['type'])
            ])
            if not existing:
                self.create(data)
                created_count += 1
        
        _logger.info("Loaded %d default EIMS master data entries", created_count)
        return created_count

