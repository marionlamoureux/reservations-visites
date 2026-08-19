#!/usr/bin/env bash
# Runs on YOUR machine. Creates a DigitalOcean droplet and deploys the app.
# Requires: doctl authenticated, DIGITALOCEAN_ACCESS_TOKEN set, an SSH key uploaded to DO.
set -euo pipefail

DROPLET_NAME="${DROPLET_NAME:-visit-form}"
REGION="${REGION:-fra1}"            # Frankfurt (closest to France)
SIZE="${SIZE:-s-1vcpu-512mb-10gb}"  # smallest / cheapest
IMAGE="${IMAGE:-ubuntu-24-04-x64}"
SSH_KEY_NAME="${SSH_KEY_NAME:?Set SSH_KEY_NAME to the name of your SSH key in DO}"
APP_SRC="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Resolving SSH key id for '$SSH_KEY_NAME'"
KEY_ID=$(doctl compute ssh-key list --no-header --format ID,Name | awk -v n="$SSH_KEY_NAME" '$2==n {print $1}')
[ -n "$KEY_ID" ] || { echo "SSH key '$SSH_KEY_NAME' not found in DO account."; exit 1; }

echo "==> Creating droplet '$DROPLET_NAME' ($SIZE, $REGION)"
doctl compute droplet create "$DROPLET_NAME" \
  --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --ssh-keys "$KEY_ID" --wait

IP=$(doctl compute droplet get "$DROPLET_NAME" --format PublicIPv4 --no-header)
echo "==> Droplet IP: $IP"

echo "==> Waiting for SSH..."
for i in $(seq 1 30); do
  if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 root@"$IP" true 2>/dev/null; then break; fi
  sleep 5
done

echo "==> Copying app files"
ssh root@"$IP" "mkdir -p /opt/visitform"
rsync -az --exclude .venv --exclude submissions.db --exclude .env \
  "$APP_SRC"/ root@"$IP":/opt/visitform/

echo "==> Bootstrapping server"
ssh root@"$IP" "bash /opt/visitform/deploy/bootstrap.sh"

echo ""
echo "======================================================"
echo " App deployed:   http://$IP/"
echo " Admin page:     http://$IP/admin"
echo ""
echo " NEXT: create /opt/visitform/.env on the droplet:"
echo "   scp .env root@$IP:/opt/visitform/.env"
echo "   ssh root@$IP 'systemctl restart visitform'"
echo "======================================================"
