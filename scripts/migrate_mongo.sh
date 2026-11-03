#!/usr/bin/env bash
# Copy the database of an original coco-annotator install (MongoDB 4.0,
# volume "<project>_mongodb_data") into the MongoDB 7 volume used by this
# version ("<project>_mongodb7_data").
#
# Run it from the coco-annotator folder while the stack is STOPPED:
#   docker compose down
#   ./scripts/migrate_mongo.sh
#
# The old volume is only read and is kept, so you can roll back at any time.
# A dump file is also saved in this folder (mongo-dump-*/).
#
# Options (environment variables):
#   OLD_DIR     old MongoDB 4.0 data FOLDER instead of a volume. The original
#               docker-compose.gpu.yml stored the database in ./db, e.g.
#               OLD_DIR=/home/user/coco-annotator/db ./scripts/migrate_mongo.sh
#   OLD_VOLUME  old MongoDB 4.0 volume   (auto-detected)
#   NEW_VOLUME  new MongoDB 7 volume     (default: <project>_mongodb7_data)
#   DB_NAME     application database     (default: flask)
#   FORCE=1     replace data already in NEW_VOLUME
set -euo pipefail
cd "$(dirname "$0")/.."

if ! docker info >/dev/null 2>&1; then
  echo "Cannot talk to Docker (is it running? did you use sudo?)."
  exit 1
fi

DB_NAME="${DB_NAME:-flask}"
PROJECT="${COMPOSE_PROJECT_NAME:-$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')}"
NEW_VOLUME="${NEW_VOLUME:-${PROJECT}_mongodb7_data}"

if [ -n "${OLD_DIR:-}" ]; then
  OLD_DIR="$(cd "$OLD_DIR" && pwd)"
  if ! ls "$OLD_DIR"/WiredTiger* >/dev/null 2>&1 && ! ls "$OLD_DIR"/*.ns >/dev/null 2>&1; then
    echo "$OLD_DIR does not look like a MongoDB data folder."
    exit 1
  fi
  OLD_SOURCE="$OLD_DIR"
  # refuse if a running container mounts this folder
  for c in $(docker ps -q); do
    if docker inspect -f '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' "$c" | grep -qx "$OLD_DIR"; then
      echo "Container $(docker inspect -f '{{.Name}}' "$c") is using $OLD_DIR. Stop the old stack first."
      exit 1
    fi
  done
elif [ -z "${OLD_VOLUME:-}" ]; then
  mapfile -t candidates < <(docker volume ls -q | grep -E 'mongodb_data$' || true)
  if [ "${#candidates[@]}" -eq 1 ]; then
    OLD_VOLUME="${candidates[0]}"
  else
    echo "Could not pick the old MongoDB volume automatically. Candidates:"
    printf '  %s\n' "${candidates[@]:-(none found)}"
    echo "Run again with OLD_VOLUME=<name> $0"
    echo "(If the old install kept its database in a folder such as ./db, use OLD_DIR=<path>.)"
    exit 1
  fi
fi
if [ -z "${OLD_DIR:-}" ]; then
  docker volume inspect "$OLD_VOLUME" >/dev/null
  OLD_SOURCE="$OLD_VOLUME"
  # Two mongod processes on one data directory corrupt it: refuse if the old
  # volume is in use.
  if [ -n "$(docker ps -q --filter "volume=$OLD_VOLUME")" ]; then
    echo "A running container is using $OLD_VOLUME. Stop the stack first (docker compose down)."
    exit 1
  fi
fi

if docker volume inspect "$NEW_VOLUME" >/dev/null 2>&1 && [ "${FORCE:-0}" != "1" ]; then
  if [ -n "$(docker run --rm -v "$NEW_VOLUME":/data alpine ls -A /data 2>/dev/null)" ]; then
    echo "$NEW_VOLUME already contains data. Run with FORCE=1 to replace the '$DB_NAME' database in it."
    exit 1
  fi
fi

DUMP_DIR="$PWD/mongo-dump-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DUMP_DIR"
cleanup() { docker rm -f coco-migrate-old coco-migrate-new >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "1/3 Dumping database '$DB_NAME' from $OLD_SOURCE (mongo:4.0) ..."
docker run -d --name coco-migrate-old -v "$OLD_SOURCE":/data/db mongo:4.0 >/dev/null
until docker exec coco-migrate-old mongo --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1; do sleep 1; done
# celery_taskmeta only holds old Celery task results (unused, and its
# MongoDB 4.0 index definition is rejected by MongoDB 7), so it is skipped.
docker exec coco-migrate-old mongodump --db "$DB_NAME" --excludeCollection=celery_taskmeta \
  --archive=/tmp/dump.archive --gzip
docker cp coco-migrate-old:/tmp/dump.archive "$DUMP_DIR/dump.archive"
docker stop -t 60 coco-migrate-old >/dev/null

echo "2/3 Restoring into $NEW_VOLUME (mongo:7.0) ..."
# Label it like docker compose would, so compose does not warn that the
# volume "was not created by Docker Compose".
docker volume create \
  --label com.docker.compose.project="$PROJECT" \
  --label com.docker.compose.volume=mongodb7_data \
  "$NEW_VOLUME" >/dev/null
docker run -d --name coco-migrate-new -v "$NEW_VOLUME":/data/db mongo:7.0 >/dev/null
until docker exec coco-migrate-new mongosh --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1; do sleep 1; done
docker cp "$DUMP_DIR/dump.archive" coco-migrate-new:/tmp/dump.archive
docker exec coco-migrate-new mongorestore --archive=/tmp/dump.archive --gzip --drop

echo "3/3 Checking ..."
docker exec coco-migrate-new mongosh --quiet "$DB_NAME" --eval '
  for (const c of ["user_model", "dataset_model", "image_model", "annotation_model", "category_model"]) {
    print(c.padEnd(18), db.getCollection(c).countDocuments());
  }'
# Shut mongod down cleanly. If it is killed (docker rm -f), MongoDB keeps
# stale collection counts and the app reports e.g. 0 users.
docker stop -t 60 coco-migrate-new >/dev/null

echo
echo "Done. Old data in $OLD_SOURCE was not modified; dump saved in $DUMP_DIR"
echo "Start the new version with: docker compose up -d --build"
