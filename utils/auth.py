import json
import base64
import requests
import logging
from .signer import canonicalize_json, sign_request_sha512, encode_certificate
from .config import EIMS_API_KEY, EIMS_TIN
from urllib.parse import urlencode

_logger = logging.getLogger(__name__)

def eims_login(client_id, client_secret, apikey, tin, private_key_path, certificate_path, login_url, timeout=30):
    """
    Authenticate with EIMS system and return access token
    
    Args:
        client_id: EIMS client ID
        client_secret: EIMS client secret
        apikey: EIMS API key
        tin: EIMS TIN
        private_key_path: Path to private key file
        certificate_path: Path to certificate file
        login_url: EIMS login URL
        timeout: Request timeout in seconds (default: 30)
    
    Returns:
        str: Access token from EIMS
    """
    try:
        _logger.info("Preparing EIMS login request...")
        
        # Build query parameters (note: 'sellerTin' in query, 'tin' in body)
        params = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "apikey": apikey,
            "sellerTin": tin
        }
        url_with_params = f"{login_url}?{urlencode(params)}"

        # Prepare JSON body (camelCase, 'tin' in body)
        request_obj = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "apikey": apikey,
            "tin": tin
        }
        _logger.info("Login payload: %s", json.dumps(request_obj))

        _logger.debug("Loading private key from: %s", private_key_path)
        # Load keys
        with open(private_key_path, "rb") as pk_file:
            private_key = pk_file.read()
            
        _logger.debug("Loading certificate from: %s", certificate_path)
        with open(certificate_path, "rb") as cert_file:
            certificate = cert_file.read()

        # Canonicalize & Sign
        _logger.debug("Canonicalizing and signing request...")
        canonical = canonicalize_json(request_obj)
        signature = sign_request_sha512(canonical, private_key)
        cert_encoded = encode_certificate(certificate)

        # Prepare full request payload
        full_payload = {
            "request": request_obj,
            "signature": signature,
            "certificate": cert_encoded
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        _logger.info("Sending EIMS login request to: %s", url_with_params)
        response = requests.post(
            url_with_params,
            headers=headers,
            json=request_obj,
            timeout=timeout,
            verify=False  # HTTP, so SSL verify off
        )

        _logger.info("EIMS login response status: %s", response.status_code)
        _logger.debug("EIMS login response: %s", response.text)

        if response.status_code == 200:
            response_data = response.json()
            
            # Extract access token from data.accessToken
            if 'data' in response_data and 'accessToken' in response_data['data']:
                access_token = response_data['data']['accessToken']
                _logger.info("EIMS login successful, access token retrieved")
                return access_token
            else:
                _logger.error("EIMS login response missing data.accessToken: %s", response_data)
                raise Exception(f"EIMS login response missing data.accessToken: {response_data}")
        else:
            _logger.error("EIMS login failed with status %s: %s", response.status_code, response.text)
            raise Exception(f"EIMS login failed: {response.status_code} {response.text}")
            
    except requests.exceptions.Timeout:
        _logger.error("EIMS login request timed out after %s seconds", timeout)
        raise Exception(f"EIMS login request timed out after {timeout} seconds")
    except requests.exceptions.ConnectionError as e:
        _logger.error("EIMS login connection error: %s", str(e))
        raise Exception(f"EIMS login connection error: {str(e)}")
    except FileNotFoundError as e:
        _logger.error("Certificate or key file not found: %s", str(e))
        raise Exception(f"Certificate or key file not found: {str(e)}")
    except Exception as e:
        _logger.error("EIMS login failed: %s", str(e))
        raise Exception(f"EIMS login failed: {str(e)}")
