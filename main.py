#!/usr/bin/env python3
import sys
import os
import random
import socket
import time
import threading
import signal
import string
import struct
from Host.ResolveHost import resolver_host
from Player.BotName import generar_nombre
from Player.Skin import generate_random_skin
from Connection.SpawnBot import conectar_bot
import state

# Colores ANSI
if os.name == 'nt':
    os.system('')
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_RED     = "\033[91m"
C_GREEN   = "\033[92m"
C_YELLOW  = "\033[93m"
C_BLUE    = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN    = "\033[96m"
C_WHITE   = "\033[97m"

def check_server_status(ip, port, timeout=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    ping_time = int(time.time() * 1000)
    client_guid = random.randint(100000, 999999)
    from RakNet.Packet import W, MAGIC
    w = W().u8(0x01).i64be(ping_time).magic().i64be(client_guid)
    try:
        sock.sendto(w.buf(), (ip, port))
        data, addr = sock.recvfrom(2048)
        if data and data[0] == 0x1c:
            from RakNet.Packet import R
            r = R(data)
            r.skip(1)
            r.skip(8)
            r.skip(8)
            r.skip(16)
            motd_raw = r.str_()
            parts = motd_raw.split(';')
            motd = parts[1] if len(parts) > 1 else motd_raw
            return True, motd
    except Exception:
        pass
    finally:
        sock.close()
    return False, ""

def on_bot_spawn():
    with state.lock_global:
        state.bots_conectados += 1
    print(f"{C_GREEN}[Sistema] Bots spawneados: {state.bots_conectados}/{len(state.bots_activos)}{C_RESET}")

def manager_loop():
    last_ping = time.time()
    bot_last_action = {}
    while not state.tiempo_terminado:
        now = time.time()
        do_ping = (now - last_ping >= 4.0)
        if do_ping:
            last_ping = now
        with state.lock_global:
            bots_list = list(state.bots_activos)
        for bot in bots_list:
            if bot['is_closing']:
                print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_YELLOW}Conexión cerrada. Reconectando en 5 segundos...{C_RESET}")
                try:
                    bot['sock'].close()
                except Exception:
                    pass
                bot['is_closing'] = False
                bot['state'] = 'DISCONNECTED'
                bot_last_action[bot['nombre']] = now
                def reconnect_task(b=bot):
                    time.sleep(5)
                    if not state.tiempo_terminado:
                        conectar_bot(b, on_bot_spawn)
                threading.Thread(target=reconnect_task, daemon=True).start()
                continue
            if bot['state'] == 'CONNECTED' and do_ping:
                try:
                    from RakNet.RakNet import send_reliable_ordered
                    payload = bytes([0x00]) + struct.pack('>q', int(time.time() * 1000))
                    send_reliable_ordered(bot, payload)
                except Exception:
                    pass
            if bot['state'] != 'CONNECTED':
                last_time = bot_last_action.get(bot['nombre'], now)
                if now - last_time > 12.0:
                    print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_RED}Tiempo de conexión agotado.{C_RESET}")
                    bot['is_closing'] = True
                    bot_last_action[bot['nombre']] = now
            else:
                bot_last_action[bot['nombre']] = now
        time.sleep(1.0)

def mostrar_tabla_status():
    with state.lock_global:
        bots_list = list(state.bots_activos)
    print(f"\n{C_BLUE}┌─────────────────┬───────────┬───────────────┬───────────┬────────────┬────────────┐{C_RESET}")
    print(f"{C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}{'Nombre':<15}{C_RESET} {C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}{'Protocolo':<9}{C_RESET} {C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}{'Estado':<13}{C_RESET} {C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}{'Spawned':<9}{C_RESET} {C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}{'Enviados':<10}{C_RESET} {C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}{'Recibidos':<10}{C_RESET} {C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}├─────────────────┼───────────┼───────────────┼───────────┼────────────┼────────────┤{C_RESET}")
    for bot in bots_list:
        status_str = bot['state']
        if status_str == 'CONNECTED':
            status_color = C_GREEN
        elif status_str == 'DISCONNECTED':
            status_color = C_RED
        else:
            status_color = C_YELLOW
        state_padded = f"{status_str:<13}"
        state_colored = f"{status_color}{state_padded}{C_RESET}"
        spawn_text = "Si" if bot['spawned'] else "No"
        spawn_padded = f"{spawn_text:<9}"
        spawn_colored = spawn_padded.replace("Si", f"{C_GREEN}Si{C_RESET}").replace("No", f"{C_RED}No{C_RESET}")
        name = bot['nombre'][:15]
        proto = str(bot['proto'])
        sent = str(bot['packets_sent'])
        rcvd = str(bot['packets_received'])
        print(f"{C_BLUE}│{C_RESET} {C_CYAN}{name:<15}{C_RESET} {C_BLUE}│{C_RESET} {proto:<9} {C_BLUE}│{C_RESET} {state_colored} {C_BLUE}│{C_RESET} {spawn_colored} {C_BLUE}│{C_RESET} {sent:<10} {C_BLUE}│{C_RESET} {rcvd:<10} {C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}└─────────────────┴───────────┴───────────────┴───────────┴────────────┴────────────┘{C_RESET}\n")

def interpretador_comandos():
    time.sleep(1.5)
    print(f"\n{C_YELLOW}[Consola]{C_RESET} Escribe '{C_GREEN}help{C_RESET}' para ver la lista de comandos.")
    while not state.tiempo_terminado:
        try:
            line = input().strip()
            if not line:
                continue
            parts = line.split(' ', 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ''
            if cmd == 'exit':
                print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_RED}Deteniendo todos los bots...{C_RESET}")
                state.tiempo_terminado = True
                break
            elif cmd == 'help':
                print(f"\n{C_BLUE}══════════════════════════════════════════════════════════════════════════{C_RESET}")
                print(f" {C_BOLD}{C_WHITE}COMANDOS DISPONIBLES{C_RESET}")
                print(f"{C_BLUE}══════════════════════════════════════════════════════════════════════════{C_RESET}")
                print(f"  {C_CYAN}status{C_RESET}          - Muestra la tabla detallada con el estado de los bots")
                print(f"  {C_CYAN}say <mensaje>{C_RESET}   - Envía un mensaje o comando desde todos los bots")
                print(f"  {C_CYAN}move{C_RESET}            - Alterna el movimiento automático de los bots")
                print(f"  {C_CYAN}jump{C_RESET}            - Hace que todos los bots den un salto")
                print(f"  {C_CYAN}autojump{C_RESET}        - Alterna los saltos aleatorios de los bots")
                print(f"  {C_CYAN}spam{C_RESET}            - Alterna el spam de mensajes predefinidos")
                print(f"  {C_CYAN}tp <x> <y> <z>{C_RESET}    - Teletransporta a todos los bots a la posición dada")
                print(f"  {C_CYAN}distribute{C_RESET}      - Esparce los bots aleatoriamente a su alrededor")
                print(f"  {C_CYAN}reconnect{C_RESET}       - Fuerza la reconexión de todos los bots")
                print(f"  {C_CYAN}info{C_RESET}            - Muestra la información de conexión actual")
                print(f"  {C_CYAN}exit{C_RESET}            - Cierra el programa y detiene todos los bots")
                print(f"{C_BLUE}══════════════════════════════════════════════════════════════════════════{C_RESET}\n")
            elif cmd == 'status':
                mostrar_tabla_status()
            elif cmd == 'say':
                if not args:
                    print(f"{C_RED}[Consola] Uso: say <mensaje>{C_RESET}")
                    continue
                msg_to_send = args.replace('-', ' ')
                sent_count = 0
                with state.lock_global:
                    for bot in state.bots_activos:
                        if bot['state'] == 'CONNECTED' and bot['spawned']:
                            from Connection.SpawnBot import send_game, build_chat
                            send_game(bot, build_chat(bot, bot['ids'], msg_to_send))
                            sent_count += 1
                print(f"{C_GREEN}[Consola] Mensaje/comando enviado por {sent_count} bots.{C_RESET}")
            elif cmd == 'move':
                with state.lock_global:
                    for bot in state.bots_activos:
                        if bot['move_active']:
                            bot['move_active'] = False
                            print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_YELLOW}Movimiento apagado.{C_RESET}")
                        else:
                            from Connection.SpawnBot import start_movement
                            start_movement(bot)
                            print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_GREEN}Movimiento encendido.{C_RESET}")
            elif cmd == 'reconnect':
                print(f"{C_YELLOW}[Consola] Forzando reconexión...{C_RESET}")
                with state.lock_global:
                    for bot in state.bots_activos:
                        bot['is_closing'] = True
            elif cmd == 'jump':
                count = 0
                with state.lock_global:
                    for bot in state.bots_activos:
                        if bot['state'] == 'CONNECTED' and bot['move_active']:
                            bot['jump_pending'] = True
                            count += 1
                if count > 0:
                    print(f"{C_GREEN}[Consola] Salto forzado para {count} bots activos.{C_RESET}")
                else:
                    print(f"{C_RED}[Consola] No hay bots en movimiento activo para saltar.{C_RESET}")
            elif cmd == 'autojump':
                with state.lock_global:
                    if len(state.bots_activos) == 0:
                        print(f"{C_RED}[Consola] No hay bots cargados.{C_RESET}")
                        continue
                    current_autojump = state.bots_activos[0]['autojump']
                    new_autojump = not current_autojump
                    for bot in state.bots_activos:
                        bot['autojump'] = new_autojump
                state_str = f"{C_GREEN}activado{C_RESET}" if new_autojump else f"{C_RED}desactivado{C_RESET}"
                print(f"{C_GREEN}[Consola] Saltos aleatorios {state_str} para todos los bots.{C_RESET}")
            elif cmd == 'spam':
                with state.lock_global:
                    if len(state.bots_activos) == 0:
                        print(f"{C_RED}[Consola] No hay bots cargados.{C_RESET}")
                        continue
                    any_spam_active = any(b['spam_active'] for b in state.bots_activos)
                    for bot in state.bots_activos:
                        if any_spam_active:
                            bot['spam_active'] = False
                        else:
                            from Connection.SpawnBot import start_spam
                            start_spam(bot)
                state_str = f"{C_RED}detenido{C_RESET}" if any_spam_active else f"{C_GREEN}activado{C_RESET}"
                print(f"{C_GREEN}[Consola] Spam de chat {state_str} para todos los bots.{C_RESET}")
            elif cmd in ('tp', 'teleport'):
                if not args:
                    print(f"{C_RED}[Consola] Uso: tp <x> <y> <z>{C_RESET}")
                    continue
                try:
                    coords = [float(c) for c in args.split()]
                    if len(coords) != 3:
                        raise ValueError()
                    tx, ty, tz = coords
                except ValueError:
                    print(f"{C_RED}[Consola] Coordenadas invalidas. Deben ser 3 numeros separados por espacios.{C_RESET}")
                    continue
                with state.lock_global:
                    count = 0
                    for bot in state.bots_activos:
                        if bot['state'] == 'CONNECTED':
                            bot['pos']['x'] = tx
                            bot['pos']['y'] = ty
                            bot['pos']['z'] = tz
                            bot['origin_pos'] = {'x': tx, 'y': ty, 'z': tz}
                            from Connection.SpawnBot import send_game, build_move_player
                            send_game(bot, build_move_player(bot, bot['ids']))
                            count += 1
                print(f"{C_GREEN}[Consola] Teletransportados {count} bots a ({tx:.1f}, {ty:.1f}, {tz:.1f}).{C_RESET}")
            elif cmd == 'distribute':
                with state.lock_global:
                    count = 0
                    for bot in state.bots_activos:
                        if bot['state'] == 'CONNECTED':
                            rx = random.uniform(-5, 5)
                            rz = random.uniform(-5, 5)
                            bot['pos']['x'] += rx
                            bot['pos']['z'] += rz
                            bot['origin_pos']['x'] = bot['pos']['x']
                            bot['origin_pos']['z'] = bot['pos']['z']
                            from Connection.SpawnBot import send_game, build_move_player
                            send_game(bot, build_move_player(bot, bot['ids']))
                            count += 1
                print(f"{C_GREEN}[Consola] Distribuidos {count} bots aleatoriamente a su alrededor.{C_RESET}")
            elif cmd == 'info':
                with state.lock_global:
                    total = len(state.bots_activos)
                    con = sum(1 for b in state.bots_activos if b['state'] == 'CONNECTED')
                    spwn = sum(1 for b in state.bots_activos if b['spawned'])
                print(f"\n{C_BLUE}┌────────────────────────────────────────────────────────┐{C_RESET}")
                print(f"{C_BLUE}│{C_RESET} {C_BOLD}{C_WHITE}INFORMACION DE LA SESION{C_RESET}                              {C_BLUE}│{C_RESET}")
                print(f"{C_BLUE}├────────────────────────────────────────────────────────┤{C_RESET}")
                print(f"{C_BLUE}│{C_RESET} Servidor: {C_GREEN}{HOST}:{PORT:<35}{C_RESET} {C_BLUE}│{C_RESET}")
                print(f"{C_BLUE}│{C_RESET} Protocolo: {C_YELLOW}{PROTO:<43}{C_RESET} {C_BLUE}│{C_RESET}")
                print(f"{C_BLUE}│{C_RESET} Bots Creados: {C_CYAN}{total:<41}{C_RESET} {C_BLUE}│{C_RESET}")
                print(f"{C_BLUE}│{C_RESET} Conectados: {C_GREEN}{con:<43}{C_RESET} {C_BLUE}│{C_RESET}")
                print(f"{C_BLUE}│{C_RESET} Spawneados: {C_GREEN}{spwn:<43}{C_RESET} {C_BLUE}│{C_RESET}")
                print(f"{C_BLUE}└────────────────────────────────────────────────────────┘{C_RESET}\n")
            else:
                print(f"{C_RED}[Consola] Comando no reconocido: '{cmd}'. Escribe 'help'.{C_RESET}")
        except (KeyboardInterrupt, EOFError):
            state.tiempo_terminado = True
            break

def main():
    global HOST, PORT, PROTO, REGISTER_CMD, MENSAJES, MSG_INTERVALO
    if len(sys.argv) < 6:
        file_name = os.path.basename(__file__)
        print(f"Uso: python {file_name} <ip> <port> <nombre> <bots> <tiempo> [protocol] [register] [mensajes] [intervalo]")
        sys.exit(1)
    ARG_HOST = sys.argv[1]
    PORT = int(sys.argv[2])
    NOMBRE = sys.argv[3]
    BOTS = int(sys.argv[4])
    TIEMPO = int(sys.argv[5])
    PROTO = 84
    REGISTER_CMD = ''
    MENSAJES_RAW = 'Hola!'
    MSG_INTERVALO = 5
    if len(sys.argv) > 6:
        if sys.argv[6] in ('70', '84'):
            PROTO = int(sys.argv[6])
            REGISTER_CMD = sys.argv[7] if len(sys.argv) > 7 else ''
            MENSAJES_RAW = sys.argv[8] if len(sys.argv) > 8 else 'Hola!'
            MSG_INTERVALO = int(sys.argv[9]) if len(sys.argv) > 9 else 5
        else:
            REGISTER_CMD = sys.argv[6]
            MENSAJES_RAW = sys.argv[7] if len(sys.argv) > 7 else 'Hola!'
            MSG_INTERVALO = int(sys.argv[8]) if len(sys.argv) > 8 else 5
    MENSAJES = [m.strip().replace('-', ' ') for m in MENSAJES_RAW.split('|') if m.strip()]
    HOST = resolver_host(ARG_HOST)
    active, motd = check_server_status(HOST, PORT)
    if active:
        print(f"{C_BLUE}[Info]{C_RESET} El servidor {C_GREEN}{HOST}:{PORT}{C_RESET} | {C_YELLOW}{motd}{C_RESET} esta activo\n")
    else:
        print(f"{C_RED}[Error] El servidor marcado ({HOST}:{PORT}) no esta activo.{C_RESET}")
        sys.exit(1)
    print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Servidor  : {C_GREEN}{HOST}:{PORT}{C_RESET}")
    print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Bots      : {C_GREEN}{BOTS}  nombre base: \"{NOMBRE}\"{C_RESET}")
    print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Protocolo : {C_GREEN}{PROTO} (MCPE 0.15.x){C_RESET}")
    if TIEMPO > 0:
        print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Tiempo    : {C_GREEN}{TIEMPO}s{C_RESET}")
    else:
        print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Tiempo    : {C_GREEN}ilimitado (escribe 'exit' para parar){C_RESET}")
    register_desc = ''
    if not REGISTER_CMD:
        register_desc = '(sin registro)'
    elif REGISTER_CMD.startswith('/'):
        register_desc = f'{REGISTER_CMD} <pass_aleatoria>'
    else:
        register_desc = f'"{REGISTER_CMD}" (contraseña fija)'
    print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Registro  : {C_GREEN}{register_desc}{C_RESET}")
    print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Mensajes  : {C_GREEN}{' | '.join(MENSAJES)}  cada {MSG_INTERVALO}s{C_RESET}\n")
    def signal_handler(sig, frame):
        state.tiempo_terminado = True
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    for i in range(BOTS):
        bot_nombre = generar_nombre(NOMBRE)
        from RakNet.Protocol import P70, P84
        ids = {'move': P70['MOVE_PLAYER'], 'text': P70['TEXT'], 'chunk': P70['CHUNK_RADIUS']} if PROTO < 84 else {'move': P84['MOVE_PLAYER'], 'text': P84['TEXT'], 'chunk': P84['CHUNK_RADIUS']}
        bot = {
            'nombre': bot_nombre,
            'client_id': random.randint(100000000, 999999999),
            'client_guid': random.randint(100000000, 999999999),
            'proto': PROTO,
            'host': HOST,
            'port': PORT,
            'register_cmd': REGISTER_CMD,
            'random_pass': ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)),
            'mensajes': MENSAJES,
            'msg_interval': MSG_INTERVALO,
            'ids': ids,
            'sock': None,
            'state': 'DISCONNECTED',
            'mtu_size': 1464,
            'current_mtu': 1464,
            'server_guid': 0,
            'send_seq': 0,
            'msg_index': 0,
            'order_index': 0,
            'split_id': 0,
            'sent_frames': {},
            'split_reconstruction': {},
            'pos': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'yaw': 0.0, 'pitch': 0.0},
            'origin_pos': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'entity_id': 0,
            'spawned': False,
            'register_sent': False,
            'spam_active': False,
            'spam_idx': 0,
            'move_active': False,
            'is_closing': False,
            'packets_sent': 0,
            'packets_received': 0,
            'skin_data': generate_random_skin(),
            'jump_pending': False,
            'autojump': False,
            'tiempo_terminado': state.tiempo_terminado  # referencia
        }
        with state.lock_global:
            state.bots_activos.append(bot)
        conectar_bot(bot, on_bot_spawn)
        time.sleep(0.3)
    threading.Thread(target=manager_loop, daemon=True).start()
    if TIEMPO > 0:
        def timer_thread():
            time.sleep(TIEMPO)
            print(f"\n{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_RED}Tiempo expirado ({TIEMPO}s). Deteniendo bots...{C_RESET}")
            state.tiempo_terminado = True
        threading.Thread(target=timer_thread, daemon=True).start()
    interpretador_comandos()
    with state.lock_global:
        for bot in state.bots_activos:
            try:
                bot['sock'].close()
            except Exception:
                pass
    print(f"{C_BLUE}{C_BOLD}[an4rchDevelopment]{C_RESET} {C_WHITE}Saliendo del programa.{C_RESET}")

if __name__ == '__main__':
    main()