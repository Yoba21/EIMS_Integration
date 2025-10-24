# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class EimsConfigurationWizard(models.TransientModel):
    _name = 'eims.configuration.wizard'
    _description = 'EIMS Configuration Wizard'
    
    # Step 1: Basic Information
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Step 2: EIMS Credentials
    eims_client_id = fields.Char(
        string='EIMS Client ID',
        required=True,
        help='Your EIMS Client ID'
    )
    eims_client_secret = fields.Char(
        string='EIMS Client Secret',
        required=True,
        help='Your EIMS Client Secret'
    )
    eims_api_key = fields.Char(
        string='EIMS API Key',
        required=True,
        help='Your EIMS API Key'
    )
    eims_tin = fields.Char(
        string='Company TIN',
        required=True,
        help='Company Tax Identification Number'
    )
    
    # Step 3: API Endpoints
    eims_login_url = fields.Char(
        string='EIMS Login URL',
        default='https://core.mor.gov.et/auth/login',
        required=True
    )
    eims_invoice_submit_url = fields.Char(
        string='EIMS Invoice Submit URL',
        default='https://core.mor.gov.et/v1/register',
        required=True
    )
    
    # Step 4: Certificate Information
    certificate_name = fields.Char(
        string='Certificate Name',
        required=True,
        help='Friendly name for your certificate'
    )
    pfx_file = fields.Binary(
        string='PKCS#12 Certificate File',
        required=True,
        help='Upload your PKCS#12 certificate file (.pfx or .p12)'
    )
    pfx_filename = fields.Char(
        string='Filename'
    )
    pfx_password = fields.Char(
        string='Certificate Password',
        required=True,
        help='Password for the PKCS#12 certificate file'
    )
    
    # Step 5: Settings
    eims_timeout = fields.Integer(
        string='Request Timeout (seconds)',
        default=30,
        help='Request timeout in seconds'
    )
    eims_verify_ssl = fields.Boolean(
        string='Verify SSL',
        default=True,
        help='Verify SSL certificates'
    )
    eims_auto_register = fields.Boolean(
        string='Auto Register Invoices',
        default=True,
        help='Automatically register invoices with EIMS when posted'
    )
    eims_block_on_error = fields.Boolean(
        string='Block on Error',
        default=False,
        help='Block invoice posting if EIMS registration fails'
    )
    
    # Wizard state
    current_step = fields.Integer(
        string='Current Step',
        default=1
    )
    total_steps = fields.Integer(
        string='Total Steps',
        default=5
    )
    
    # Validation results
    validation_results = fields.Text(
        string='Validation Results',
        readonly=True
    )
    
    def action_next_step(self):
        """Move to next step"""
        if self.current_step < self.total_steps:
            self.current_step += 1
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eims.configuration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_previous_step(self):
        """Move to previous step"""
        if self.current_step > 1:
            self.current_step -= 1
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'eims.configuration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_validate_configuration(self):
        """Validate the configuration"""
        try:
            results = []
            
            # Validate credentials
            if not self.eims_client_id:
                results.append("❌ EIMS Client ID is required")
            else:
                results.append("✅ EIMS Client ID provided")
            
            if not self.eims_client_secret:
                results.append("❌ EIMS Client Secret is required")
            else:
                results.append("✅ EIMS Client Secret provided")
            
            if not self.eims_api_key:
                results.append("❌ EIMS API Key is required")
            else:
                results.append("✅ EIMS API Key provided")
            
            if not self.eims_tin:
                results.append("❌ Company TIN is required")
            else:
                results.append("✅ Company TIN provided")
            
            # Validate certificate
            if not self.pfx_file:
                results.append("❌ Certificate file is required")
            else:
                results.append("✅ Certificate file provided")
            
            if not self.pfx_password:
                results.append("❌ Certificate password is required")
            else:
                results.append("✅ Certificate password provided")
            
            # Test certificate validity
            if self.pfx_file and self.pfx_password:
                try:
                    from ..models.eims_certificate import EimsCertificate
                    temp_cert = EimsCertificate.create({
                        'name': 'Temp Validation',
                        'company_id': self.company_id.id,
                        'pfx_file': self.pfx_file,
                        'pfx_password': self.pfx_password
                    })
                    if temp_cert.expiry_date:
                        results.append(f"✅ Certificate valid, expires on {temp_cert.expiry_date}")
                        if temp_cert.is_expired:
                            results.append("⚠️ Certificate has expired")
                        elif temp_cert.is_expiring_soon:
                            results.append(f"⚠️ Certificate expires in {temp_cert.days_to_expiry} days")
                    temp_cert.unlink()
                except Exception as e:
                    results.append(f"❌ Certificate validation failed: {str(e)}")
            
            self.validation_results = '\n'.join(results)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Validation'),
                    'message': _('Validation completed. Check the results below.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_("Configuration validation failed: %s") % str(e))
    
    def action_save_configuration(self):
        """Save the configuration"""
        try:
            # Save settings to config parameters
            params = self.env['ir.config_parameter'].sudo()
            
            params.set_param('eims_integration.client_id', self.eims_client_id)
            params.set_param('eims_integration.client_secret', self.eims_client_secret)
            params.set_param('eims_integration.api_key', self.eims_api_key)
            params.set_param('eims_integration.tin', self.eims_tin)
            params.set_param('eims_integration.login_url', self.eims_login_url)
            params.set_param('eims_integration.invoice_submit_url', self.eims_invoice_submit_url)
            params.set_param('eims_integration.timeout', str(self.eims_timeout))
            params.set_param('eims_integration.verify_ssl', str(self.eims_verify_ssl))
            params.set_param('eims_integration.auto_register', str(self.eims_auto_register))
            params.set_param('eims_integration.block_on_error', str(self.eims_block_on_error))
            
            # Create certificate record
            certificate = self.env['eims.certificate'].create({
                'name': self.certificate_name,
                'company_id': self.company_id.id,
                'pfx_file': self.pfx_file,
                'pfx_filename': self.pfx_filename,
                'pfx_password': self.pfx_password,
                'is_active': True
            })
            
            _logger.info("EIMS configuration saved successfully for company %s", self.company_id.name)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Saved'),
                    'message': _('EIMS configuration has been saved successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_("Failed to save configuration: %s") % str(e))
    
    def action_test_connection(self):
        """Test EIMS connection"""
        try:
            from ..utils import auth, config
            
            # Update config with wizard values
            config.EIMS_CLIENT_ID = self.eims_client_id
            config.EIMS_CLIENT_SECRET = self.eims_client_secret
            config.EIMS_API_KEY = self.eims_api_key
            config.EIMS_TIN = self.eims_tin
            config.EIMS_LOGIN_URL = self.eims_login_url
            config.EIMS_INVOICE_SUBMIT_URL = self.eims_invoice_submit_url
            config.EIMS_TIMEOUT = self.eims_timeout
            config.EIMS_VERIFY_SSL = self.eims_verify_ssl
            
            # Test login (this will fail without actual certificate files)
            # For now, just validate the credentials format
            if len(self.eims_client_id) < 10:
                raise ValidationError("Client ID appears to be invalid")
            
            if len(self.eims_client_secret) < 10:
                raise ValidationError("Client Secret appears to be invalid")
            
            if len(self.eims_api_key) < 10:
                raise ValidationError("API Key appears to be invalid")
            
            if len(self.eims_tin) < 9:
                raise ValidationError("TIN appears to be invalid")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test'),
                    'message': _('Credentials format validation passed. Full connection test requires certificate files.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_("Connection test failed: %s") % str(e))

