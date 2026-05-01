#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  MPS Contract Generator — Auto Deploy Script
#  Works alongside existing Traefik + Docker setup
# ═══════════════════════════════════════════════════════════════
set -e

DOMAIN="contracts.mrpropertysiam.com"
APP_DIR="/var/www/mps-contracts"
PORT=3721
REPO="https://github.com/Hostpilotpro/mps-contract-generator.git"
EMAIL="info@mrpropertysiam.com"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     MPS Contract Generator — Installing...           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. System packages ────────────────────────────────────────
echo "▸ Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-pip curl \
  fonts-noto fonts-noto-core 2>/dev/null
echo "  System packages ✓"

# ── 2. Node.js 20 ─────────────────────────────────────────────
if ! command -v node &>/dev/null || node -e "process.exit(parseInt(process.version.slice(1)) < 18 ? 1 : 0)" 2>/dev/null; then
  echo "▸ Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
  apt-get install -y nodejs >/dev/null 2>&1
fi
echo "  Node $(node -v) ✓"

# ── 3. PM2 ────────────────────────────────────────────────────
npm install -g pm2 --silent 2>/dev/null || true
echo "  PM2 ✓"

# ── 4. Python packages ────────────────────────────────────────
echo "▸ Installing Python packages..."
pip3 install --quiet reportlab Pillow 2>/dev/null
echo "  reportlab + Pillow ✓"

# ── 5. Clone / update repo ────────────────────────────────────
echo "▸ Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
  echo "  Updating existing installation..."
  cd "$APP_DIR" && git pull origin main
else
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi
cd "$APP_DIR"

# ── 6. Install npm packages & build ───────────────────────────
echo "▸ Installing npm packages..."
npm install --silent 2>/dev/null
echo "▸ Building frontend..."
npm run build 2>/dev/null
echo "  Build ✓"

# ── 7. PM2 ecosystem file ─────────────────────────────────────
cat > "$APP_DIR/ecosystem.config.cjs" << PMEOF
module.exports = {
  apps: [{
    name: 'mps-contracts',
    script: 'dist/index.cjs',
    cwd: '$APP_DIR',
    env: { NODE_ENV: 'production', PORT: $PORT },
    restart_delay: 3000,
    max_restarts: 10,
    watch: false,
  }]
}
PMEOF

# ── 8. Start with PM2 ─────────────────────────────────────────
echo "▸ Starting app with PM2..."
pm2 delete mps-contracts 2>/dev/null || true
pm2 start "$APP_DIR/ecosystem.config.cjs"
pm2 save --force >/dev/null 2>&1
pm2 startup systemd -u root --hp /root 2>/dev/null | tail -1 | bash 2>/dev/null || true
echo "  App running on port $PORT ✓"

# ── 9. Traefik dynamic config (works with existing Traefik) ───
echo "▸ Configuring Traefik routing for $DOMAIN..."

# Create Traefik dynamic config directory if it doesn't exist
mkdir -p /opt/traefik/dynamic

cat > /opt/traefik/dynamic/mps-contracts.yml << TREOF
http:
  routers:
    mps-contracts:
      rule: "Host(\`$DOMAIN\`)"
      entryPoints:
        - websecure
      service: mps-contracts
      tls:
        certResolver: letsencrypt

  services:
    mps-contracts:
      loadBalancer:
        servers:
          - url: "http://172.17.0.1:$PORT"
TREOF

# Check if Traefik is using a file provider pointing to /opt/traefik/dynamic
# If not, check the actual Traefik config location
TRAEFIK_COMPOSE=$(find /root /opt /home -name "docker-compose.yml" -o -name "docker-compose.yaml" 2>/dev/null | xargs grep -l "traefik" 2>/dev/null | head -1)
if [ -n "$TRAEFIK_COMPOSE" ]; then
  TRAEFIK_DIR=$(dirname "$TRAEFIK_COMPOSE")
  echo "  Found Traefik at: $TRAEFIK_DIR"
  # Check if there's an existing dynamic config folder
  DYNAMIC_DIR=$(find "$TRAEFIK_DIR" -name "*.yml" -path "*/dynamic/*" 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
  if [ -n "$DYNAMIC_DIR" ] && [ "$DYNAMIC_DIR" != "/opt/traefik/dynamic" ]; then
    cp /opt/traefik/dynamic/mps-contracts.yml "$DYNAMIC_DIR/mps-contracts.yml"
    echo "  Config copied to $DYNAMIC_DIR ✓"
  fi
fi

echo "  Traefik config written ✓"

# ── 10. Verify app is responding ──────────────────────────────
sleep 3
if curl -s --max-time 5 http://127.0.0.1:$PORT | grep -q "html\|contract\|MPS" 2>/dev/null; then
  echo "  App health check ✓"
else
  echo "  App starting up (may take a few more seconds)..."
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  DONE!                                               ║"
echo "║                                                      ║"
echo "║  App running on port: $PORT                      ║"
echo "║  Target URL: https://$DOMAIN  ║"
echo "║                                                      ║"
echo "║  If https:// does not work yet, check Traefik logs:  ║"
echo "║  docker logs root-traefik-1 --tail 20               ║"
echo "║                                                      ║"
echo "║  To update the app later:                            ║"
echo "║  cd $APP_DIR && git pull && npm run build && pm2 restart mps-contracts"
echo "╚══════════════════════════════════════════════════════╝"
