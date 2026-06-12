# Variables globales compartidas
import threading

bots_conectados = 0
bots_activos = []  # lista de objetos Bot
lock_global = threading.Lock()
tiempo_terminado = False