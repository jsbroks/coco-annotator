#!/bin/bash
# Daily MongoDB backup, run by the "backup" service in docker-compose.yml.
#
#   BACKUP_HOUR  hour of the day to back up (0-23, default 3)
#   BACKUP_KEEP  how many backups to keep (default 14)
#   TZ           time zone for BACKUP_HOUR and the file names
#
# Backups are written to /backups as coco-YYYY-MM-DD_HHMM.archive.gz.
# Restore one with:
#   sudo docker exec -i annotator_mongodb mongorestore --drop --archive --gzip < backups/<file>
set -u

HOUR=${BACKUP_HOUR:-3}
KEEP=${BACKUP_KEEP:-14}
HOST=${BACKUP_MONGO_HOST:-database}
DIR=/backups

mkdir -p "$DIR"

backup() {
  local name="coco-$(date +%Y-%m-%d_%H%M).archive.gz"
  echo "$(date '+%F %T') backing up to $name"
  if mongodump --host "$HOST" --db flask --archive="$DIR/$name.part" --gzip --quiet; then
    mv "$DIR/$name.part" "$DIR/$name"
    echo "$(date '+%F %T') done ($(du -h "$DIR/$name" | cut -f1))"
  else
    rm -f "$DIR/$name.part"
    echo "$(date '+%F %T') backup FAILED" >&2
    return 1
  fi
  # keep the newest $KEEP
  ls -1t "$DIR"/coco-*.archive.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
    echo "$(date '+%F %T') removing old backup $(basename "$old")"
    rm -f "$old"
  done
}

# wait for the database
for _ in $(seq 1 60); do
  mongosh --host "$HOST" --quiet --eval 'db.runCommand({ping: 1}).ok' >/dev/null 2>&1 && break
  sleep 5
done

# no backup in the last day (first start, or the server was off): make one now
if [ -z "$(find "$DIR" -name 'coco-*.archive.gz' -mmin -1440 2>/dev/null | head -n 1)" ]; then
  backup
fi

while true; do
  now=$(date +%s)
  next=$(date -d "today $HOUR:00" +%s)
  [ "$next" -le "$now" ] && next=$(date -d "tomorrow $HOUR:00" +%s)
  echo "$(date '+%F %T') next backup at $(date -d "@$next" '+%F %H:%M')"
  sleep $((next - now))
  backup
  sleep 60
done
