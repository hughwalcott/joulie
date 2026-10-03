#!/bin/zsh
# Starts Joulie for the kiosk account: the Gradio UI, then Chrome in kiosk
# mode pointed at it. Launched at login by "Joulie Kiosk.command" (a Login Item
# of kioskuser) — see the "Kiosk account" section of the README.
#
# Runs the same checkout the developer account edits (/Users/Shared/joulie), so
# a code or config change reaches the kiosk on its next start with nothing to
# copy. Only the paths below differ from a developer run.
set -u

JOULIE_HOME=/Users/Shared/joulie
VENV=/Users/Shared/joulie-venv
MODELS=/Users/Shared/joulie-models
LOG_DIR=$JOULIE_HOME/logs/kiosk
PORT=7860

# Model caches shared with the developer account — without these each account
# would download its own copy into its own home, and fail to at an offline event.
export HF_HOME=$MODELS/hf
export TTS_HOME=$MODELS          # Coqui appends "tts" itself
export HF_HUB_OFFLINE=1
export JOULIE_METRICS_DIR=$LOG_DIR
# __pycache__ written by this account would be owned by it and left for the
# developer account to trip over.
export PYTHONDONTWRITEBYTECODE=1

mkdir -p "$LOG_DIR"
cd "$JOULIE_HOME" || exit 1

# The port is held by whichever account started Joulie first, including one
# left running in a background fast-user-switching session.
if nc -z 127.0.0.1 $PORT 2>/dev/null; then
  echo "Port $PORT is already in use — Joulie is probably still running in another account."
  echo "Log that account out (or quit its Joulie) and log in again."
  exit 1
fi

echo "=== $(date '+%Y-%m-%d %H:%M:%S') starting Joulie as $(id -un) ===" >> "$LOG_DIR/joulie.log"
"$VENV/bin/python" main.py --ui > >(tee -a "$LOG_DIR/joulie.log") 2>&1 &
joulie_pid=$!

# A dedicated profile, so --kiosk applies even if this account already has
# Chrome open, and so the window can be closed with Joulie.
chrome_profile="$HOME/Library/Application Support/JoulieKioskChrome"
cleanup() {
  kill $joulie_pid 2>/dev/null
  pkill -f -- "--user-data-dir=$chrome_profile" 2>/dev/null
}
trap cleanup EXIT INT TERM HUP

until curl -sf -o /dev/null "http://127.0.0.1:$PORT"; do
  if ! kill -0 $joulie_pid 2>/dev/null; then
    echo "Joulie exited during startup — see $LOG_DIR/joulie.log"
    exit 1
  fi
  sleep 1
done

open -na "Google Chrome" --args --kiosk --user-data-dir="$chrome_profile" \
  --no-first-run --noerrdialogs "http://127.0.0.1:$PORT"

wait $joulie_pid
