#!/bin/zsh
# One-off, needs root: moves Ollama from the developer's `brew services` agent
# to a system LaunchDaemon, and lets the kiosk account run powermetrics.
#
#   sudo /Users/Shared/joulie/scripts/kiosk/install-services.sh [kiosk-account]
#
# Undo: sudo launchctl bootout system/com.joulie.ollama
#       sudo rm /Library/LaunchDaemons/com.joulie.ollama.plist /etc/sudoers.d/joulie-powermetrics-kiosk
#       brew services start ollama
set -euo pipefail

KIOSK_USER=${1:-kioskuser}
HERE=${0:A:h}
PLIST=/Library/LaunchDaemons/com.joulie.ollama.plist
SUDOERS=/etc/sudoers.d/joulie-powermetrics-kiosk

if [[ $EUID -ne 0 || -z ${SUDO_USER:-} ]]; then
  echo "Run with sudo from your own account: sudo $0" >&2
  exit 1
fi
OWNER=$SUDO_USER
OWNER_UID=$(id -u "$OWNER")
id "$KIOSK_USER" >/dev/null

# 1. Stop the per-user Homebrew agent so two servers don't fight over :11434.
if [[ -f /Users/$OWNER/Library/LaunchAgents/homebrew.mxcl.ollama.plist ]]; then
  sudo -H -u "$OWNER" /opt/homebrew/bin/brew services stop ollama \
    || launchctl bootout "gui/$OWNER_UID/homebrew.mxcl.ollama" 2>/dev/null || true
fi

# 2. Install and start the daemon.
launchctl bootout system/com.joulie.ollama 2>/dev/null || true
sed "s/__OWNER__/$OWNER/g" "$HERE/com.joulie.ollama.plist" > "$PLIST"
chown root:wheel "$PLIST"
chmod 644 "$PLIST"
plutil -lint "$PLIST"
launchctl bootstrap system "$PLIST"
echo "ollama: started as system daemon (runs as $OWNER)"

# 3. powermetrics for joulie/power.py — validated before install, since a
#    broken sudoers file locks out sudo entirely.
tmp=$(mktemp)
echo "$KIOSK_USER ALL=(root) NOPASSWD: /usr/bin/powermetrics" > "$tmp"
visudo -cf "$tmp"
install -m 440 -o root -g wheel "$tmp" "$SUDOERS"
rm -f "$tmp"
echo "sudoers: $KIOSK_USER may run powermetrics"

# 4. Check Ollama answers.
for _ in {1..20}; do
  curl -sf http://127.0.0.1:11434/api/version >/dev/null && break
  sleep 1
done
if curl -sf http://127.0.0.1:11434/api/version >/dev/null; then
  echo "ollama: responding on :11434"
else
  echo "ollama: NOT responding — check /opt/homebrew/var/log/ollama.log" >&2
  exit 1
fi
