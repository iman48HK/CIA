#!/usr/bin/env bash
# Run on the Linux server as root from a **git clone** of this repo (repo root).
# Usage:  bash deploy/bootstrap.sh
#
# For a **full** install (Docker + clone + .env + compose) from only SSH, use instead:
#   curl -fsSL https://raw.githubusercontent.com/iman48HK/CIA/main/deploy/install-remote.sh | bash
# Or from your laptop:  ssh root@SERVER 'bash -s' < deploy/install-remote.sh
#
# After install, diagnose gaps:
#   curl -fsSL https://raw.githubusercontent.com/iman48HK/CIA/main/deploy/server-check.sh | bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl git docker.io docker-compose-plugin
  systemctl enable --now docker || true
fi

if [ ! -f .env.deploy ]; then
  cp deploy/env.deploy.example .env.deploy
  echo "Created .env.deploy from example — edit JWT_SECRET and OPENROUTER_API_KEY, then run:"
  echo "  docker compose -f docker-compose.prod.yml --env-file .env.deploy up -d --build"
  exit 0
fi

docker compose -f docker-compose.prod.yml --env-file .env.deploy pull 2>/dev/null || true
docker compose -f docker-compose.prod.yml --env-file .env.deploy up -d --build

echo "Services started. Open http://<this-server-ip>:6000"
echo "If the page loads but login/API fails: check CORS_ORIGINS in .env.deploy matches the exact URL (scheme + host + port)."
echo "Ensure your cloud firewall allows inbound TCP 6000."
