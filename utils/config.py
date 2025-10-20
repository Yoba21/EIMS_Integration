"""
EIMS Integration Configuration
Update these settings to match your EIMS environment
"""

# EIMS Authentication Settings
EIMS_CLIENT_ID = "602016be-089c-4914-a70b-c389993810e3"
EIMS_CLIENT_SECRET = "038b0ec3-3a4f-4d22-9ba6-f9489882ea67"
EIMS_SYSTEM_NUMBER = "2E852D2AD8"
EIMS_API_KEY = "7ed5f7a2-4290-4db0-93f1-fa5376869f51"
EIMS_TIN = "0062192232"

# EIMS API Endpoints
EIMS_LOGIN_URL = "https://core.mor.gov.et/auth/login"
EIMS_INVOICE_SUBMIT_URL = "https://core.mor.gov.et/v1/register"

# Certificate and Key Paths
EIMS_PRIVATE_KEY_PATH = "C:/Users/Lenovo/Desktop/POS Integration/private_key.key"
EIMS_CERTIFICATE_PATH = "C:/Users/Lenovo/Desktop/POS Integration/0062192232.pem"

# Request Settings
EIMS_TIMEOUT = 30  # seconds
EIMS_VERIFY_SSL = True

# Company Default Settings (can be overridden per company)
DEFAULT_REGION = "11"
DEFAULT_WEREDA = "01"
DEFAULT_SYSTEM_TYPE = "POS"
DEFAULT_SYSTEM_NUMBER = "ODOO18"

# Invoice Settings
DEFAULT_TRANSACTION_TYPE = "B2B"
DEFAULT_DOCUMENT_TYPE = "INV"
DEFAULT_PAYMENT_TERM = "IMMEDIATE"
DEFAULT_PAYMENT_MODE = "Cash"
DEFAULT_NATURE_OF_SUPPLY = "GOODS"
DEFAULT_TAX_CODE = "VAT" 