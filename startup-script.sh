#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

# --- Optional: read-only Docker Hub token. Empty = log in and start the app manually ---
DOCKERHUB_USER="luisgp863"
DOCKERHUB_TOKEN=""

REPO="https://github.com/LuisGP-sudo/1nventaire.git"
REPO_DIR="/opt/1nventaire"
APP_DIR="$REPO_DIR/prod"

# --- Base packages ---
apt-get update
apt-get install -y ca-certificates curl git ufw

# --- Docker + compose plugin (official repo) ---
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# --- Firewall: SSH, HTTP and HTTPS (443 already open for Caddy later) ---
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
