# O2 Home — whole-home control (O2 Monitor & Control)

Android app + iPhone/iPad web app to control a whole home built on Tasmota relay controllers.

- **Up to 8 Tasmota controllers**, each up to **8 relays** — topics `o2/villa/01`, `o2/villa/02`, … (or any custom topic)
- Mark which relays are used, name them, put them in **rooms**
- Views: **All rooms** or **one room**, as **simple buttons** or **room maps** (drag devices, strips, glows)
- Quick actions per scope: All off / Room off, Lights on, Lights off, **Music mode**
- Connection: **Auto** (MQTT, falls back to each controller's IP directly), **MQTT**, or **Direct**
- Screen stays on (setting), backup/copy setup to another phone (Setup → General)

## Setup in the app
⚙ **Setup → Controllers**: add controller → pick topic `o2/villa/NN` → enter its IP (for Direct) → switch on relays used → name + room.
⚙ **Setup → Rooms**: add/rename/reorder rooms.
⚙ **Setup → Connection → Which broker**:
- **Home broker** (home Wi-Fi): `192.168.10.5:1883` (app) / `ws://192.168.10.5:1884` (browser)
- **Away broker** (internet): `mqtts://your-broker:8883` (app, TLS) / `wss://your-broker:8884/mqtt` (browser) + username/password
- **Auto** tries Home first (4 s), then Away; re-checks Home whenever the app is opened; switches to Away 8 s after the home connection drops.

### Away broker: bridge your home broker to a cloud broker
Keep the Tasmotas on the home broker and mirror the `o2/` topics to the cloud broker (Mosquitto on 192.168.10.5, e.g. `/etc/mosquitto/conf.d/bridge.conf`):
```
connection cloud
address your-broker.com:8883
bridge_capath /etc/ssl/certs
remote_username <user>
remote_password <password>
topic cmnd/o2/# in 0
topic stat/o2/# out 0
topic tele/o2/# out 0
```
Long-press any device for icon, colour, strip shape, room or relay changes.
**Arrange** (quick button): drag ⠿ to reorder buttons, tap the size chip for Small / Normal / Wide; on a map drag the icons.

## Android
Push to `main` → GitHub Actions builds a signed APK → **Releases** → download on the phone and install.

## iPhone / iPad (web app) — on the Pi run one of:
```
curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi-nginx.sh | bash   # http://<pi>:8020/
curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi.sh | bash         # http://<pi>:1880/home/
```
Then Safari → Share → Add to Home Screen.

Brand assets: `brand/` (O2 gold #D4AF37).

## Device types
- **Switch** — any relay (lights, AC, fan, TV, projector, water heater, cat's washroom …). The icon is picked from the name.
- **Low / High** (e.g. cove lights) — long-press → Type *Low / High* → Low relay + High relay. Low = Low relay ON, High relay OFF · High = both ON · Off = both OFF.
  Same tile size: tap = on (last level) / off, tap *Low* or *High* to choose the level.
- **Gate** — Setup → Controllers → *+ Add gate* (its own device, not tied to one relay). Per button:
  - **Open**: relay A **ON** + relay B **OFF** (default 7 ON, 8 OFF) · **Close**: relay B **ON** + relay A **OFF** (8 ON, 7 OFF) — OFF is sent first, then ON.
  - 1-second pulse: set it in Tasmota, e.g. `PulseTime7 10`, `PulseTime8 10`.
  - **Half open**: only publishes an MQTT message (default `o2/gate/half` → `ON`); Node-RED does the timing.
  - *All off* and *Room off* never send anything to gate relays.
- **Garden watering (Node-RED)** — Setup → Controllers → *+ Add garden watering*. The app talks to a dedicated topic:
  - app → `o2/garden/watering/set`: `{"cmd":"start","minutes":10}`, `{"cmd":"stop"}`, `{"cmd":"auto","on":true}`, `{"cmd":"get"}`
  - Node-RED → `o2/garden/watering/state` (retained): `{"state":"ON","until":<epoch ms>,"auto":true,"schedule":"06:00 · 15 min"}`
  - Ready-made flow: `node-red/garden-watering-flow.json` (Node-RED → Menu → Import). Edit the relay topic and schedule at the top of the *Garden watering* function.

## Group buttons (Lights / Climate)

One full-width button that controls several devices — e.g. 2 cove lights + 2 spot lights, or AC + fan.
- Inside a room the Lights button shows **every light as its own tile** (default): cove lights get Low / High (tap the lit one again for off), spots and lamps tap on/off, plus All on/off. **Half height** option: Lights = one row Spots · Cove low · Cove high · All on/off; Climate = big Fan quick button with a small AC button on the right. **Full** shows a control for every device.
- Big picture + master power button: turns the whole group on or off (cove lights return to their last Low/High).
- Each device has its own large control inside the card; Low/High lights get **Off · Low · High**.
- The individual buttons are hidden in that room (they stay on the map); turn this off in the group editor.
- Add or edit under **Setup → Controllers → Group buttons**, or long-press a group. On first start the app creates a Lights and a Climate button in each room that has them.

## All rooms – "By type" (default)

Every room in one window, one small button per kind of device: **Cove lights · Spot lights · Lights · Climate (AC + fan) · TV**, plus gate, watering and anything else.
- **Tap**: all of that kind on / off (cove lights return to their last Low/High).
- **Gate**: tap opens / closes (the button shows what the next tap does); Open · Half open · Close are in the room.
- **Press and hold any button** (or empty space in a room) to open that room with all its buttons.
- **Arrange** (top bar) works here too: drag the grip to reorder the buttons in each room.
- Setup → General: *All rooms – small icons only*, and *Open the app on*: last visited room, All rooms or a fixed room.
- Setup → General → *All rooms – buttons*: By type · Every device · Large.

## Power meter – Tuya PC473 (3-phase clamp meter)

The app shows live power at the top (⚡ chip), a Power card in All rooms (total kW, L1/L2/L3, kWh) and a detail sheet
(voltage, current, power, PF per phase, frequency, relay switch, raw data points).

The meter is read **locally** by a small bridge on the Pi (tinytuya → MQTT). After setup no Tuya cloud is needed.

1. Install on the Pi (same network as the meter):
   `curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi-power.sh | sudo bash`
2. Find the meter's local IP + protocol: `cd /opt/o2-power && sudo ./venv/bin/python -m tinytuya scan`
3. Get the **local key** (one time): create a free Cloud project on https://iot.tuya.com, link your Smart Life / Tuya app account
   (Devices → Link App Account → scan QR), then run `sudo ./venv/bin/python -m tinytuya wizard` with the project's Access ID / Secret.
   The device ID is the *Virtual ID* from the Tuya app (Device Information).
4. Edit `/etc/o2-power.json` (ip, key; mqtt user/pass if your broker needs them) → `sudo systemctl restart o2-power`
   → `journalctl -u o2-power -f`.
5. In the app: Setup → Controllers → **+ Add power meter**, topic `o2/energy/main`.

MQTT: `o2/energy/main/state` (retained JSON: power W, current A, energy kWh, freq, phases[v,a,w,pf,kwh], dps raw),
`o2/energy/main/set` `{"cmd":"get"}` or `{"relay":true|false}`.
Default data points (PC473/PC321): 101-106 L1, 111-116 L2, 121-126 L3 (V×0.1, A×0.001, W, PF×0.01, kWh×0.01), 131 total kWh,
132 total A, 133 total W, 135 Hz. Different firmware? Override in `"map"`, e.g. `"power": [115, 1]`.

### One-line light buttons (e.g. Living + Dining)
Group editor → Button: **One line** → `[All on/off] [Spot] [Strip 1] [Strip 2]` in one row. Make one Lights button per area
(Living, Dining) in the same room; each is one line. Cove lights in a line: tap = Low → High → Off.
Climate card: fan takes 2 parts, each AC 1 part.
