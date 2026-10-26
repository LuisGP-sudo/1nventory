#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

# --- Settings ---
DOMAIN="1nventory.duckdns.org"
REPO="https://github.com/LuisGP-sudo/1nventory.git"
REPO_DIR="/opt/1nventaire"
APP_DIR="$REPO_DIR/prod"

# Optional read-only Docker Hub token.
DOCKERHUB_USER="luisgp863"
DOCKERHUB_TOKEN=""

# --- Base packages ---
apt-get update
apt-get install -y ca-certificates curl git ufw gnupg debian-keyring debian-archive-keyring apt-transport-https

# --- Docker + compose plugin (official repo) ---
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# --- Caddy on the host (official repo): HTTPS + Let's Encrypt ---
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

cat > /etc/caddy/Caddyfile << EOF
${DOMAIN} {
    reverse_proxy 127.0.0.1:8080
}
EOF
systemctl enable caddy
systemctl restart caddy

# --- Firewall: SSH, HTTP (Let's Encrypt validation) and HTTPS ---
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# --- Code from GitHub (compose file and .env.example come from the repo) ---
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$REPO" "$REPO_DIR" || echo "git clone failed (private repo?): clone it manually into $REPO_DIR"
fi

# --- Create .env from the example (if it does not exist yet) ---
if [ -f "$APP_DIR/.env.example" ] && [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

# --- Login, pull and start (only if a token is set and the compose file exists) ---
if [ -n "$DOCKERHUB_TOKEN" ] && [ -f "$APP_DIR/docker-compose.yml" ]; then
  cd "$APP_DIR"
  echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin
  docker compose pull
  docker compose up -d
else
  echo "Next step, manually: cd $APP_DIR && docker login -u $DOCKERHUB_USER && docker compose up -d"
fi

echo "Setup finished"
