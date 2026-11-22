#!/usr/bin/env python3
"""O2 Home - Tuya power meter bridge (OWON / Tuya PC473 3-phase clamp meter, and similar).

Reads the meter on the local network with tinytuya (no Tuya cloud needed after setup)
and publishes the readings to MQTT for the O2 Home app:

  <topic>/state   retained JSON  {"online":true,"power":2410,"current":10.6,"energy":1234.5,"freq":50,
                                  "phases":[{"v":230.1,"a":3.2,"w":700,"pf":0.95,"kwh":410.2},...],"dps":{...raw...},"ts":...}
  <topic>/set     {"cmd":"get"} -> publish now,  {"relay":true|false} -> switch the meter's relay (if it has one)

Config: /etc/o2-power.json (see power-meter/o2-power.example.json)
"""
import base64, json, os, sys, threading, time

import tinytuya
import paho.mqtt.client as mqtt

CFG_PATH = sys.argv[1] if len(sys.argv) > 1 else '/etc/o2-power.json'

# PC473 / PC321 style data points:  name -> (dp, scale)
DEFAULT_MAP = {
    'v1': (101, 0.1),  'a1': (102, 0.001), 'w1': (103, 1), 'pf1': (104, 0.01), 'kwh1': (106, 0.01),
    'v2': (111, 0.1),  'a2': (112, 0.001), 'w2': (113, 1), 'pf2': (114, 0.01), 'kwh2': (116, 0.01),
    'v3': (121, 0.1),  'a3': (122, 0.001), 'w3': (123, 1), 'pf3': (124, 0.01), 'kwh3': (126, 0.01),
    'energy': (131, 0.01), 'current': (132, 0.001), 'power': (133, 1), 'freq': (135, 1), 'temp': (136, 0.1),
    'relay': (1, None),
}
# Some Tuya meters send each phase as base64 in dp 6 / 7 / 8 (voltage 2 bytes 0.1 V, current 3 bytes mA, power 3 bytes W)
B64_PHASES = {1: '6', 2: '7', 3: '8'}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def decode(dps, mp):
    out = {}
    for name, spec in mp.items():
        dp, scale = (spec[0], spec[1]) if isinstance(spec, (list, tuple)) else (spec, 1)
        v = dps.get(str(dp))
        if v is None:
            continue
        if scale is None or isinstance(v, bool):
            out[name] = v
            continue
        n = num(v)
        if n is not None:
            out[name] = round(n * scale, 4)
    phases = []
    for i in (1, 2, 3):
        p = {k: out.get(f'{k}{i}') for k in ('v', 'a', 'w', 'pf', 'kwh')}
        raw = dps.get(B64_PHASES[i])
        if p['w'] is None and isinstance(raw, str):
            try:
                b = base64.b64decode(raw)
                if len(b) >= 8:
                    p['v'] = int.from_bytes(b[0:2], 'big') / 10
                    p['a'] = int.from_bytes(b[2:5], 'big') / 1000
                    p['w'] = int.from_bytes(b[5:8], 'big')
            except Exception:
                pass
        if any(x is not None for x in p.values()):
            phases.append({k: x for k, x in p.items() if x is not None})
    st = {'phases': phases}
    for k in ('power', 'current', 'energy', 'freq', 'temp', 'relay'):
        if k in out:
            st[k] = out[k]
    if 'power' not in st and phases:
        st['power'] = round(sum(p.get('w', 0) for p in phases), 1)
    if 'current' not in st and phases:
        st['current'] = round(sum(p.get('a', 0) for p in phases), 3)
    if 'energy' not in st and any('kwh' in p for p in phases):
        st['energy'] = round(sum(p.get('kwh', 0) for p in phases), 2)
    return st


class Meter(threading.Thread):
    def __init__(self, m, client, interval):
        super().__init__(daemon=True)
        self.m, self.client, self.interval = m, client, interval
        self.topic = m.get('topic', 'o2/energy/main').strip('/')
        self.map = dict(DEFAULT_MAP)
        self.map.update({k: tuple(v) if isinstance(v, list) else v for k, v in (m.get('map') or {}).items()})
        self.dev, self.dps, self.online, self.kick = None, {}, None, threading.Event()

    def connect(self):
        versions = [m for m in [self.m.get('version', 'auto')] if m != 'auto'] or [3.5, 3.4, 3.3, 3.1]
        for ver in versions:
            d = tinytuya.Device(self.m['id'], address=self.m['ip'], local_key=self.m['key'], version=float(ver))
            d.set_socketTimeout(5)
            d.set_socketRetryLimit(1)
            st = d.status()
            if st and 'dps' in st:
                log(self.m.get('name', self.topic), f'connected (protocol {ver})')
                d.set_socketPersistent(True)
                self.dps.update({str(k): v for k, v in st['dps'].items()})
                return d
        raise RuntimeError(f'no answer from {self.m["ip"]} - check IP, local key and that the Tuya app is closed')

    def publish(self, online=True):
        st = decode(self.dps, self.map) if online else {}
        st.update({'online': online, 'name': self.m.get('name', ''), 'ts': int(time.time()), 'dps': self.dps})
        self.client.publish(f'{self.topic}/state', json.dumps(st), qos=0, retain=True)
        if online != self.online:
            log(self.m.get('name', self.topic), 'online' if online else 'OFFLINE')
        self.online = online

    def command(self, j):
        if j.get('relay') is not None and self.dev:
            dp = self.map.get('relay', (1, None))[0]
            self.dev.set_value(dp, bool(j['relay']))
        self.kick.set()

    def run(self):
        refresh = sorted({int(v[0] if isinstance(v, tuple) else v) for k, v in self.map.items() if k != 'relay'})
        while True:
            try:
                if not self.dev:
                    self.dev = self.connect()
                    self.publish(True)
                try:
                    self.dev.updatedps(refresh)        # ask the meter to send fresh values
                except Exception:
                    pass
                st = self.dev.status()
                if not st or 'dps' not in st:
                    raise RuntimeError(st.get('Error') if isinstance(st, dict) else 'no data')
                self.dps.update({str(k): v for k, v in st['dps'].items()})
                self.publish(True)
            except Exception as e:
                log(self.m.get('name', self.topic), 'error:', e)
                try:
                    self.dev and self.dev.close()
                except Exception:
                    pass
                self.dev = None
                self.publish(False)
                time.sleep(min(30, self.interval * 3))
            self.kick.wait(self.interval)
            self.kick.clear()


def main():
    cfg = json.load(open(CFG_PATH))
    mq = cfg.get('mqtt', {})
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='o2-power-' + str(os.getpid()))
    except AttributeError:                       # paho-mqtt 1.x
        client = mqtt.Client(client_id='o2-power-' + str(os.getpid()))
    if mq.get('user'):
        client.username_pw_set(mq['user'], mq.get('pass', ''))
    meters = [Meter(m, client, float(cfg.get('interval', 5))) for m in cfg.get('meters', [])]
    by_topic = {f'{m.topic}/set': m for m in meters}

    def on_connect(c, u, flags, rc, *a):
        log('MQTT connected', mq.get('host'))
        for t in by_topic:
            c.subscribe(t)
        for m in meters:
            if m.online is not None:
                m.publish(m.online)

    def on_message(c, u, msg):
        m = by_topic.get(msg.topic)
        if not m:
            return
        try:
            j = json.loads(msg.payload.decode() or '{}')
        except ValueError:
            j = {}
        m.command(j)

    client.on_connect, client.on_message = on_connect, on_message
    client.reconnect_delay_set(2, 30)
    client.connect_async(mq.get('host', '127.0.0.1'), int(mq.get('port', 1883)), 30)
    client.loop_start()
    for m in meters:
        m.start()
    while True:
        time.sleep(3600)


if __name__ == '__main__':
    main()
