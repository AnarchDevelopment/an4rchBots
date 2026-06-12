import time
import math
import struct
from .Packet import W, R, MAGIC

FRAME_STORE_MAX = 1024

def _udp_send(bot, buf):
    if bot['sock'] is None:
        return
    try:
        bot['sock'].sendto(buf, (bot['host'], bot['port']))
        bot['packets_sent'] += 1
    except Exception:
        pass

def _rak_frame(bot, payload, is_split, split_count, split_id, split_idx):
    if bot['sock'] is None or bot['is_closing'] or bot.get('tiempo_terminado', False):
        return
    seq = bot['send_seq']
    bot['send_seq'] += 1
    w = W()
    w.u8(0x84).t_le(seq)
    w.u8(0x70 if is_split else 0x60)
    w.u16be(len(payload) * 8)
    mi = bot['msg_index']; bot['msg_index'] += 1
    oi = bot['order_index']; bot['order_index'] += 1
    w.t_le(mi).t_le(oi).u8(0)
    if is_split:
        w.u32be(split_count).u16be(split_id).u32be(split_idx)
    w.raw(payload)
    buf = w.buf()
    bot['sent_frames'][seq] = buf
    if len(bot['sent_frames']) > FRAME_STORE_MAX:
        del bot['sent_frames'][next(iter(bot['sent_frames']))]
    _udp_send(bot, buf)

def send_reliable_ordered(bot, payload):
    if bot['sock'] is None or bot['is_closing'] or bot.get('tiempo_terminado', False):
        return
    MAX = (bot['mtu_size'] or 1464) - 60
    if len(payload) <= MAX:
        _rak_frame(bot, payload, False, 0, 0, 0)
        return
    sid = bot['split_id'] & 0xFFFF
    bot['split_id'] += 1
    cnt = math.ceil(len(payload) / MAX)
    for i in range(cnt):
        _rak_frame(bot, payload[i*MAX:(i+1)*MAX], True, cnt, sid, i)

def send_ack(bot, nums):
    if bot['sock'] is None or bot['is_closing']:
        return
    sns = sorted(set(nums))
    recs = []
    i = 0
    while i < len(sns):
        s = e = sns[i]
        while i+1 < len(sns) and sns[i+1] == sns[i]+1:
            i += 1
            e = sns[i]
        recs.append((s, e))
        i += 1
    w = W().u8(0xC0).u16be(len(recs))
    for s, e in recs:
        w.u8(1).t_le(s) if s == e else w.u8(0).t_le(s).t_le(e)
    _udp_send(bot, w.buf())

def handle_nack(bot, msg):
    if bot['sock'] is None or bot['is_closing']:
        return
    try:
        r = R(msg)
        r.skip(1)
        cnt = r.u16be()
        for _ in range(cnt):
            single = r.u8()
            s = r.t_le()
            e = s if single else r.t_le()
            for seq in range(s, e+1):
                f = bot['sent_frames'].get(seq)
                if f and bot['sock'] and not bot['is_closing']:
                    _udp_send(bot, f)
    except Exception:
        pass

def send_open_connection_request_1(bot):
    mtu = bot['current_mtu']
    w = W().u8(0x05).magic().u8(8)
    padding_len = mtu - len(w.buf()) - 28
    if padding_len > 0:
        w.raw(bytes([0] * padding_len))
    _udp_send(bot, w.buf())

def send_open_connection_request_2(bot):
    w = W().u8(0x07).magic().rak_ip(bot['host'], bot['port']).u16be(bot['mtu_size']).i64be(bot['client_guid'])
    _udp_send(bot, w.buf())

def send_connection_request(bot):
    now_ms = int(time.time() * 1000)
    payload = W().u8(0x09).i64be(bot['client_guid']).i64be(now_ms).u8(0).buf()
    send_reliable_ordered(bot, payload)

def send_new_incoming_connection(bot):
    w = W().u8(0x13).rak_ip(bot['host'], bot['port'])
    for _ in range(10):
        w.rak_ip("127.0.0.1", 0)
    now_ms = int(time.time() * 1000)
    w.i64be(now_ms).i64be(0)
    send_reliable_ordered(bot, w.buf())