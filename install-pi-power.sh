#!/usr/bin/env bash
# O2 Home - Tuya power meter bridge (PC473) for Raspberry Pi
# Usage:  curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi-power.sh | sudo bash
set -e
REPO=https://raw.githubusercontent.com/anwar3000/o2-home-control/main
DIR=/opt/o2-power
echo "== Installing O2 power meter bridge into $DIR"
apt-get update -qq && apt-get install -y -qq python3-venv python3-pip curl >/dev/null
mkdir -p $DIR
python3 -m venv $DIR/venv
$DIR/venv/bin/pip install -q --upgrade pip tinytuya paho-mqtt
curl -fsSL $REPO/power-meter/pc473_bridge.py -o $DIR/pc473_bridge.py
[ -f /etc/o2-power.json ] || curl -fsSL $REPO/power-meter/o2-power.example.json -o /etc/o2-power.json
cat > /etc/systemd/system/o2-power.service <<UNIT
[Unit]
Description=O2 Home power meter bridge (Tuya -> MQTT)
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
ExecStart=$DIR/venv/bin/python $DIR/pc473_bridge.py /etc/o2-power.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable o2-power >/dev/null
if grep -q PUT-LOCAL-KEY-HERE /etc/o2-power.json; then
  echo
  echo "== Almost done. Next:"
  echo "   1) Find the meter's IP and protocol:   cd $DIR && sudo ./venv/bin/python -m tinytuya scan"
  echo "   2) Get the local key:                  cd $DIR && sudo ./venv/bin/python -m tinytuya wizard"
  echo "   3) Put ip + key in /etc/o2-power.json: sudo nano /etc/o2-power.json"
  echo "   4) Start it:                           sudo systemctl restart o2-power && journalctl -u o2-power -f"
else
  systemctl restart o2-power
  echo "== Running. Log: journalctl -u o2-power -f"
fi
