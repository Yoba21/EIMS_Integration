# EIMS Integration for Odoo 18.0

This module integrates Odoo 18.0 with the Ethiopia EIMS (Electronic Invoice Management System) for automatic invoice submission.

## Features

- ✅ Automatic EIMS integration when posting customer invoices
- ✅ Configurable EIMS credentials and endpoints
- ✅ Comprehensive error handling and logging
- ✅ Support for SSL certificates and private keys
- ✅ Real-time status tracking (Pending, Sent, Error)
- ✅ IRN (Invoice Reference Number) storage

## Installation

1. **Copy the module** to your Odoo addons directory:
   ```
   cp -r eims_integration /path/to/odoo/addons/
   ```

2. **Update the addons path** in your Odoo configuration file

3. **Install the module** via Odoo Apps menu or command line:
   ```bash
   python odoo-bin -d your_database -i eims_integration
   ```

## Configuration

### 1. Update EIMS Settings

Edit `utils/config.py` with your EIMS credentials:

```python
# EIMS Authentication Settings
EIMS_CLIENT_ID = "your_client_id"
EIMS_CLIENT_SECRET = "your_client_secret"
EIMS_SYSTEM_NUMBER = "your_system_number"

# EIMS API Endpoints
EIMS_LOGIN_URL = "https://core.mor.gov.et/auth/login?"
EIMS_INVOICE_SUBMIT_URL = "https://core.mor.gov.et/api/v1/invoice/submit"

# Certificate and Key Paths
EIMS_PRIVATE_KEY_PATH = "path/to/your/private_key.key"
EIMS_CERTIFICATE_PATH = "path/to/your/certificate.pem"
```

### 2. Certificate Setup

Ensure your SSL certificates are properly configured:

- **Private Key**: RSA private key file (.key format)
- **Certificate**: X.509 certificate file (.pem format)
- **File Permissions**: Ensure Odoo can read these files

### 3. Test Configuration

Run the test script to verify your setup:

```bash
cd odoo/addons/eims_integration
python test_eims_config.py
```

## Usage

### Automatic Integration

Once configured, the EIMS integration works automatically:

1. **Create a customer invoice** in Odoo
2. **Post the invoice** (click "Post" button)
3. **EIMS integration triggers** automatically
4. **Check the status** in the invoice form

### Manual Testing

You can test the integration manually:

1. Go to **Invoicing > Customer Invoices**
2. Create a new invoice
3. Add products and customer
4. Click **Post**
5. Check the logs for EIMS integration messages

## Monitoring

### Logs

Monitor the integration through Odoo logs:

```bash
tail -f /var/log/odoo/odoo.log | grep EIMS
```

### Status Tracking

Each invoice has EIMS status fields:
- **EIMS Status**: Pending, Sent, or Error
- **EIMS IRN**: Invoice Reference Number from EIMS

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check network connectivity to EIMS servers
   - Verify firewall settings
   - Increase timeout in config.py

2. **Certificate Errors**
   - Verify certificate file paths
   - Check file permissions
   - Ensure certificates are valid

3. **Authentication Failures**
   - Verify client ID and secret
   - Check system number
   - Ensure certificates match EIMS registration

### Debug Mode

Enable debug logging by setting log level to DEBUG in Odoo configuration:

```ini
[options]
log_level = debug
```

## API Reference

### EIMS Payload Structure

The module generates EIMS-compliant JSON payloads:

```json
{
  "request": {
    "TransactionType": "B2B",
    "DocumentDetails": {
      "DocumentNumber": "INV/2025/00001",
      "Date": "2025-06-12T10:00:00+03:00",
      "Type": "INV"
    },
    "SellerDetails": {
      "TIN": "123456789",
      "LegalName": "Your Company",
      "City": "Addis Ababa",
      "Region": "11",
      "Wereda": "01"
    },
    "BuyerDetails": {
      "LegalName": "Customer Name",
      "Region": "11",
      "Wereda": "01"
    },
    "ItemList": [...],
    "ValueDetails": {...},
    "PaymentDetails": {...},
    "SourceSystem": {...}
  },
  "signature": "",
  "certificate": ""
}
```

## Support

For issues and questions:

1. Check the logs for detailed error messages
2. Verify your EIMS credentials and certificates
3. Test with the provided test script
4. Contact your EIMS administrator for API access

## Version History

- **v1.0.0**: Initial release with basic EIMS integration
- **v1.1.0**: Added configuration file and improved error handling
- **v1.2.0**: Added comprehensive logging and status tracking

## License

This module is licensed under LGPL-3.0. 