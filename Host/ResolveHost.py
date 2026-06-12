import socket
import sys

# Reutilizamos los códigos de color desde main (pero aquí no es necesario)
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_RESET = "\033[0m"

def resolver_host(host):
    try:
        socket.inet_aton(host)
        return host
    except socket.error:
        try:
            ip = socket.gethostbyname(host)
            print(f"{C_BLUE}[Info]{C_RESET} Host '{C_YELLOW}{host}{C_RESET}' resuelto a '{C_GREEN}{ip}{C_RESET}'")
            return ip
        except socket.gaierror as e:
            print(f"{C_RED}[Error] No se pudo resolver el host '{host}': {e}{C_RESET}")
            sys.exit(1)