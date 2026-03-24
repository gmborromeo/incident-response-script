#!/bin/bash

SERVICE=$1
#SERVICE="postgresql"
MAX_TRIES=3
BACKOFF=5   # seconds, doubles each attempt
LOG_FILE="logs/incident.log"

if [ -z "$SERVICE" ]; then
  echo "Usage: ./restart.sh "
  exit 1
fi

log() {
  echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\
\"level\":\"info\",\"check\":\"restart\",\
\"value\":0,\"message\":\"$1\"}" >> "$LOG_FILE"
  echo "[RESTART] $1"
}


log "Attempting restart of $SERVICE (max $MAX_TRIES attempts)"

for i in $(seq 1 $MAX_TRIES); do
  log "Restart attempt $i of $MAX_TRIES for $SERVICE (backoff: ${BACKOFF}s)"

  sudo systemctl restart $SERVICE
  sleep 3

  STATUS=$(systemctl is-active "$SERVICE")
  if [ "$STATUS" = "active" ]; then
    log "Successfully restarted $SERVICE on attempt $i"
    exit 0
  fi

  log "$SERVICE still not active after attempt $i - waiting ${BACKOFF}s"
  sleep $BACKOFF
  BACKOFF=$((BACKOFF * 2))  # exponential backoff: 5s, 10s, 20s

done

log "FAILED to restart $SERVICE after $MAX_TRIES attempts - manual intervention required"
exit 1
