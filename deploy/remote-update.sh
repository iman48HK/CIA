#!/usr/bin/env bash
# Run on the Ubuntu server as root (e.g. after scp):  bash /root/remote-update.sh
# Stops the CIA stack, replaces /opt/cia with a fresh shallow clone from GitHub,
# restores .env.deploy from /tmp, then rebuilds and starts Docker.
set -euo pipefail

CIA_INSTALL_ROOT="${CIA_INSTALL_ROOT:-/opt/cia}"
CIA_REPO_URL="${CIA_REPO_URL:-https://github.com/iman48HK/CIA.git}"
ENV_BAK="/tmp/cia.env.deploy.bak.$$"

if [ ! -f "${CIA_INSTALL_ROOT}/.env.deploy" ]; then
  echo "ERROR: ${CIA_INSTALL_ROOT}/.env.deploy not found. Create it first (see deploy/env.deploy.example)." >&2
  exit 1
fi

echo "==> Stopping existing stack (frees port 80 for gateway)…"
if [ -f "${CIA_INSTALL_ROOT}/docker-compose.prod.yml" ]; then
  (cd "${CIA_INSTALL_ROOT}" && docker compose -f docker-compose.prod.yml --env-file .env.deploy down) || true
fi

echo "==> Backing up .env.deploy…"
cp "${CIA_INSTALL_ROOT}/.env.deploy" "$ENV_BAK"
chmod 600 "$ENV_BAK"

echo "==> Replacing ${CIA_INSTALL_ROOT} with fresh clone…"
rm -rf "${CIA_INSTALL_ROOT}"
mkdir -p "$(dirname "${CIA_INSTALL_ROOT}")"
git clone -b main --depth 1 "$CIA_REPO_URL" "${CIA_INSTALL_ROOT}"

echo "==> Restoring .env.deploy…"
cp "$ENV_BAK" "${CIA_INSTALL_ROOT}/.env.deploy"
chmod 600 "${CIA_INSTALL_ROOT}/.env.deploy"
rm -f "$ENV_BAK"

cd "${CIA_INSTALL_ROOT}"
echo "==> Building and starting (docker compose prod)…"
docker compose -f docker-compose.prod.yml --env-file .env.deploy pull 2>/dev/null || true
docker compose -f docker-compose.prod.yml --env-file .env.deploy up -d --build

echo ""
echo "==> Status:"
docker compose -f docker-compose.prod.yml --env-file .env.deploy ps
