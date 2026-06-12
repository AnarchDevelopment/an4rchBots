import random
import base64

def generate_random_skin():
    buf = bytearray(64 * 32 * 4)

    def fill(x0, y0, x1, y1, r, g, b, a=255):
        for y in range(y0, y1):
            for x in range(x0, x1):
                i = (y * 64 + x) * 4
                buf[i] = r; buf[i+1] = g; buf[i+2] = b; buf[i+3] = a

    SK = (random.randint(120, 240), random.randint(90, 180), random.randint(50, 130))
    HR = (random.randint(20, 150), random.randint(20, 100), random.randint(10, 80))
    SH = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    PT = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    BT = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    fill(8,  0, 16,  8, *HR); fill(16, 0, 24,  8, *SK)
    fill( 0, 8,  8, 16, *SK); fill( 8, 8, 16, 16, *SK)
    fill(16, 8, 24, 16, *HR); fill(24, 8, 32, 16, *HR)
    fill(8, 0, 16, 4, *HR)
    
    eye_r, eye_g, eye_b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    fill( 9, 9, 11, 11, 255, 255, 255)
    buf[(9+10*64)*4] = eye_r; buf[(9+10*64)*4+1] = eye_g; buf[(9+10*64)*4+2] = eye_b
    fill(13, 9, 15, 11, 255, 255, 255)
    buf[(14+10*64)*4] = eye_r; buf[(14+10*64)*4+1] = eye_g; buf[(14+10*64)*4+2] = eye_b
    
    fill(11, 11, 13, 12, *SK)
    fill(10, 13, 14, 14, 140, 60, 20)
    fill(20, 16, 28, 20, *SH); fill(28, 16, 36, 20, *SH)
    fill(16, 20, 20, 32, *SH); fill(20, 20, 28, 32, *SH)
    fill(28, 20, 32, 32, *SH); fill(32, 20, 40, 32, *SH)
    fill(23, 20, 25, 32, (SH[0]+50)%256, (SH[1]+50)%256, (SH[2]+50)%256)
    fill(44, 16, 48, 20, *SK); fill(48, 16, 52, 20, *SK)
    fill(40, 20, 44, 32, *SK); fill(44, 20, 48, 32, *SK)
    fill(48, 20, 52, 32, *SK); fill(52, 20, 56, 32, *SK)
    fill(44, 20, 48, 24, *SH); fill(40, 20, 44, 24, *SH)
    fill(48, 20, 52, 24, *SH); fill(52, 20, 56, 24, *SH)
    fill( 4, 16,  8, 20, *PT); fill( 8, 16, 12, 20, *PT)
    fill( 0, 20,  4, 32, *PT); fill( 4, 20,  8, 32, *PT)
    fill( 8, 20, 12, 32, *PT); fill(12, 20, 16, 32, *PT)
    fill( 0, 28,  4, 32, *BT); fill( 4, 28,  8, 32, *BT)
    fill( 8, 28, 12, 32, *BT); fill(12, 28, 16, 32, *BT)

    return base64.b64encode(bytes(buf)).decode('utf-8')