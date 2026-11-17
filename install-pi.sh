#!/bin/bash
# O2 Home — install/update the web app into Node-RED on a Raspberry Pi.
# Run on the Pi as the user that runs Node-RED (usually "pi"):
#   curl -fsSL https://raw.githubusercontent.com/anwar3000/o2-home-control/main/install-pi.sh | bash
set -e

NR="$HOME/.node-red"
SETTINGS="$NR/settings.js"
PUBLIC="$NR/public"

echo "==> Downloading the latest web app from GitHub…"
TMP=$(mktemp -d)
curl -fsSL https://github.com/anwar3000/o2-home-control/archive/refs/heads/main.tar.gz | tar -xz -C "$TMP"
SRC="$TMP/o2-home-control-main/web"
[ -f "$SRC/index.html" ] || { echo "Download failed (web/index.html not found)"; exit 1; }

# Use the folder Node-RED already serves, if httpStatic is set to a plain path
CHANGED_SETTINGS=0
if [ -f "$SETTINGS" ]; then
  EXISTING=$(grep -E "^[[:space:]]*httpStatic[[:space:]]*:[[:space:]]*['\"]" "$SETTINGS" | head -1 | sed -E "s/.*httpStatic[[:space:]]*:[[:space:]]*['\"]([^'\"]+)['\"].*/\1/")
  if [ -n "$EXISTING" ]; then
    PUBLIC="${EXISTING%/}"
    echo "==> Node-RED already serves static files from: $PUBLIC"
  elif grep -qE "^[[:space:]]*httpStatic[[:space:]]*:" "$SETTINGS"; then
    echo "!!  settings.js has a custom httpStatic setting — copying to $PUBLIC/home; check it is served."
  else
    cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
    sed -i "0,/module.exports[[:space:]]*=[[:space:]]*{/{s#module.exports[[:space:]]*=[[:space:]]*{#module.exports = {\n    httpStatic: '$PUBLIC/',#}" "$SETTINGS"
    if grep -q "httpStatic: '$PUBLIC/'" "$SETTINGS"; then
      echo "==> Added httpStatic: '$PUBLIC/' to settings.js (backup saved)"
      CHANGED_SETTINGS=1
    else
      echo "!!  Could not edit settings.js automatically. Add this line inside module.exports = { … }:"
      echo "      httpStatic: '$PUBLIC/',"
    fi
  fi
else
  echo "!!  $SETTINGS not found — is Node-RED installed for this user ($USER)?"
fi

echo "==> Copying web app to $PUBLIC/home"
mkdir -p "$PUBLIC"
rm -rf "$PUBLIC/home"
cp -r "$SRC" "$PUBLIC/home"
rm -rf "$TMP"

if [ "$CHANGED_SETTINGS" = "1" ]; then
  echo "==> Restarting Node-RED…"
  if systemctl list-units --type=service 2>/dev/null | grep -q nodered; then
    sudo systemctl restart nodered
  elif command -v node-red-restart >/dev/null 2>&1; then
    node-red-restart
  else
    echo "!!  Please restart Node-RED yourself."
  fi
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "Done.  Open on iPhone / iPad (Safari):   http://${IP:-<pi-ip>}:1880/home/"
echo "Then: Share → Add to Home Screen."
