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
⚙ **Setup → Rooms**: add/rename/reorder rooms. **Connection**: broker `192.168.10.5:1883` (app) / `ws://192.168.10.5:1884` (browser).
Long-press any device for icon, colour, strip shape, room or relay changes. On a map, tap ✥ to arrange.

## Android
Push to `main` → GitHub Actions builds a signed APK → **Releases** → download on the phone and install.

## iPhone / iPad (web app) — on the Pi run one of:
```
curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi-nginx.sh | bash   # http://<pi>:8020/
curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi.sh | bash         # http://<pi>:1880/home/
```
Then Safari → Share → Add to Home Screen.

Brand assets: `brand/` (O2 gold #D4AF37).
