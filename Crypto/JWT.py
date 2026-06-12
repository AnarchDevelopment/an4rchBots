import json
import base64
from .EC import EC_KEY, pub_key_b64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

def b64url(data):
    if isinstance(data, (dict, list)):
        data = json.dumps(data, separators=(',', ':')).encode('utf-8')
    elif isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def der_sig_to_raw(der):
    o = 2
    rl = der[o+1]; o += 2; rr = der[o:o+rl]; o += rl
    sl = der[o+1]; o += 2; sr = der[o:o+sl]
    ra = bytearray(48); sa = bytearray(48)
    rt = rr[1:] if rr[0]==0 else rr
    st = sr[1:] if sr[0]==0 else sr
    ra[48-len(rt):] = rt; sa[48-len(st):] = st
    return bytes(ra) + bytes(sa)

def make_jwt(payload):
    pub = pub_key_b64()
    data = b64url({'alg':'ES384','x5u':pub}) + '.' + b64url(payload)
    if EC_KEY is None:
        return data + '.'
    try:
        der = EC_KEY.sign(data.encode('utf-8'), ec.ECDSA(hashes.SHA384()))
        return data + '.' + base64.urlsafe_b64encode(der_sig_to_raw(der)).rstrip(b'=').decode('utf-8')
    except Exception:
        return data + '.'