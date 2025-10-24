# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # EIMS Authentication Settings
    eims_client_id = fields.Char(
        string='EIMS Client ID',
        config_parameter='eims_integration.client_id',
        help='EIMS Client ID for authentication'
    )
    eims_client_secret = fields.Char(
        string='EIMS Client Secret',
        config_parameter='eims_integration.client_secret',
        help='EIMS Client Secret for authentication'
    )
    eims_api_key = fields.Char(
        string='EIMS API Key',
        config_parameter='eims_integration.api_key',
        help='EIMS API Key'
    )
    eims_tin = fields.Char(
        string='Company TIN',
        config_parameter='eims_integration.tin',
        help='Company Tax Identification Number'
    )

    # EIMS API Endpoints
    eims_login_url = fields.Char(
        string='EIMS Login URL',
        config_parameter='eims_integration.login_url',
        default='https://core.mor.gov.et/auth/login',
        help='EIMS Login API Endpoint'
    )
    eims_invoice_submit_url = fields.Char(
        string='EIMS Invoice Submit URL',
        config_parameter='eims_integration.invoice_submit_url',
        default='https://core.mor.gov.et/v1/register',
        help='EIMS Invoice Submission API Endpoint'
    )

    # Certificate and Key Paths
    eims_private_key_path = fields.Char(
        string='Private Key Path',
        config_parameter='eims_integration.private_key_path',
        help='Path to private key file (.key)'
    )
    eims_certificate_path = fields.Char(
        string='Certificate Path',
        config_parameter='eims_integration.certificate_path',
        help='Path to certificate file (.pem)'
    )

    # Request Settings
    eims_timeout = fields.Integer(
        string='Request Timeout (seconds)',
        config_parameter='eims_integration.timeout',
        default=30,
        help='Request timeout in seconds'
    )
    eims_verify_ssl = fields.Boolean(
        string='Verify SSL',
        config_parameter='eims_integration.verify_ssl',
        default=True,
        help='Verify SSL certificates'
    )

    # Integration Settings
    eims_auto_register = fields.Boolean(
        string='Auto Register Invoices',
        config_parameter='eims_integration.auto_register',
        default=True,
        help='Automatically register invoices with EIMS when posted'
    )
    eims_block_on_error = fields.Boolean(
        string='Block on Error',
        config_parameter='eims_integration.block_on_error',
        default=False,
        help='Block invoice posting if EIMS registration fails'
    )

    # Company Default Settings
    eims_default_region = fields.Char(
        string='Default Region',
        config_parameter='eims_integration.default_region',
        default='11',
        help='Default region code for EIMS'
    )
    eims_default_wereda = fields.Char(
        string='Default Wereda',
        config_parameter='eims_integration.default_wereda',
        default='01',
        help='Default wereda code for EIMS'
    )
    eims_default_system_type = fields.Char(
        string='Default System Type',
        config_parameter='eims_integration.default_system_type',
        default='POS',
        help='Default system type for EIMS'
    )
    eims_default_system_number = fields.Char(
        string='Default System Number',
        config_parameter='eims_integration.default_system_number',
        default='ODOO18',
        help='Default system number for EIMS'
    )

    @api.model
    def get_values(self):
        """Get configuration values"""
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        
        res.update(
            eims_client_id=params.get_param('eims_integration.client_id', ''),
            eims_client_secret=params.get_param('eims_integration.client_secret', ''),
            eims_api_key=params.get_param('eims_integration.api_key', ''),
            eims_tin=params.get_param('eims_integration.tin', ''),
            eims_login_url=params.get_param('eims_integration.login_url', 'https://core.mor.gov.et/auth/login'),
            eims_invoice_submit_url=params.get_param('eims_integration.invoice_submit_url', 'https://core.mor.gov.et/v1/register'),
            eims_private_key_path=params.get_param('eims_integration.private_key_path', ''),
            eims_certificate_path=params.get_param('eims_integration.certificate_path', ''),
            eims_timeout=int(params.get_param('eims_integration.timeout', '30')),
            eims_verify_ssl=params.get_param('eims_integration.verify_ssl', 'True') == 'True',
            eims_auto_register=params.get_param('eims_integration.auto_register', 'True') == 'True',
            eims_block_on_error=params.get_param('eims_integration.block_on_error', 'False') == 'True',
            eims_default_region=params.get_param('eims_integration.default_region', '11'),
            eims_default_wereda=params.get_param('eims_integration.default_wereda', '01'),
            eims_default_system_type=params.get_param('eims_integration.default_system_type', 'POS'),
            eims_default_system_number=params.get_param('eims_integration.default_system_number', 'ODOO18'),
        )
        return res

    def set_values(self):
        """Set configuration values"""
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        
        params.set_param('eims_integration.client_id', self.eims_client_id or '')
        params.set_param('eims_integration.client_secret', self.eims_client_secret or '')
        params.set_param('eims_integration.api_key', self.eims_api_key or '')
        params.set_param('eims_integration.tin', self.eims_tin or '')
        params.set_param('eims_integration.login_url', self.eims_login_url or 'https://core.mor.gov.et/auth/login')
        params.set_param('eims_integration.invoice_submit_url', self.eims_invoice_submit_url or 'https://core.mor.gov.et/v1/register')
        params.set_param('eims_integration.private_key_path', self.eims_private_key_path or '')
        params.set_param('eims_integration.certificate_path', self.eims_certificate_path or '')
        params.set_param('eims_integration.timeout', str(self.eims_timeout))
        params.set_param('eims_integration.verify_ssl', str(self.eims_verify_ssl))
        params.set_param('eims_integration.auto_register', str(self.eims_auto_register))
        params.set_param('eims_integration.block_on_error', str(self.eims_block_on_error))
        params.set_param('eims_integration.default_region', self.eims_default_region or '11')
        params.set_param('eims_integration.default_wereda', self.eims_default_wereda or '01')
        params.set_param('eims_integration.default_system_type', self.eims_default_system_type or 'POS')
        params.set_param('eims_integration.default_system_number', self.eims_default_system_number or 'ODOO18')

    def action_test_eims_connection(self):
        """Test EIMS connection with current settings"""
        try:
            from ..utils import auth, config
            
            # Update config with current settings
            config.EIMS_CLIENT_ID = self.eims_client_id
            config.EIMS_CLIENT_SECRET = self.eims_client_secret
            config.EIMS_API_KEY = self.eims_api_key
            config.EIMS_TIN = self.eims_tin
            config.EIMS_LOGIN_URL = self.eims_login_url
            config.EIMS_INVOICE_SUBMIT_URL = self.eims_invoice_submit_url
            config.EIMS_PRIVATE_KEY_PATH = self.eims_private_key_path
            config.EIMS_CERTIFICATE_PATH = self.eims_certificate_path
            config.EIMS_TIMEOUT = self.eims_timeout
            config.EIMS_VERIFY_SSL = self.eims_verify_ssl
            
            # Test login
            token = auth.eims_login(
                client_id=self.eims_client_id,
                client_secret=self.eims_client_secret,
                apikey=self.eims_api_key,
                tin=self.eims_tin,
                private_key_path=self.eims_private_key_path,
                certificate_path=self.eims_certificate_path,
                login_url=self.eims_login_url,
                timeout=self.eims_timeout
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test Successful'),
                    'message': _('EIMS connection test completed successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test Failed'),
                    'message': _('EIMS connection test failed: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

