#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  MPS Contract Generator — Auto Deploy Script
#  Run this on your Hostinger VPS as root
# ═══════════════════════════════════════════════════════════════
set -e

DOMAIN="contracts.mrpropertysiam.com"
APP_DIR="/var/www/mps-contracts"
PORT=3721
REPO="https://github.com/Hostpilotpro/mps-contract-generator.git"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     MPS Contract Generator — Installing...           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. System packages ────────────────────────────────────────
echo "▸ Installing system packages..."
apt-get update -qq
apt-get install -y -qq curl git nginx python3 python3-pip certbot python3-certbot-nginx \
  fonts-noto fonts-noto-cjk 2>/dev/null

# ── 2. Node.js 20 ─────────────────────────────────────────────
if ! command -v node &>/dev/null || [[ "$(node -v)" < "v18" ]]; then
  echo "▸ Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null
  apt-get install -y nodejs 2>/dev/null
fi
echo "  Node $(node -v) ✓"

# ── 3. PM2 ────────────────────────────────────────────────────
npm install -g pm2 --silent 2>/dev/null
echo "  PM2 ✓"

# ── 4. Python packages ────────────────────────────────────────
echo "▸ Installing Python packages..."
pip3 install --quiet reportlab Pillow 2>/dev/null
echo "  reportlab + Pillow ✓"

# ── 5. Clone / update repo ────────────────────────────────────
echo "▸ Cloning repository..."
if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR" && git pull origin main
else
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

# ── 6. Install npm packages & build ───────────────────────────
echo "▸ Installing npm packages..."
npm install --silent

echo "▸ Building frontend..."
npm run build

# ── 7. PM2 ecosystem file ─────────────────────────────────────
cat > "$APP_DIR/ecosystem.config.cjs" << EOF
module.exports = {
  apps: [{
    name: 'mps-contracts',
    script: 'dist/index.cjs',
    cwd: '$APP_DIR',
    env: { NODE_ENV: 'production', PORT: $PORT },
    restart_delay: 3000,
    max_restarts: 10,
  }]
}
EOF

# ── 8. Start with PM2 ─────────────────────────────────────────
echo "▸ Starting app with PM2..."
pm2 delete mps-contracts 2>/dev/null || true
pm2 start "$APP_DIR/ecosystem.config.cjs"
pm2 save
pm2 startup | tail -1 | bash 2>/dev/null || true

# ── 9. Nginx config ───────────────────────────────────────────
echo "▸ Configuring Nginx..."
cat > /etc/nginx/sites-available/mps-contracts << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Serve static files directly from S3-style dist
    root $APP_DIR/dist/public;
    index index.html;

    # API calls → Node.js backend
    location /api/ {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 120s;
    }

    # Font and static asset files
    location /fonts/ {
        try_files \$uri =404;
    }

    # All other routes → index.html (SPA)
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

ln -sf /etc/nginx/sites-available/mps-contracts /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
echo "  Nginx ✓"

# ── 10. SSL certificate ───────────────────────────────────────
echo "▸ Getting SSL certificate for $DOMAIN..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email info@mrpropertysiam.com \
  --redirect 2>/dev/null && echo "  SSL ✓" || echo "  SSL skipped (add DNS first, then run: certbot --nginx -d $DOMAIN)"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  DONE! App running at:                               ║"
echo "║  http://$DOMAIN                    ║"
echo "║                                                      ║"
echo "║  To update later, run:                               ║"
echo "║  cd $APP_DIR && git pull && npm run build && pm2 restart mps-contracts"
echo "╚══════════════════════════════════════════════════════╝"
