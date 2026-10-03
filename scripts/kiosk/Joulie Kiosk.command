#!/bin/zsh
# Login Item for kioskuser. Runs run.sh inside Terminal rather than from a
# LaunchAgent: macOS grants microphone access to the app that owns the process,
# and a script launched by launchd has no app to grant it to — the mic would
# deliver silence, which Joulie reads as the handset's mute button.
exec /Users/Shared/joulie/scripts/kiosk/run.sh
