# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class EimsCertificate(models.Model):
    _name = 'eims.certificate'
    _description = 'EIMS Certificate Management'
    _order = 'create_date desc'
    
    name = fields.Char(
        string='Certificate Name', 
        required=True,
        help='Friendly name for this certificate'
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    pfx_file = fields.Binary(
        string='PKCS#12 Certificate File', 
        required=True,
        help='Upload your PKCS#12 certificate file (.pfx or .p12)'
    )
    pfx_filename = fields.Char(
        string='Filename',
        help='Original filename of the uploaded certificate'
    )
    pfx_password = fields.Char(
        string='Certificate Password', 
        required=True,
        help='Password for the PKCS#12 certificate file'
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        compute='_compute_expiry_date',
        store=True,
        help='Certificate expiry date extracted from the certificate'
    )
    is_active = fields.Boolean(
        string='Active', 
        default=True,
        help='Whether this certificate is currently active for EIMS integration'
    )
    created_date = fields.Datetime(
        string='Created Date', 
        default=fields.Datetime.now
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    
    # Computed fields for UI display
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_days_to_expiry',
        help='Number of days until certificate expires'
    )
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        help='Whether the certificate has expired',
        store=True
    )
    is_expiring_soon = fields.Boolean(
        string='Expiring Soon',
        compute='_compute_is_expiring_soon',
        help='Whether the certificate expires within 30 days',
        store=True
    )
    
    @api.depends('pfx_file', 'pfx_password')
    def _compute_expiry_date(self):
        """Extract expiry date from PKCS#12 certificate"""
        for record in self:
            if record.pfx_file and record.pfx_password:
                try:
                    expiry_date = self._extract_certificate_expiry(
                        record.pfx_file, 
                        record.pfx_password
                    )
                    record.expiry_date = expiry_date
                except Exception as e:
                    _logger.warning("Could not extract certificate expiry date: %s", str(e))
                    record.expiry_date = False
            else:
                record.expiry_date = False
    
    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        """Calculate days until certificate expires"""
        today = fields.Date.today()
        for record in self:
            if record.expiry_date:
                delta = record.expiry_date - today
                record.days_to_expiry = delta.days
            else:
                record.days_to_expiry = 0
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        """Check if certificate is expired"""
        today = fields.Date.today()
        for record in self:
            record.is_expired = record.expiry_date and record.expiry_date < today
    
    @api.depends('expiry_date')
    def _compute_is_expiring_soon(self):
        """Check if certificate expires within 30 days"""
        today = fields.Date.today()
        for record in self:
            if record.expiry_date:
                delta = record.expiry_date - today
                record.is_expiring_soon = 0 <= delta.days <= 30
            else:
                record.is_expiring_soon = False
    
    def _extract_certificate_expiry(self, pfx_data, password):
        """Extract expiry date from PKCS#12 certificate"""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.serialization import pkcs12
            
            # Decode base64 data
            if isinstance(pfx_data, str):
                pfx_bytes = base64.b64decode(pfx_data)
            else:
                pfx_bytes = pfx_data
            
            # Load PKCS#12
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pfx_bytes,
                password.encode() if isinstance(password, str) else password,
                backend=default_backend()
            )
            
            if certificate:
                # Extract expiry date from certificate
                expiry_date = certificate.not_valid_after.date()
                return expiry_date
            else:
                raise ValidationError(_("No certificate found in PKCS#12 file"))
                
        except Exception as e:
            _logger.error("Error extracting certificate expiry: %s", str(e))
            raise ValidationError(_("Could not extract certificate expiry date: %s") % str(e))
    
    @api.model
    def create(self, vals_list):
        """Override create to validate certificate"""
        record = super().create(vals_list)
        
        # Validate certificate on creation
        if record.pfx_file and record.pfx_password:
            try:
                record._extract_certificate_expiry(record.pfx_file, record.pfx_password)
            except ValidationError:
                # Certificate validation failed, but don't block creation
                # Just log the warning
                _logger.warning("Certificate validation failed for %s", record.name)
        
        return record
    
    def write(self, vals):
        """Override write to validate certificate if changed"""
        result = super().write(vals)
        
        # Re-validate certificate if file or password changed
        if 'pfx_file' in vals or 'pfx_password' in vals:
            for record in self:
                if record.pfx_file and record.pfx_password:
                    try:
                        record._extract_certificate_expiry(record.pfx_file, record.pfx_password)
                    except ValidationError:
                        _logger.warning("Certificate validation failed for %s", record.name)
        
        return result
    
    @api.constrains('company_id', 'is_active')
    def _check_active_certificate_per_company(self):
        """Ensure only one active certificate per company"""
        for record in self:
            if record.is_active:
                existing_active = self.search([
                    ('company_id', '=', record.company_id.id),
                    ('is_active', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing_active:
                    raise ValidationError(
                        _("Only one active certificate is allowed per company. "
                          "Please deactivate the existing certificate first.")
                    )
    
    def action_deactivate(self):
        """Deactivate certificate"""
        self.write({'is_active': False})
    
    def action_activate(self):
        """Activate certificate"""
        self.write({'is_active': True})
    
    def action_test_certificate(self):
        """Test certificate validity"""
        self.ensure_one()
        try:
            expiry_date = self._extract_certificate_expiry(self.pfx_file, self.pfx_password)
            message = _("Certificate is valid and expires on %s") % expiry_date.strftime('%Y-%m-%d')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Certificate Test'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Certificate Test Failed'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    @api.model
    def check_certificate_expiry(self):
        """Check certificate expiry and send notifications"""
        try:
            # Find certificates expiring in the next 30 days
            expiring_certificates = self.search([
                ('is_active', '=', True),
                ('expiry_date', '<=', fields.Date.today() + timedelta(days=30)),
                ('expiry_date', '>', fields.Date.today())
            ])
            
            for cert in expiring_certificates:
                days_to_expiry = cert.days_to_expiry
                
                if days_to_expiry <= 7:
                    # Critical - expires within 7 days
                    self._send_certificate_alert(cert, 'critical', days_to_expiry)
                elif days_to_expiry <= 15:
                    # Warning - expires within 15 days
                    self._send_certificate_alert(cert, 'warning', days_to_expiry)
                elif days_to_expiry <= 30:
                    # Info - expires within 30 days
                    self._send_certificate_alert(cert, 'info', days_to_expiry)
            
            # Find expired certificates
            expired_certificates = self.search([
                ('is_active', '=', True),
                ('expiry_date', '<', fields.Date.today())
            ])
            
            for cert in expired_certificates:
                self._send_certificate_alert(cert, 'expired', 0)
                # Deactivate expired certificates
                cert.write({'is_active': False})
            
            _logger.info("Certificate expiry check completed. Found %d expiring and %d expired certificates", 
                       len(expiring_certificates), len(expired_certificates))
                       
        except Exception as e:
            _logger.error("Certificate expiry check failed: %s", str(e))
    
    def _send_certificate_alert(self, certificate, alert_type, days_to_expiry):
        """Send certificate expiry alert"""
        try:
            from datetime import timedelta
            
            # Get EIMS managers
            managers = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('eims_integration.group_eims_manager').id)
            ])
            
            if not managers:
                return
            
            # Prepare alert message
            if alert_type == 'expired':
                subject = f"EIMS Certificate Expired - {certificate.name}"
                message = f"""
EIMS Certificate Alert - EXPIRED

Certificate: {certificate.name}
Company: {certificate.company_id.name}
Expiry Date: {certificate.expiry_date}

This certificate has expired and needs to be replaced immediately.
EIMS integration will fail until a new certificate is uploaded.
                """
            else:
                urgency = "CRITICAL" if alert_type == 'critical' else "WARNING" if alert_type == 'warning' else "INFO"
                subject = f"EIMS Certificate Expiring Soon - {certificate.name}"
                message = f"""
EIMS Certificate Alert - {urgency}

Certificate: {certificate.name}
Company: {certificate.company_id.name}
Expiry Date: {certificate.expiry_date}
Days Remaining: {days_to_expiry}

Please upload a new certificate before the current one expires.
                """
            
            # Create mail message
            self.env['mail.message'].create({
                'subject': subject,
                'body': message,
                'message_type': 'notification',
                'partner_ids': [(6, 0, managers.mapped('partner_id').ids)],
            })
            
            _logger.info("Sent certificate %s alert for %s (expires in %d days)", 
                       alert_type, certificate.name, days_to_expiry)
                       
        except Exception as e:
            _logger.error("Failed to send certificate alert: %s", str(e))
