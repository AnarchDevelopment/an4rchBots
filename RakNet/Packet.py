import struct

MAGIC = bytes([0x00,0xFF,0xFF,0x00,0xFE,0xFE,0xFE,0xFE,0xFD,0xFD,0xFD,0xFD,0x12,0x34,0x56,0x78])
MTU_LIST = [1492, 1464, 1400, 1200, 576]

class W:
    def __init__(self):
        self.parts = []
    def u8(self, v):
        self.parts.append(struct.pack('B', v & 0xFF)); return self
    def u16be(self, v):
        self.parts.append(struct.pack('>H', v & 0xFFFF)); return self
    def i32be(self, v):
        self.parts.append(struct.pack('>i', v)); return self
    def u32be(self, v):
        self.parts.append(struct.pack('>I', v & 0xFFFFFFFF)); return self
    def i32le(self, v):
        self.parts.append(struct.pack('<i', v)); return self
    def i64be(self, v):
        self.parts.append(struct.pack('>q', v)); return self
    def u64be(self, v):
        self.parts.append(struct.pack('>Q', v & 0xFFFFFFFFFFFFFFFF)); return self
    def f32be(self, v):
        self.parts.append(struct.pack('>f', v)); return self
    def t_le(self, v):
        self.parts.append(bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF])); return self
    def raw(self, b):
        self.parts.append(bytes(b)); return self
    def magic(self):
        self.parts.append(MAGIC); return self
    def str_(self, s):
        b = s.encode('utf-8'); self.u16be(len(b)); self.parts.append(b); return self
    def str_raw(self, b):
        b = bytes(b); self.u16be(len(b)); self.parts.append(b); return self
    def rak_ip(self, ip, port):
        self.u8(4)
        for o in ip.split('.'):
            self.u8((~int(o)) & 0xFF)
        self.u16be(port); return self
    def buf(self):
        return b''.join(self.parts)

class R:
    def __init__(self, b):
        self.b = bytes(b)
        self.p = 0
    def left(self):
        return len(self.b) - self.p
    def u8(self):
        v = self.b[self.p]; self.p += 1; return v
    def u16be(self):
        v = struct.unpack_from('>H', self.b, self.p)[0]; self.p += 2; return v
    def i32be(self):
        v = struct.unpack_from('>i', self.b, self.p)[0]; self.p += 4; return v
    def u32be(self):
        v = struct.unpack_from('>I', self.b, self.p)[0]; self.p += 4; return v
    def i64be(self):
        v = struct.unpack_from('>q', self.b, self.p)[0]; self.p += 8; return v
    def u64be(self):
        v = struct.unpack_from('>Q', self.b, self.p)[0]; self.p += 8; return v
    def f32be(self):
        v = struct.unpack_from('>f', self.b, self.p)[0]; self.p += 4; return v
    def t_le(self):
        v = self.b[self.p]|(self.b[self.p+1]<<8)|(self.b[self.p+2]<<16); self.p+=3; return v
    def bytes_(self, n):
        v = self.b[self.p:self.p+n]; self.p += n; return v
    def skip(self, n):
        self.p += n; return self
    def str_(self):
        n = self.u16be()
        return self.bytes_(n).decode('utf-8', errors='replace')