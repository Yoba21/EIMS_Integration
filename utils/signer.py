import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

def canonicalize_json(data: dict) -> bytes:
    """Canonicalize JSON (no whitespace, sorted keys)."""
    return json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')

def sign_request_sha512(canonical_data: bytes, private_key_pem: bytes) -> str:
    """Sign using SHA512withRSA."""
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
        backend=default_backend()
    )
    signature = private_key.sign(
        canonical_data,
        padding.PKCS1v15(),
        hashes.SHA512()
    )
    return base64.b64encode(signature).decode('utf-8')

def encode_certificate(cert_pem: bytes) -> str:
    """Base64 encode the full PEM certificate."""
    return base64.b64encode(cert_pem).decode('utf-8')
