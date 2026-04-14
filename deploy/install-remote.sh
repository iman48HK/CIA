#!/usr/bin/env bash
# Full server setup for Ubuntu/Debian as root.
# From your laptop (one password prompt), run:
#   ssh root@YOUR_SERVER_IP 'bash -s' < deploy/install-remote.sh
# Or on the server after SSH:
#   curl -fsSL https://raw.githubusercontent.com/iman48HK/CIA/main/deploy/install-remote.sh | bash
#
# Optional env:
#   CIA_REPO_URL   (default: https://github.com/iman48HK/CIA.git)
#   CIA_INSTALL_ROOT (default: /opt/cia)
#   CIA_PUBLIC_IP  (override public IPv4 for CORS, else auto-detect)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

CIA_REPO_URL="${CIA_REPO_URL:-https://github.com/iman48HK/CIA.git}"
CIA_INSTALL_ROOT="${CIA_INSTALL_ROOT:-/opt/cia}"

detect_public_ip() {
  if [ -n "${CIA_PUBLIC_IP:-}" ]; then
    echo "$CIA_PUBLIC_IP"
    return
  fi
  curl -fsSL --max-time 3 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null && return
  curl -4fsSL --max-time 3 ifconfig.me 2>/dev/null && return
  hostname -I 2>/dev/null | awk '{print $1}'
}

echo "==> Installing packages (git, curl, openssl, docker)…"
apt-get update -y
apt-get install -y ca-certificates curl git openssl docker.io docker-compose-plugin
systemctl enable --now docker

echo "==> Cloning or updating repo at ${CIA_INSTALL_ROOT}…"
mkdir -p "$(dirname "$CIA_INSTALL_ROOT")"
if [ ! -d "${CIA_INSTALL_ROOT}/.git" ]; then
  git clone -b main --depth 1 "$CIA_REPO_URL" "$CIA_INSTALL_ROOT"
else
  cd "$CIA_INSTALL_ROOT"
  git fetch origin
  git pull origin main --ff-only || git pull --ff-only
fi
cd "$CIA_INSTALL_ROOT"

PUBLIC_IP="$(detect_public_ip || true)"
PUBLIC_IP="${PUBLIC_IP:-127.0.0.1}"
CORS_ORIGINS="http://${PUBLIC_IP}:6000,http://127.0.0.1:6000,http://localhost:6000"

if [ ! -f .env.deploy ]; then
  JWT_SECRET="$(openssl rand -hex 32)"
  cat > .env.deploy << EOF
JWT_SECRET=${JWT_SECRET}
OPENROUTER_API_KEY=
OPENROUTER_MODEL=auto
OPENROUTER_FALLBACK_MODEL=qwen/qwen3-vl-32b-instruct
CORS_ORIGINS=${CORS_ORIGINS}
EOF
  chmod 600 .env.deploy
  echo "==> Created .env.deploy (JWT + CORS for ${CORS_ORIGINS}). Add OPENROUTER_API_KEY here if you use the assistant."
else
  echo "==> Keeping existing .env.deploy (not overwritten)."
fi

echo "==> Building and starting Docker stack on port 6000…"
docker compose -f docker-compose.prod.yml --env-file .env.deploy pull 2>/dev/null || true
docker compose -f docker-compose.prod.yml --env-file .env.deploy up -d --build

echo ""
echo "==> Done."
echo "    App URL:    http://${PUBLIC_IP}:6000"
echo "    Health:     http://${PUBLIC_IP}:6000/api/health"
echo "    Open TCP 6000 in your cloud firewall if the URL does not load."
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  echo "    UFW is active; if needed run: ufw allow 6000/tcp && ufw reload"
fi
