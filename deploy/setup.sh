#!/usr/bin/env bash
# ============================================================================
#  NZF WW Knowledgebase - one-shot server setup (Ubuntu)
#  Run this from the project root on the server AFTER creating the .env file.
#  Usage:  bash deploy/setup.sh
# ============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
  echo "ERROR: No .env file found. Copy .env.example to .env and fill in the"
  echo "       client secret before running this script."
  exit 1
fi

# --- 1. Install Docker if missing ---
if ! command -v docker >/dev/null 2>&1; then
  echo ">>> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

# --- 2. Build and start the stack ---
echo ">>> Building and starting containers..."
docker compose up -d --build

# --- 3. Pull the embedding model into Ollama ---
echo ">>> Pulling embedding model (nomic-embed-text)... this may take a minute."
docker compose exec -T ollama ollama pull nomic-embed-text

echo ""
echo ">>> Done. Checking health..."
sleep 3
curl -s http://localhost:8000/health || true
echo ""
echo ""
echo ">>> The app is running on port 8000 of this server."
echo ">>> IMPORTANT: restrict port 8000 in the Hetzner Cloud Firewall to your IPs,"
echo ">>> or put a password/reverse-proxy in front, until real login is added."
