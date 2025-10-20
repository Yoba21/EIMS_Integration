from odoo import models, fields, api
from ..utils import signer
from ..utils import auth
from ..utils import config
import json
import logging
import requests

_logger = logging.getLogger(__name__)

_logger.info("Loading EIMS Integration AccountMove class")

class AccountMove(models.Model):
    _inherit = 'account.move'

    eims_irn = fields.Char(string="EIMS IRN")
    eims_status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('error', 'Error')
    ], default='pending', string="EIMS Status")
    eims_error_message = fields.Text(string="EIMS Error Message")

    def action_post(self):
        _logger.info("EIMS action_post method called for invoice(s)")
        # Call original Odoo post method
        result = super(AccountMove, self).action_post()

        # Only trigger for customer invoices
        for invoice in self:
            _logger.info("Processing invoice %s with move_type: %s", invoice.name, invoice.move_type)
            if invoice.move_type == 'out_invoice':
                _logger.info("Triggering EIMS login for invoice %s", invoice.name)
                # Log the payload for debug before submission
                _logger.debug("Prepared EIMS Payload: %s", json.dumps(invoice._prepare_eims_payload(), indent=2))
                invoice.send_to_eims()
            else:
                _logger.info("Skipping EIMS for invoice %s (move_type: %s)", invoice.name, invoice.move_type)

        return result

    def send_to_eims(self):
        cfg = config
        key_data = open(cfg.EIMS_PRIVATE_KEY_PATH, 'rb').read()
        cert_data = open(cfg.EIMS_CERTIFICATE_PATH, 'rb').read()
        for inv in self:
            try:
                inv.eims_error_message = False  # Clear previous error
                _logger.info("Starting EIMS integration for invoice %s", inv.name)
                # Step 1: Login to EIMS
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
                inv.eims_status = 'pending'
                # Step 2: Prepare invoice payload (request)
                _logger.info("Preparing invoice payload for %s", inv.name)
                request_obj = inv._prepare_eims_payload()['request']
                # Step 3: Canonicalize and sign the request
                canonical = signer.canonicalize_json(request_obj)
                signature = signer.sign_request_sha512(canonical, key_data)
                certificate = signer.encode_certificate(cert_data)
                payload = {
                    'request': request_obj,
                    'signature': signature,
                    'certificate': certificate
                }
                _logger.debug("Final EIMS payload: %s", json.dumps(payload, indent=2))
                # Step 4: Submit invoice to EIMS
                _logger.info("Submitting invoice to EIMS...")
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                response = requests.post(
                    cfg.EIMS_INVOICE_SUBMIT_URL,
                    json=payload,
                    headers=headers,
                    timeout=cfg.EIMS_TIMEOUT,
                    verify=cfg.EIMS_VERIFY_SSL
                )
                _logger.info("EIMS API Response Status: %s", response.status_code)
                _logger.debug("EIMS API Response: %s", response.text)
                if response.status_code == 200:
                    response_data = response.json()
                    _logger.info("Invoice submitted successfully to EIMS")
                    # Extract IRN from response['body']['irn'] if available
                    irn = response_data.get('body', {}).get('irn')
                    if irn:
                        inv.eims_irn = irn
                        _logger.info("EIMS IRN received: %s", inv.eims_irn)
                    inv.eims_status = 'sent'
                    inv.eims_error_message = False
                    _logger.info("EIMS integration completed successfully for invoice %s", inv.name)
                else:
                    _logger.error("EIMS API returned error status: %s - %s", response.status_code, response.text)
                    inv.eims_status = 'error'
                    inv.eims_error_message = response.text
            except requests.exceptions.Timeout:
                _logger.error("EIMS request timed out for invoice %s", inv.name)
                inv.eims_status = 'error'
                inv.eims_error_message = "EIMS request timed out"
            except requests.exceptions.ConnectionError as e:
                _logger.error("EIMS connection error for invoice %s: %s", inv.name, str(e))
                inv.eims_status = 'error'
                inv.eims_error_message = str(e)
            except Exception as e:
                _logger.error("EIMS integration failed for invoice %s: %s", inv.name, str(e))
                inv.eims_status = 'error'
                inv.eims_error_message = str(e)

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
            "HouseNumber": val(seller, 'street2'),
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
            "HouseNumber": val(buyer, 'street2'),
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
