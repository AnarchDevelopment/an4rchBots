from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

try:
    EC_KEY = ec.generate_private_key(ec.SECP384R1(), default_backend())
except Exception:
    EC_KEY = None

def pub_key_b64():
    if EC_KEY is None:
        return 'AAAA'
    return base64.b64encode(EC_KEY.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )).decode('utf-8')