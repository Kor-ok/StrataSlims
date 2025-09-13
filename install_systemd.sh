#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_SRC="$(cd "$(dirname "$0")" && pwd)/systemd/strataslims.service"
SERVICE_DST="/etc/systemd/system/strataslims.service"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root (e.g., sudo $0)"
  exit 1
fi

if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "Service file not found at $SERVICE_SRC"
  exit 1
fi

cp -f "$SERVICE_SRC" "$SERVICE_DST"
systemctl daemon-reload
systemctl enable strataslims.service
systemctl restart strataslims.service

echo "Installed and started strataslims.service"
