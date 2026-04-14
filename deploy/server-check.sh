#!/usr/bin/env bash
# Run on the server (as root):  bash deploy/server-check.sh
# Or from repo root on server:   bash deploy/server-check.sh
# Reports what is present vs missing for the CIA Docker deployment on port 6000.

set -euo pipefail
ROOT="${CIA_INSTALL_ROOT:-/opt/cia}"

pass() { echo "[ok]   $*"; }
fail() { echo "[MISS] $*"; }
warn() { echo "[warn] $*"; }

echo "======== CIA server check ($(date -u +%Y-%m-%dT%H:%MZ)) ========"
echo "Install root: $ROOT"
echo

command -v docker >/dev/null 2>&1 && pass "docker installed: $(docker --version)" || fail "docker not installed"
docker compose version >/dev/null 2>&1 && pass "docker compose plugin: $(docker compose version)" || fail "docker compose plugin missing"

if [ -d "$ROOT/.git" ]; then
  pass "repo clone exists at $ROOT"
  (cd "$ROOT" && git rev-parse --short HEAD 2>/dev/null | xargs -I{} echo "       commit: {}") || true
else
  fail "repo not found at $ROOT (expected git clone)"
fi

[ -f "$ROOT/docker-compose.prod.yml" ] && pass "docker-compose.prod.yml present" || fail "docker-compose.prod.yml missing"
[ -f "$ROOT/deploy/nginx-gateway.conf" ] && pass "nginx gateway config present" || fail "deploy/nginx-gateway.conf missing"

if [ -f "$ROOT/.env.deploy" ]; then
  pass ".env.deploy exists"
  grep -q '^JWT_SECRET=.\{16\}' "$ROOT/.env.deploy" 2>/dev/null && pass "JWT_SECRET looks set (length)" || warn "JWT_SECRET missing or very short"
  grep -q '^CORS_ORIGINS=http' "$ROOT/.env.deploy" 2>/dev/null && pass "CORS_ORIGINS present" || warn "CORS_ORIGINS missing or unusual"
  if grep -q '^OPENROUTER_API_KEY=$' "$ROOT/.env.deploy" 2>/dev/null || ! grep -q '^OPENROUTER_API_KEY=.' "$ROOT/.env.deploy" 2>/dev/null; then
    warn "OPENROUTER_API_KEY empty — AI chat/reports that call OpenRouter will fail"
  else
    pass "OPENROUTER_API_KEY non-empty"
  fi
else
  fail ".env.deploy missing — run install-remote.sh or copy deploy/env.deploy.example"
fi

echo
echo "=== Docker compose (project: cia) ==="
if [ -f "$ROOT/.env.deploy" ] && [ -f "$ROOT/docker-compose.prod.yml" ]; then
  cd "$ROOT"
  docker compose -f docker-compose.prod.yml --env-file .env.deploy ps -a 2>&1 || fail "docker compose ps failed"
else
  fail "skipped compose ps (missing files)"
fi

echo
echo "=== Listeners on 6000 (host) ==="
if command -v ss >/dev/null 2>&1; then
  ss -tlnp 2>/dev/null | grep ':6000 ' && pass "something listening on TCP 6000" || fail "nothing listening on TCP 6000 (gateway not up or wrong port)"
elif command -v netstat >/dev/null 2>&1; then
  netstat -tlnp 2>/dev/null | grep ':6000 ' && pass "something listening on TCP 6000" || fail "nothing on TCP 6000"
else
  warn "ss/netstat not available; cannot verify port 6000"
fi

echo
echo "=== HTTP checks (from this server) ==="
if curl -fsS -m 5 http://127.0.0.1:6000/api/health >/dev/null 2>&1; then
  pass "GET http://127.0.0.1:6000/api/health OK"
  curl -sS http://127.0.0.1:6000/api/health | head -c 200; echo
else
  fail "GET http://127.0.0.1:6000/api/health failed (nginx/gateway/api down or firewall loopback only)"
fi

echo
echo "=== UFW (if installed) ==="
if command -v ufw >/dev/null 2>&1; then
  ufw status 2>/dev/null | head -5
  if ufw status 2>/dev/null | grep -q 'Status: active'; then
    ufw status 2>/dev/null | grep -q '6000' && pass "ufw mentions 6000" || warn "ufw active but 6000 may be closed — run: ufw allow 6000/tcp"
  fi
else
  warn "ufw not installed (cloud firewall still must allow 6000)"
fi

echo
echo "=== Recent gateway / api logs (last 30 lines each) ==="
if [ -f "$ROOT/.env.deploy" ]; then
  cd "$ROOT"
  docker compose -f docker-compose.prod.yml --env-file .env.deploy logs --tail=30 gateway 2>&1 | tail -35 || true
  docker compose -f docker-compose.prod.yml --env-file .env.deploy logs --tail=30 api 2>&1 | tail -35 || true
fi

echo "======== end ========"
