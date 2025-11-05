#!/bin/bash
# Auto-deployment script for Revenue Dashboard
# This script is triggered by GitHub webhook

set -e  # Exit on error

PROJECT_DIR="/home/pi/projects/revenue_dashboard"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="revenue_dashboard"

echo "=========================================="
echo "Starting deployment for Revenue Dashboard"
echo "Time: $(date)"
echo "=========================================="

# Navigate to project directory
cd "$PROJECT_DIR" || {
    echo "Error: Cannot access project directory: $PROJECT_DIR"
    exit 1
}

# Pull latest changes from GitHub
echo "Pulling latest changes from GitHub..."
git pull origin main || {
    echo "Error: Git pull failed"
    exit 1
}

# Activate virtual environment
echo "Activating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "Warning: Virtual environment not found. Creating..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate" || {
    echo "Error: Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt || {
    echo "Error: Failed to install dependencies"
    exit 1
}

# Run database migrations
echo "Running database migrations..."
python3 migrate_db.py || {
    echo "Warning: Database migration failed, but continuing..."
    echo "You may need to run migrations manually: python3 migrate_db.py"
}

# Restart systemd service
echo "Restarting systemd service..."
sudo systemctl restart "$SERVICE_NAME" || {
    echo "Error: Failed to restart service"
    exit 1
}

# Check service status
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Service is running successfully"
else
    echo "Warning: Service may not be running. Check status with: sudo systemctl status $SERVICE_NAME"
fi

echo "=========================================="
echo "Deployment completed successfully!"
echo "Time: $(date)"
echo "=========================================="

