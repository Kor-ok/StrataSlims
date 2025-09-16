#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_SRC="$(cd "$(dirname "$0")" && pwd)/systemd/strataslims.service"
SERVICE_DST="/etc/systemd/system/strataslims.service"
CONTROL_SRC="$(cd "$(dirname "$0")" && pwd)/systemd/strataslims-control.service"
CONTROL_DST="/etc/systemd/system/strataslims-control.service"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (e.g., sudo $0)"
  exit 1
fi

if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "Service file not found at $SERVICE_SRC"
  exit 1
fi

cp -f "$SERVICE_SRC" "$SERVICE_DST"
if [[ -f "$CONTROL_SRC" ]]; then
  cp -f "$CONTROL_SRC" "$CONTROL_DST"
fi

systemctl daemon-reload
systemctl enable --now strataslims.service
if [[ -f "$CONTROL_DST" ]]; then
  systemctl enable --now strataslims-control.service
fi

echo "Installed/started: strataslims.service and strataslims-control.service (if present)"