#!/usr/bin/env bash
# Daily SQLite backup. On the VM add to cron, e.g.:
#   0 3 * * * /home/ubuntu/toefl-gre-app/backup.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/data/app.db"
DEST="$DIR/backups"
mkdir -p "$DEST"
[ -f "$SRC" ] || { echo "no db at $SRC"; exit 0; }
cp "$SRC" "$DEST/app-$(date +%F-%H%M).db"
# keep the 14 most recent
ls -1t "$DEST"/app-*.db 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "backed up to $DEST"
