#!/bin/bash

# =========================
# CONFIGURATION
# =========================

# Raspberry Pi connection
PI_HOST="10.1.10.72"         # IP address or hostname of your Pi
PI_USER="pi"                   # SSH username
PI_PASSWORD="Loyola19"                 # Leave blank if using SSH key auth
           # Change if your Pi SSH runs on a non-standard port

# Local project
LOCAL_APP_DIR="."   # Local path to your Flask project (current directory)

# Remote project
PI_APP_DIR="/opt/rpi-led-controller"                 # Directory on Pi where app lives
VENV_PATH="$PI_APP_DIR/venv"                # Virtual environment path on the Pi

# Flask systemd service name (if you’re using one)
SERVICE_NAME="myflask.service"

# Files/directories to exclude during sync
EXCLUDES=(".git" "__pycache__" "*.pyc" "node_modules" ".venv" ".pytest_cache" "*.swp")

# =========================
# DEPLOYMENT
# =========================

echo "Starting deploy to $PI_HOST..."

# Build exclude args for rsync
EXCLUDE_ARGS=""
for e in "${EXCLUDES[@]}"; do
  EXCLUDE_ARGS+=" --exclude $e"
done

# Sync files to Pi
echo "Syncing project files to Pi..."
rsync -az -e "ssh" --rsync-path="sudo rsync" --delete $EXCLUDE_ARGS "$LOCAL_APP_DIR/" "${PI_USER}@${PI_HOST}:${PI_APP_DIR}/"

echo "Deploy complete."
