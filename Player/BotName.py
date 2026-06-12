import random
import string

CHARS = string.ascii_lowercase + string.digits

def generar_nombre(base):
    return f"{base}_{''.join(random.choices(CHARS, k=6))}"