import zlib
import struct
from .Packet import W

P70 = {
    'LOGIN': 0x8f, 'PLAY_STATUS': 0x90, 'DISCONNECT': 0x91,
    'BATCH': 0x92, 'TEXT': 0x93, 'START_GAME': 0x95,
    'MOVE_PLAYER': 0x9d, 'CHUNK_RADIUS': 0xc9
}
P84 = {
    'LOGIN': 0x01, 'PLAY_STATUS': 0x02, 'DISCONNECT': 0x05,
    'TEXT': 0x09, 'START_GAME': 0x0b, 'MOVE_PLAYER': 0x13,
    'CHUNK_RADIUS': 0x3d
}

def build_batch(pkts, bot):
    inner = b''.join(struct.pack('>I', len(p)) + p for p in pkts)
    comp = zlib.compress(inner, level=7)
    if bot['proto'] >= 84:
        return bytes([0xfe, 0x06]) + W().i32be(len(comp)).raw(comp).buf()
    return W().u8(P70['BATCH']).i32be(len(comp)).raw(comp).buf()