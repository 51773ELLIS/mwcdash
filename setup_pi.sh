#!/bin/bash
# Raspberry Pi Setup Script for Revenue Dashboard
# Run this script on your Raspberry Pi to set up the application

set -e  # Exit on error

# Detect user and set project directory dynamically
USER_HOME="$HOME"
PROJECT_DIR="$USER_HOME/projects/revenue_dashboard"
REPO_URL="https://github.com/51773ELLIS/mwcdash.git"

echo "=========================================="
echo "Revenue Dashboard - Raspberry Pi Setup"
echo "=========================================="
echo "User Home: $USER_HOME"
echo "Project Directory: $PROJECT_DIR"
echo "=========================================="

# Create projects directory if it doesn't exist
echo "Creating projects directory..."
mkdir -p "$USER_HOME/projects"
cd "$USER_HOME/projects"

# Clone repository if it doesn't exist
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Cloning repository from GitHub..."
    git clone "$REPO_URL" revenue_dashboard
    cd revenue_dashboard
else
    echo "Repository already exists. Updating..."
    cd revenue_dashboard
    git pull origin main
fi

# Create virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Initialize database migrations (if not already done)
echo "Setting up database migrations..."
if [ ! -d "migrations" ]; then
    echo "Initializing migrations..."
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
else
    echo "Migrations already initialized. Running upgrades..."
    flask db upgrade
fi

# Make deploy script executable
chmod +x deploy.sh

# Install systemd service
echo "Installing systemd service..."
sudo cp systemd/revenue_dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable revenue_dashboard

# Start service
echo "Starting service..."
sudo systemctl start revenue_dashboard

# Wait a moment for service to start
sleep 2

# Check service status
echo ""
echo "Service status:"
sudo systemctl status revenue_dashboard --no-pager -l

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "The application should now be accessible at:"
echo "  http://pi.local:5050"
echo "  or"
echo "  http://$(hostname -I | awk '{print $1}'):5050"
echo ""
echo "Default login credentials:"
echo "  Username: ellis"
echo "  Password: changeme"
echo ""
echo "IMPORTANT: Change the password after first login!"
echo ""
echo "To check service logs:"
echo "  sudo journalctl -u revenue_dashboard -f"
echo ""

