import json
import base64
import requests
import logging
from .signer import canonicalize_json, sign_request_sha512, encode_certificate

_logger = logging.getLogger(__name__)

def eims_login(client_id, client_secret, apikey, tin, private_key_path, certificate_path, login_url, timeout=30, verify_ssl=True):
    """
    Authenticate with EIMS system and return access token.
    
    Signs the request with the private key and includes the certificate.
    """
    try:
        _logger.info("Preparing EIMS login request...")

        # Load private key
        _logger.debug("Loading private key from: %s", private_key_path)
        with open(private_key_path, "rb") as pk_file:
            private_key = pk_file.read()
        
        # Load certificate
        _logger.debug("Loading certificate from: %s", certificate_path)
        with open(certificate_path, "rb") as cert_file:
            certificate = cert_file.read()
        
        # Prepare request object
        request_obj = {
            "clientId": client_id,
            "clientSecret": client_secret,
            "apikey": apikey,
            "tin": tin
        }
        _logger.info("Login request object prepared")

        # Canonicalize and sign
        canonical = canonicalize_json(request_obj)
        signature = sign_request_sha512(canonical, private_key)
        cert_encoded = encode_certificate(certificate)
        
        # Full payload
        full_payload = {
            "request": request_obj,
            "signature": signature,
            "certificate": cert_encoded
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        _logger.info("Sending EIMS login request to: %s", login_url)
        response = requests.post(
            login_url,
            headers=headers,
            json=full_payload,  # send the signed payload
            timeout=timeout,
            verify=verify_ssl
        )

        _logger.info("EIMS login response status: %s", response.status_code)
        _logger.debug("EIMS login response: %s", response.text)

        if response.status_code == 200:
            response_data = response.json()
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
