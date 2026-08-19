#!/usr/bin/env bash
# Runs ON the droplet (as root) to install and start the app.
# Assumes the app files were already copied to /opt/visitform.
set -euo pipefail

APP_DIR=/opt/visitform

echo "==> Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx

echo "==> Creating virtualenv"
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Setting ownership + data permissions"
chown -R www-data:www-data "$APP_DIR"

if [ ! -f "$APP_DIR/.env" ]; then
  echo "!! WARNING: $APP_DIR/.env is missing. Copy .env.example to .env and fill it in."
fi

echo "==> Installing systemd service"
cp "$APP_DIR/deploy/visitform.service" /etc/systemd/system/visitform.service
systemctl daemon-reload
systemctl enable visitform
systemctl restart visitform

echo "==> Configuring nginx"
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/visitform
ln -sf /etc/nginx/sites-available/visitform /etc/nginx/sites-enabled/visitform
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "==> Done. App should be live on http://<droplet-ip>/"
systemctl --no-pager status visitform | head -5
