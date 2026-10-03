#!/bin/zsh
# One-off: moves the checkout and the Whisper/embedding/XTTS model caches out of
# the developer's home (which other accounts cannot enter) into /Users/Shared,
# leaving a symlink at each old path so nothing on the developer side changes.
# Then grants both accounts write access to the folders Joulie writes to.
#
# Run as the developer account, NOT with sudo, with Joulie stopped:
#   ~/Workspaces/joulie/scripts/kiosk/relocate.sh [kiosk-account]
# Safe to re-run: anything already moved is skipped.
set -euo pipefail

KIOSK_USER=${1:-kioskuser}
OWNER=$(id -un)
SHARED=/Users/Shared

if [[ $EUID -eq 0 ]]; then
  echo "Run this as yourself, not with sudo — moved files must stay owned by you." >&2
  exit 1
fi
if ! id "$KIOSK_USER" >/dev/null 2>&1; then
  echo "No account named '$KIOSK_USER'." >&2
  exit 1
fi
if pgrep -f "main.py" >/dev/null; then
  echo "Joulie is running (pgrep -f main.py) — quit it first; it has the model caches and chroma_db open." >&2
  exit 1
fi

# Moves $1 to $2 and leaves a symlink at $1.
relocate() {
  local src=$1 dst=$2
  if [[ -L $src ]]; then
    echo "skip  $src (already a symlink → $(readlink "$src"))"
    return
  fi
  if [[ ! -e $src ]]; then
    echo "skip  $src (does not exist)"
    return
  fi
  if [[ -e $dst ]]; then
    echo "stop  $dst already exists — move or remove it, then re-run." >&2
    exit 1
  fi
  mkdir -p "$(dirname "$dst")"
  mv "$src" "$dst"
  ln -s "$dst" "$src"
  echo "moved $src → $dst"
}

relocate "$HOME/Workspaces/joulie"                     "$SHARED/joulie"
relocate "$HOME/.cache/huggingface"                    "$SHARED/joulie-models/hf"
relocate "$HOME/Library/Application Support/tts"       "$SHARED/joulie-models/tts"

# Everything is readable by every account already (755/644). Joulie writes to
# these at runtime — chroma's SQLite opens read-write even for queries, the
# greeting is re-rendered when missing, metrics and the HF lock files are
# written per turn/load. The ACL is inherited by new files, so whatever either
# account creates there stays editable by the other.
PERMS=read,write,append,delete,readattr,writeattr,readextattr,writeextattr,readsecurity,execute
DIR_PERMS=$PERMS,list,search,add_file,add_subdirectory,delete_child,file_inherit,directory_inherit

mkdir -p "$SHARED/joulie/logs/kiosk"
for dir in "$SHARED/joulie/chroma_db" "$SHARED/joulie/logs" "$SHARED/joulie/assets" \
           "$SHARED/joulie-models"; do
  [[ -d $dir ]] || continue
  for who in "$KIOSK_USER" "$OWNER"; do
    find "$dir" -type d -exec chmod +a "user:$who allow $DIR_PERMS" {} +
    find "$dir" -type f -exec chmod +a "user:$who allow $PERMS" {} +
  done
  echo "acl   $dir (writable by $OWNER and $KIOSK_USER)"
done

chmod +x "$SHARED/joulie/scripts/kiosk/run.sh" "$SHARED/joulie/scripts/kiosk/Joulie Kiosk.command"
echo
echo "Done. Next: sudo $SHARED/joulie/scripts/kiosk/install-services.sh $KIOSK_USER"
