from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from ..utils import signer
from ..utils import auth
from ..utils import config
import json
import logging
import requests
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

_logger.info("Loading EIMS Integration AccountMove class")

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Existing EIMS fields (enhanced)
    eims_irn = fields.Char(
        string="EIMS IRN",
        readonly=True,
        help="Invoice Reference Number from EIMS"
    )
    eims_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('ok', 'Success'),
        ('failed', 'Failed')
    ], default='draft', string="EIMS Status", readonly=True)
    eims_error_message = fields.Text(
        string="EIMS Error Message",
        readonly=True,
        help="Last error message from EIMS integration"
    )
    
    # New EIMS fields (Phase-1 requirements)
    eims_qr_image = fields.Binary(
        string="QR Code Image",
        readonly=True,
        help="QR code image received from EIMS"
    )
    eims_signed_invoice = fields.Binary(
        string="Signed Invoice",
        readonly=True,
        help="Signed invoice document from EIMS"
    )
    eims_ack_date = fields.Datetime(
        string="Acknowledgment Date",
        readonly=True,
        help="Date when EIMS acknowledged the invoice"
    )
    eims_last_error = fields.Text(
        string="Last Error",
        readonly=True,
        help="Last error message from EIMS"
    )
    eims_sent_json = fields.Text(
        string="Sent JSON",
        readonly=True,
        help="Full JSON payload sent to EIMS (for debugging)"
    )
    
    # Related fields
    eims_log_ids = fields.One2many(
        'eims.log',
        'move_id',
        string="EIMS Logs",
        readonly=True,
        help="All EIMS integration logs for this invoice"
    )
    eims_log_count = fields.Integer(
        string="Log Count",
        compute='_compute_eims_log_count',
        help="Number of EIMS log entries"
    )
    
    # Computed fields
    eims_can_retry = fields.Boolean(
        string="Can Retry",
        compute='_compute_eims_can_retry',
        help="Whether this invoice can be retried for EIMS integration"
    )
    eims_is_registered = fields.Boolean(
        string="Is Registered",
        compute='_compute_eims_is_registered',
        help="Whether this invoice is registered with EIMS"
    )
    
    @api.depends('eims_log_ids')
    def _compute_eims_log_count(self):
        """Compute the number of EIMS log entries"""
        for record in self:
            record.eims_log_count = len(record.eims_log_ids)
    
    @api.depends('eims_status', 'eims_irn')
    def _compute_eims_can_retry(self):
        """Check if invoice can be retried"""
        for record in self:
            record.eims_can_retry = (
                record.eims_status in ['failed', 'error'] and 
                not record.eims_irn and
                record.move_type == 'out_invoice'
            )
    
    @api.depends('eims_status', 'eims_irn')
    def _compute_eims_is_registered(self):
        """Check if invoice is registered with EIMS"""
        for record in self:
            record.eims_is_registered = (
                record.eims_status == 'ok' and 
                bool(record.eims_irn)
            )

    def action_post(self):
        _logger.info("EIMS action_post method called for invoice(s)")
        # Call original Odoo post method
        result = super(AccountMove, self).action_post()

        # Only trigger for customer invoices
        for invoice in self:
            _logger.info("Processing invoice %s with move_type: %s", invoice.name, invoice.move_type)
            if invoice.move_type == 'out_invoice' and invoice.company_id.country_id.code == 'ET':
                # Check if already registered
                if invoice.eims_irn:
                    _logger.info("Invoice %s already registered with EIMS (IRN: %s)", invoice.name, invoice.eims_irn)
                    continue
                
                _logger.info("Triggering EIMS integration for invoice %s", invoice.name)
                try:
                    invoice.send_to_eims()
                except Exception as e:
                    _logger.error("EIMS integration failed for invoice %s: %s", invoice.name, str(e))
                    # Don't block posting, just log the error
                    invoice.write({
                        'eims_status': 'failed',
                        'eims_last_error': str(e),
                        'eims_error_message': str(e)
                    })
            else:
                _logger.info("Skipping EIMS for invoice %s (move_type: %s, country: %s)", 
                           invoice.name, invoice.move_type, invoice.company_id.country_id.code)

        return result

    def send_to_eims(self):
        """Send invoice to EIMS with comprehensive logging and error handling"""
        cfg = config
        start_time = time.time()
        
        for inv in self:
            log_vals = {
                'move_id': inv.id,
                'state': 'draft',
                'datetime': fields.Datetime.now(),
            }
            
            try:
                # Clear previous errors
                inv.write({
                    'eims_status': 'pending',
                    'eims_last_error': False,
                    'eims_error_message': False
                })
                
                _logger.info("Starting EIMS integration for invoice %s", inv.name)
                
                # Step 1: Validate prerequisites
                self._validate_eims_prerequisites(inv)
                
                # Step 2: Prepare payload
                _logger.info("Preparing invoice payload for %s", inv.name)
                payload = inv._prepare_eims_payload()
                log_vals['request_json'] = json.dumps(payload, indent=2)
                
                # Step 3: Load certificate and key
                try:
                    with open(cfg.EIMS_PRIVATE_KEY_PATH, 'rb') as key_file:
                        key_data = key_file.read()
                    with open(cfg.EIMS_CERTIFICATE_PATH, 'rb') as cert_file:
                        cert_data = cert_file.read()
                except FileNotFoundError as e:
                    raise UserError(_("Certificate or key file not found: %s") % str(e))
                
                # Step 4: Login to EIMS
                _logger.info("Attempting EIMS login...")
                token = auth.eims_login(
                    client_id=cfg.EIMS_CLIENT_ID,
                    client_secret=cfg.EIMS_CLIENT_SECRET,
                    apikey=cfg.EIMS_API_KEY,
                    tin=cfg.EIMS_TIN,
                    private_key_path=cfg.EIMS_PRIVATE_KEY_PATH,
                    certificate_path=cfg.EIMS_CERTIFICATE_PATH,
                    login_url=cfg.EIMS_LOGIN_URL,
                    timeout=cfg.EIMS_TIMEOUT
                )
                _logger.info("EIMS Access Token retrieved successfully")
                
                # Step 5: Sign the request
                request_obj = payload['request']
                canonical = signer.canonicalize_json(request_obj)
                signature = signer.sign_request_sha512(canonical, key_data)
                certificate = signer.encode_certificate(cert_data)
                
                final_payload = {
                    'request': request_obj,
                    'signature': signature,
                    'certificate': certificate
                }
                
                # Step 6: Submit to EIMS
                _logger.info("Submitting invoice to EIMS...")
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                response_start = time.time()
                response = requests.post(
                    cfg.EIMS_INVOICE_SUBMIT_URL,
                    json=final_payload,
                    headers=headers,
                    timeout=cfg.EIMS_TIMEOUT,
                    verify=cfg.EIMS_VERIFY_SSL
                )
                response_time = int((time.time() - response_start) * 1000)
                
                _logger.info("EIMS API Response Status: %s (Response time: %dms)", 
                           response.status_code, response_time)
                _logger.debug("EIMS API Response: %s", response.text)
                
                # Step 7: Process response
                log_vals.update({
                    'response_json': response.text,
                    'http_status_code': response.status_code,
                    'response_time_ms': response_time
                })
                
                if response.status_code == 200:
                    response_data = response.json()
                    _logger.info("Invoice submitted successfully to EIMS")
                    
                    # Extract response data
                    irn = response_data.get('body', {}).get('irn')
                    qr_data = response_data.get('body', {}).get('qrCode')
                    signed_invoice = response_data.get('body', {}).get('signedInvoice')
                    
                    # Update invoice with EIMS data
                    update_vals = {
                        'eims_status': 'ok',
                        'eims_ack_date': fields.Datetime.now(),
                        'eims_sent_json': json.dumps(final_payload, indent=2)
                    }
                    
                    if irn:
                        update_vals['eims_irn'] = irn
                        _logger.info("EIMS IRN received: %s", irn)
                    
                    if qr_data:
                        # Generate QR code image
                        qr_image = self._generate_qr_code(qr_data)
                        update_vals['eims_qr_image'] = qr_image
                    
                    if signed_invoice:
                        update_vals['eims_signed_invoice'] = signed_invoice
                    
                    inv.write(update_vals)
                    
                    # Update log with success
                    log_vals.update({
                        'state': 'ok',
                        'irn': irn,
                        'qr_data': qr_data
                    })
                    
                    _logger.info("EIMS integration completed successfully for invoice %s", inv.name)
                    
                else:
                    # Handle API errors
                    error_message = self._parse_eims_error(response)
                    inv.write({
                        'eims_status': 'failed',
                        'eims_last_error': error_message,
                        'eims_error_message': error_message
                    })
                    
                    log_vals.update({
                        'state': 'failed',
                        'error_text': error_message,
                        'error_code': str(response.status_code)
                    })
                    
                    _logger.error("EIMS API returned error status: %s - %s", 
                                response.status_code, error_message)
                    
            except requests.exceptions.Timeout:
                error_msg = "EIMS request timed out"
                _logger.error("EIMS request timed out for invoice %s", inv.name)
                inv.write({
                    'eims_status': 'failed',
                    'eims_last_error': error_msg,
                    'eims_error_message': error_msg
                })
                log_vals.update({
                    'state': 'failed',
                    'error_text': error_msg
                })
                
            except requests.exceptions.ConnectionError as e:
                error_msg = f"EIMS connection error: {str(e)}"
                _logger.error("EIMS connection error for invoice %s: %s", inv.name, str(e))
                inv.write({
                    'eims_status': 'failed',
                    'eims_last_error': error_msg,
                    'eims_error_message': error_msg
                })
                log_vals.update({
                    'state': 'failed',
                    'error_text': error_msg
                })
                
            except UserError:
                # Re-raise UserError as-is
                raise
                
            except Exception as e:
                error_msg = f"EIMS integration failed: {str(e)}"
                _logger.error("EIMS integration failed for invoice %s: %s", inv.name, str(e))
                inv.write({
                    'eims_status': 'failed',
                    'eims_last_error': error_msg,
                    'eims_error_message': error_msg
                })
                log_vals.update({
                    'state': 'failed',
                    'error_text': error_msg
                })
                
            finally:
                # Always create log entry
                self.env['eims.log'].create(log_vals)
    
    def _validate_eims_prerequisites(self, invoice):
        """Validate prerequisites for EIMS integration"""
        if not invoice.company_id.vat:
            raise UserError(_("Company VAT/TIN is required for EIMS integration"))
        
        if not invoice.partner_id.name:
            raise UserError(_("Customer name is required for EIMS integration"))
        
        if not invoice.invoice_line_ids:
            raise UserError(_("Invoice must have at least one line item"))
        
        # Check if certificate exists and is valid
        certificate = self.env['eims.certificate'].search([
            ('company_id', '=', invoice.company_id.id),
            ('is_active', '=', True)
        ], limit=1)
        
        if not certificate:
            raise UserError(_("No active EIMS certificate found for company %s") % invoice.company_id.name)
        
        if certificate.is_expired:
            raise UserError(_("EIMS certificate has expired. Please upload a new certificate."))
        
        if certificate.is_expiring_soon:
            _logger.warning("EIMS certificate expires soon (%d days) for company %s", 
                          certificate.days_to_expiry, invoice.company_id.name)
    
    def _parse_eims_error(self, response):
        """Parse EIMS error response into user-friendly message"""
        try:
            response_data = response.json()
            if 'message' in response_data:
                return response_data['message']
            elif 'error' in response_data:
                return response_data['error']
            elif 'errors' in response_data and response_data['errors']:
                return str(response_data['errors'][0])
            else:
                return f"HTTP {response.status_code}: {response.text[:200]}"
        except:
            return f"HTTP {response.status_code}: {response.text[:200]}"
    
    def _generate_qr_code(self, qr_data):
        """Generate QR code image from data"""
        try:
            from ..utils.qr_generator import generate_qr_code
            return generate_qr_code(qr_data)
        except ImportError:
            _logger.warning("QR code generation not available")
            return False
        except Exception as e:
            _logger.error("QR code generation failed: %s", str(e))
            return False

    def _prepare_eims_payload(self):
        self.ensure_one()
        # Helper: get value or None
        def val(obj, attr):
            return getattr(obj, attr, None) or None

        # Seller details
        seller = self.company_id
        # Buyer details
        buyer = self.partner_id

        # TransactionType logic
        transaction_type = self.move_type == 'out_invoice' and 'B2B' or 'B2C'
        buyer_tin = val(buyer, 'vat') if transaction_type not in ('B2C', 'G2C') else None
        buyer_vat = None if not buyer_tin else val(buyer, 'vat')

        # DocumentDetails
        doc_type = 'INV'  # Could be dynamic
        doc_reason = None
        if doc_type in ('CRE', 'DEB', 'INT', 'FIN'):
            doc_reason = self.ref or 'Reason required'

        # ReferenceDetails
        reference_details = {}
        if doc_type in ('CRE', 'DEB', 'INT', 'FIN'):
            reference_details['RelatedDocument'] = self.invoice_origin or 'RelatedDocRequired'

        # SourceSystem
        source_system = {
            "SystemType": config.DEFAULT_SYSTEM_TYPE,
            "SystemNumber": config.DEFAULT_SYSTEM_NUMBER,
            "InvoiceCounter": 1,  # Should be dynamic if possible
        }

        # ValueDetails
        value_details = {
            "TotalValue": self.amount_total,
            "TaxValue": self.amount_tax,
            "InvoiceCurrency": self.currency_id.name,
        }
        if self.currency_id.name != 'ETB':
            value_details["ExchangeRate"] = self.currency_id.rate or 1
        # Add optional fields as needed

        # ItemList
        item_list = []
        for i, line in enumerate(self.invoice_line_ids):
            item = {
                "LineNumber": i + 1,
                "NatureOfSupplies": line.name or "Goods",
                "ProductDescription": line.name or "",
                "ItemCode": line.product_id.default_code or "",
                "UnitPrice": line.price_unit,
                "Quantity": line.quantity,
                "Unit": line.product_uom_id.name,
                "PreTaxValue": line.price_subtotal,
                "TaxAmount": line.price_total - line.price_subtotal,
                "TotalLineAmount": line.price_total,
                "TaxCode": (line.tax_ids and line.tax_ids[0].name) or "VAT",
                # Optional fields:
                "Discount": 0,
                "HarmonizationCode": getattr(line.product_id, 'hs_code', ""),
            }
            item_list.append(item)

        # SellerDetails
        seller_details = {
            "Tin": val(seller, 'vat'),
            "LegalName": val(seller, 'name'),
            "City": val(seller, 'city'),
            "Wereda": val(seller, 'wereda') or "01",
            "Region": val(seller, 'region_id') and seller.region_id.code or config.DEFAULT_REGION,
            "Zone": val(seller, 'zone') or None,
            "Email": val(seller, 'email'),
            "Phone": val(seller, 'phone'),
            "Kebele": val(seller, 'kebele'),
            "SubTin": val(seller, 'sub_tin'),
            "Country": val(seller, 'country_id') and seller.country_id.code or None,
            "SubCity": val(seller, 'subcity'),
            "Locality": val(seller, 'locality'),
            "TradeName": val(seller, 'trade_name'),
            "VatNumber": val(seller, 'vat'),
            "HouseNumber": val(seller, 'slistt2'),
        }

        # BuyerDetails
        buyer_details = {
            "LegalName": val(buyer, 'name'),
            "Tin": buyer_tin,
            "City": val(buyer, 'city'),
            "Zone": val(buyer, 'zone'),
            "Email": val(buyer, 'email'),
            "Phone": val(buyer, 'phone'),
            "IdType": val(buyer, 'id_type'),
            "Kebele": val(buyer, 'kebele'),
            "Region": val(buyer, 'region_id') and buyer.region_id.code or config.DEFAULT_REGION,
            "SubTin": val(buyer, 'sub_tin'),
            "Wereda": val(buyer, 'wereda'),
            "Country": val(buyer, 'country_id') and buyer.country_id.code or None,
            "SubCity": val(buyer, 'subcity'),
            "IdNumber": val(buyer, 'id_number'),
            "Locality": val(buyer, 'locality'),
            "TradeName": val(buyer, 'trade_name'),
            "VatNumber": buyer_vat,
            "HouseNumber": val(buyer, 'slistt2'),
        }

        # PaymentDetails
        payment_details = {
            "PaymentTerm": config.DEFAULT_PAYMENT_TERM,
            "Mode": config.DEFAULT_PAYMENT_MODE,
        }

        # DocumentDetails
        document_details = {
            "DocumentNumber": self.name,
            "Date": self.invoice_date.strftime('%Y-%m-%dT%H:%M:%S') + "+03:00",
            "Type": doc_type,
        }
        if doc_reason:
            document_details["Reason"] = doc_reason

        payload = {
            "request": {
                "TransactionType": transaction_type,
                "DocumentDetails": document_details,
                "SourceSystem": source_system,
                "SellerDetails": seller_details,
                "BuyerDetails": buyer_details,
                "ItemList": item_list,
                "PaymentDetails": payment_details,
                "ValueDetails": value_details,
                "ReferenceDetails": reference_details,
            },
            "signature": "",
            "certificate": ""
        }
        return payload
    
    def action_view_eims_logs(self):
        """View EIMS logs for this invoice"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('EIMS Logs - %s') % self.name,
            'res_model': 'eims.log',
            'view_mode': 'list,form',
            'domain': [('move_id', '=', self.id)],
            'context': {'default_move_id': self.id},
            'target': 'current',
        }
    
    def action_retry_eims(self):
        """Retry EIMS integration for this invoice"""
        self.ensure_one()
        if not self.eims_can_retry:
            raise UserError(_("This invoice cannot be retried for EIMS integration"))
        
        try:
            self.send_to_eims()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Retry Initiated'),
                    'message': _('Invoice %s is being retried for EIMS integration') % self.name,
                    'type': 'info',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Could not retry EIMS integration: %s") % str(e))
    
    def action_copy_irn(self):
        """Copy IRN to clipboard (JavaScript action)"""
        self.ensure_one()
        if not self.eims_irn:
            raise UserError(_("No IRN available for this invoice"))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('IRN Copied'),
                'message': _('IRN %s copied to clipboard') % self.eims_irn,
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def retry_failed_eims_invoices(self):
        """Retry failed EIMS integrations for invoices"""
        try:
            # Find invoices that failed EIMS integration
            failed_invoices = self.search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('eims_status', '=', 'failed'),
                ('eims_irn', '=', False),
                ('company_id.country_id.code', '=', 'ET')
            ])
            
            retry_count = 0
            for invoice in failed_invoices:
                try:
                    # Check if certificate is available and valid
                    certificate = self.env['eims.certificate'].search([
                        ('company_id', '=', invoice.company_id.id),
                        ('is_active', '=', True)
                    ], limit=1)
                    
                    if not certificate or certificate.is_expired:
                        _logger.warning("Skipping retry for invoice %s - no valid certificate", invoice.name)
                        continue
                    
                    # Retry EIMS integration
                    invoice.send_to_eims()
                    retry_count += 1
                    
                except Exception as e:
                    _logger.error("Failed to retry EIMS integration for invoice %s: %s", invoice.name, str(e))
            
            _logger.info("EIMS retry completed. Retried %d invoices", retry_count)
            
        except Exception as e:
            _logger.error("EIMS retry process failed: %s", str(e))
