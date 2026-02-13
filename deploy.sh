#!/bin/bash
# Stock Screener - AWS Lightsail deployment script
# Run this on a fresh Ubuntu 22.04 Lightsail instance
set -e

APP_DIR="/opt/stock-screener"
APP_USER="stockapp"
REPO="https://github.com/rigelshysaj/stock-screener.git"

echo "=== Stock Screener - Deploying to Lightsail ==="

# 1. System packages
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git nginx

# 2. Create app user
echo "[2/6] Setting up app user..."
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -r -s /bin/false "$APP_USER"
fi

# 3. Clone/update repo
echo "[3/6] Cloning repository..."
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" && sudo git pull
else
    sudo git clone "$REPO" "$APP_DIR"
fi
sudo chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# 4. Python environment
echo "[4/6] Setting up Python environment..."
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" venv/bin/pip install --quiet -r requirements.txt

# 5. Systemd service
echo "[5/6] Installing systemd service..."
sudo tee /etc/systemd/system/stock-screener.service > /dev/null <<'SERVICE'
[Unit]
Description=Stock Screener Web App
After=network.target

[Service]
Type=exec
User=stockapp
Group=stockapp
WorkingDirectory=/opt/stock-screener
ExecStart=/opt/stock-screener/venv/bin/gunicorn app:app --bind 127.0.0.1:5000 --timeout 600 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable stock-screener
sudo systemctl restart stock-screener

# 6. Nginx reverse proxy
echo "[6/6] Configuring Nginx..."
sudo tee /etc/nginx/sites-available/stock-screener > /dev/null <<'NGINX'
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;
    }
}
NGINX

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/stock-screener /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "=== Deploy complete! ==="
echo "App running at: http://$(curl -s http://checkip.amazonaws.com)"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status stock-screener   # check status"
echo "  sudo journalctl -u stock-screener -f   # view logs"
echo "  cd $APP_DIR && sudo git pull && sudo systemctl restart stock-screener  # update"
