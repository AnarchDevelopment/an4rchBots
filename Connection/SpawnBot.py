import time
import threading
import random
import math
import zlib
import json
import os
import struct
import socket
from Crypto.JWT import make_jwt
from Crypto.EC import pub_key_b64
from RakNet.Packet import W, R
from RakNet.RakNet import (
    send_open_connection_request_1, send_open_connection_request_2,
    send_connection_request, send_new_incoming_connection,
    send_reliable_ordered, handle_nack, send_ack, _udp_send
)
from RakNet.Protocol import P70, P84, build_batch

# Constantes de movimiento
MOVE_TICK_S = 0.1
MOVE_CHANGE_S = 3.0
MOVE_STEP = 0.28
MOVE_RANGE = 22
GRAVITY_RATE = 0.12

def build_login84(bot):
    pub = pub_key_b64()
    uuid = '00000000-0000-4000-8000-' + os.urandom(6).hex()
    now = int(time.time())
    chain = make_jwt({
        'extraData': {
            'displayName': bot['nombre'],
            'identity': uuid,
            'XUID': ''
        },
        'identityPublicKey': pub,
        'nbf': now - 60,
        'exp': now + 86400
    })
    skin = make_jwt({
        'ClientRandomId': bot['client_id'] & 0xFFFFFFFF,
        'ServerAddress': f"{bot['host']}:{bot['port']}",
        'SkinData': bot['skin_data'],
        'SkinId': 'Standard_Custom',
        'CapeData': '',
        'SkinGeometryName': 'geometry.humanoid.custom',
        'SkinGeometry': '',
        'DeviceOS': 1,
        'GameVersion': '0.15.10'
    })
    cb = json.dumps({'chain': [chain]}).encode('utf-8')
    sb = skin.encode('utf-8')
    raw = W().i32le(len(cb)).raw(cb).i32le(len(sb)).raw(sb).buf()
    comp = zlib.compress(raw, level=7)
    return bytes([0xfe, 0x01]) + W().i32be(84).i32be(len(comp)).raw(comp).buf()

def build_login70(bot):
    skin_buf = base64.b64decode(bot['skin_data'])
    return (W().u8(P70['LOGIN']).str_(bot['nombre']).i32be(70).i32be(70)
            .u64be(bot['client_id']).raw(os.urandom(16))
            .str_(f"{bot['host']}:{bot['port']}").str_('').str_('Standard_Custom')
            .str_raw(skin_buf).u8(0).buf())

def build_chunk_radius(bot, ids):
    return W().u8(ids['chunk']).i32be(8).buf()

def build_move_player(bot, ids):
    p = bot['pos']
    return (W().u8(ids['move']).i64be(bot['entity_id'])
            .f32be(p['x']).f32be(p['y']).f32be(p['z'])
            .f32be(p['yaw']).f32be(p['yaw']).f32be(p['pitch'])
            .u8(0).u8(1).buf())

def build_chat(bot, ids, msg):
    return W().u8(ids['text']).u8(1).str_(bot['nombre']).str_(msg).buf()

def send_game(bot, pkt):
    if bot['sock'] is None or bot['is_closing'] or bot.get('tiempo_terminado', False):
        return
    send_reliable_ordered(bot, build_batch([pkt], bot))

def send_register(bot):
    if bot['register_sent'] or not bot['register_cmd']:
        return
    bot['register_sent'] = True
    if bot['register_cmd'].startswith('/'):
        msg = f"{bot['register_cmd']} {bot['random_pass']}"
    else:
        msg = bot['register_cmd']

    def enviar(n):
        if bot['is_closing'] or bot.get('tiempo_terminado', False):
            return
        send_game(bot, build_chat(bot, bot['ids'], msg))
        print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_YELLOW}Registro #{n} -> \"{msg}\"{C_RESET}")

    enviar(1)
    threading.Timer(0.8, lambda: enviar(2)).start()
    threading.Timer(2.0, lambda: enviar(3)).start()

def start_spam(bot):
    if bot['spam_active'] or bot['is_closing']:
        return
    bot['spam_active'] = True
    bot['spam_idx'] = 0
    def loop():
        time.sleep(bot['msg_interval'])
        while bot['spam_active'] and not bot['is_closing'] and not bot.get('tiempo_terminado', False):
            if not bot['spawned']:
                time.sleep(1)
                continue
            msg = bot['mensajes'][bot['spam_idx'] % len(bot['mensajes'])]
            bot['spam_idx'] += 1
            send_game(bot, build_chat(bot, bot['ids'], msg))
            print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_MAGENTA}Spam -> \"{msg}\"{C_RESET}")
            time.sleep(bot['msg_interval'])
        bot['spam_active'] = False
    threading.Thread(target=loop, daemon=True).start()

def start_movement(bot):
    if bot['move_active'] or bot['is_closing']:
        return
    bot['move_active'] = True
    st = {
        'dir': random.random() * math.pi * 2,
        'spd': MOVE_STEP,
        'velY': 0.0,
        'last_dir': time.time()
    }
    def loop():
        while bot['move_active'] and not bot['is_closing'] and not bot.get('tiempo_terminado', False):
            now = time.time()
            if now - st['last_dir'] >= MOVE_CHANGE_S:
                st['dir'] = random.random() * math.pi * 2
                st['spd'] = MOVE_STEP * (0.6 + random.random() * 0.8)
                st['last_dir'] = now
            ox, oy, oz = bot['origin_pos']['x'], bot['origin_pos']['y'], bot['origin_pos']['z']
            dx = bot['pos']['x'] - ox
            dz = bot['pos']['z'] - oz
            if dx*dx + dz*dz > MOVE_RANGE*MOVE_RANGE:
                st['dir'] = math.atan2(oz - bot['pos']['z'], ox - bot['pos']['x'])
                st['spd'] = MOVE_STEP * 1.2
            else:
                bot['pos']['x'] += math.cos(st['dir']) * st['spd']
                bot['pos']['z'] += math.sin(st['dir']) * st['spd']
            p = bot['pos']
            if bot.get('jump_pending') or (bot.get('autojump') and random.random() < 0.08):
                bot['jump_pending'] = False
                st['velY'] = 0.55
                p['y'] += 0.1
            if p['y'] > oy + 0.05:
                st['velY'] -= GRAVITY_RATE
                p['y'] += st['velY']
                if p['y'] <= oy:
                    p['y'] = oy
                    st['velY'] = 0.0
            elif p['y'] < oy - 0.05:
                p['y'] += 0.2
                if p['y'] > oy:
                    p['y'] = oy
            else:
                p['y'] = oy
                st['velY'] = 0.0
            bot['pos']['yaw'] = ((st['dir'] * 180 / math.pi) + 90 + 360) % 360
            send_game(bot, build_move_player(bot, bot['ids']))
            time.sleep(MOVE_TICK_S)
        bot['move_active'] = False
    threading.Thread(target=loop, daemon=True).start()

def on_spawn(bot, on_bot_spawn_callback):
    if bot['spawned']:
        return
    bot['spawned'] = True
    on_bot_spawn_callback()
    p = bot['pos']
    print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_GREEN}¡Spawneado!{C_RESET} pos=({C_YELLOW}{p['x']:.1f}, {p['y']:.1f}, {p['z']:.1f}{C_RESET})")
    send_register(bot)
    start_movement(bot)
    start_spam(bot)

def handle_mcpe_packet(bot, pkt_data, on_bot_spawn):
    if not pkt_data:
        return
    pkt_id = pkt_data[0]
    play_status_id = P70['PLAY_STATUS'] if bot['proto'] < 84 else P84['PLAY_STATUS']
    if pkt_id == play_status_id:
        try:
            r = R(pkt_data)
            r.skip(1)
            status = r.i32be()
            if status == 3:
                on_spawn(bot, on_bot_spawn)
        except Exception:
            pass
    start_game_id = P70['START_GAME'] if bot['proto'] < 84 else P84['START_GAME']
    if pkt_id == start_game_id:
        try:
            r = R(pkt_data)
            r.skip(1)
            entity_id = r.i64be()
            r.i64be()  # runtime_id
            r.i32be()  # gamemode
            x = r.f32be()
            y = r.f32be()
            z = r.f32be()
            bot['entity_id'] = entity_id
            bot['pos'] = {'x': x, 'y': y, 'z': z, 'yaw': 0.0, 'pitch': 0.0}
            bot['origin_pos'] = {'x': x, 'y': y, 'z': z}
            send_game(bot, build_chunk_radius(bot, bot['ids']))
        except Exception:
            pass
    disconnect_id = P70['DISCONNECT'] if bot['proto'] < 84 else P84['DISCONNECT']
    if pkt_id == disconnect_id:
        try:
            r = R(pkt_data)
            r.skip(1)
            reason = r.str_()
            print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_RED}Desconectado por el servidor: {reason}{C_RESET}")
        except Exception:
            print(f"{C_CYAN}[{bot['nombre']}]{C_RESET} {C_RED}Desconectado por el servidor (error leyendo razón){C_RESET}")
        bot['is_closing'] = True

def read_packet_length(r):
    if r.left() <= 0:
        return 0
    if r.b[r.p] == 0:
        return r.i32be()
    else:
        value = 0
        shift = 0
        while True:
            if r.p >= len(r.b):
                return 0
            b = r.u8()
            value |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift > 35:
                return 0
        return value

def parse_mcpe_batch(bot, data, on_bot_spawn):
    try:
        r = R(data)
        while r.left() > 0:
            length = read_packet_length(r)
            if length <= 0 or length > r.left():
                break
            pkt_data = r.bytes_(length)
            handle_mcpe_packet(bot, pkt_data, on_bot_spawn)
    except Exception:
        pass

def handle_session_packet(bot, payload, on_bot_spawn):
    if not payload:
        return
    header = payload[0]
    if header == 0x10:  # Connection Request Accepted
        try:
            bot['state'] = 'CONNECTED'
            send_new_incoming_connection(bot)
            if bot['proto'] >= 84:
                send_reliable_ordered(bot, build_login84(bot))
            else:
                send_reliable_ordered(bot, build_login70(bot))
        except Exception:
            pass
    else:
        is_batch = (bot['proto'] < 84 and header == P70['BATCH']) or (bot['proto'] >= 84 and header == 0xfe)
        if is_batch:
            decompressed = None
            for offset in (1, 2, 5, 6):
                try:
                    decompressed = zlib.decompress(payload[offset:])
                    break
                except Exception:
                    continue
            if decompressed:
                parse_mcpe_batch(bot, decompressed, on_bot_spawn)

def handle_raknet_packet(bot, data, on_bot_spawn):
    if not data:
        return
    bot['packets_received'] += 1
    header = data[0]
    if header == 0xC0:
        return
    if header == 0xA0:
        handle_nack(bot, data)
        return
    if 0x80 <= header <= 0x8F:
        try:
            r = R(data)
            r.skip(1)
            seq = r.t_le()
            send_ack(bot, [seq])
            while r.left() > 0:
                flags = r.u8()
                reliability = (flags & 0xE0) >> 5
                is_split = (flags & 0x10) != 0
                length_in_bits = r.u16be()
                length = math.ceil(length_in_bits / 8)
                if reliability >= 2:
                    r.skip(3)
                if reliability in (3, 4, 7):
                    r.skip(4)
                split_count = 0
                split_id = 0
                split_idx = 0
                if is_split:
                    split_count = r.u32be()
                    split_id = r.u16be()
                    split_idx = r.u32be()
                payload = r.bytes_(length)
                if is_split:
                    if split_id not in bot['split_reconstruction']:
                        bot['split_reconstruction'][split_id] = {}
                    bot['split_reconstruction'][split_id][split_idx] = payload
                    if len(bot['split_reconstruction'][split_id]) == split_count:
                        full_payload = b''.join(bot['split_reconstruction'][split_id][i] for i in range(split_count))
                        del bot['split_reconstruction'][split_id]
                        handle_session_packet(bot, full_payload, on_bot_spawn)
                else:
                    handle_session_packet(bot, payload, on_bot_spawn)
        except Exception:
            pass
        return
    if header == 0x06:
        try:
            r = R(data)
            r.skip(1 + 16)
            server_guid = r.i64be()
            use_security = r.u8()
            mtu_size = r.u16be()
            bot['mtu_size'] = mtu_size
            bot['server_guid'] = server_guid
            bot['state'] = 'HANDSHAKE_1'
            send_open_connection_request_2(bot)
        except Exception:
            pass
    elif header == 0x08:
        try:
            bot['state'] = 'HANDSHAKE_2'
            send_connection_request(bot)
        except Exception:
            pass

def socket_receive_loop(bot, on_bot_spawn):
    while not bot['is_closing'] and not bot.get('tiempo_terminado', False):
        try:
            data, addr = bot['sock'].recvfrom(2048)
            if not data:
                continue
            handle_raknet_packet(bot, data, on_bot_spawn)
        except socket.timeout:
            if bot['state'] == 'DISCONNECTED':
                send_open_connection_request_1(bot)
            elif bot['state'] == 'HANDSHAKE_1':
                send_open_connection_request_2(bot)
            elif bot['state'] == 'HANDSHAKE_2':
                send_connection_request(bot)
        except Exception:
            break

def conectar_bot(bot, on_bot_spawn):
    bot['is_closing'] = False
    bot['spawned'] = False
    bot['register_sent'] = False
    bot['spam_active'] = False
    bot['move_active'] = False
    bot['state'] = 'DISCONNECTED'
    bot['send_seq'] = 0
    bot['msg_index'] = 0
    bot['order_index'] = 0
    bot['split_id'] = 0
    bot['sent_frames'] = {}
    bot['split_reconstruction'] = {}
    bot['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bot['sock'].settimeout(1.0)
    try:
        bot['sock'].bind(('', 0))
    except Exception as e:
        print(f"{C_RED}[Error] [{bot['nombre']}] Error en bind: {e}{C_RESET}")
        return False
    threading.Thread(target=socket_receive_loop, args=(bot, on_bot_spawn), daemon=True).start()
    send_open_connection_request_1(bot)
    return True