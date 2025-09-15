#!/usr/bin/env bash
set -Eeuo pipefail

# Adjust these to match your VM layout
REPO_DIR="/home/korokchatterjee/StrataSlims"
PYTHON_BIN="${REPO_DIR}/.venv/bin/python3.9"

cd "$REPO_DIR"

echo "[run_with_update] Starting in $REPO_DIR"

hash_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    sha256sum "$f" | awk '{print $1}'
  else
    echo ""
  fi
}

if command -v git >/dev/null 2>&1; then
  OLD_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
  OLD_REQ_HASH=$(hash_file requirements.txt)
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  if [[ -z "$BRANCH" || "$BRANCH" == "HEAD" ]]; then
    BRANCH="${STRATASLIMS_BRANCH:-main}"
  fi

  echo "[run_with_update] Fetching latest code (branch: $BRANCH)"
  git fetch --all --prune || true
  if ! git pull --ff-only origin "$BRANCH"; then
    echo "[run_with_update] git pull failed (non-ff or network); continuing with existing code."
  fi

  NEW_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
  NEW_REQ_HASH=$(hash_file requirements.txt)

  # Install requirements only if requirements.txt changed or venv is empty
  if [[ "$OLD_REQ_HASH" != "$NEW_REQ_HASH" ]] || [[ ! -x "$PYTHON_BIN" ]]; then
    if [[ -f requirements.txt ]]; then
      echo "[run_with_update] requirements.txt changed or venv missing; installing deps (best-effort)"
      if ! "$PYTHON_BIN" -m pip install --timeout=300 --retries=3 -r requirements.txt; then
        echo "[run_with_update] pip install failed; proceeding anyway."
      fi
    fi
  fi
else
  echo "[run_with_update] git not found; skipping auto-update."
fi

exec "$PYTHON_BIN" -u "$REPO_DIR/main.py" run
