# Raspberry Pi Deployment Guide

This guide will help you deploy the Earnings Dashboard to your Raspberry Pi.

## Quick Setup

### Option 1: Automated Setup Script (Recommended)

1. **SSH into your Raspberry Pi:**
   ```bash
   ssh pi@192.168.1.88
   ```

2. **Download and run the setup script:**
   ```bash
   cd /home/pi
   wget https://raw.githubusercontent.com/51773ELLIS/mwcdash/main/setup_pi.sh
   chmod +x setup_pi.sh
   ./setup_pi.sh
   ```

   Or manually download the script from the repository and run it.

### Option 2: Manual Setup

1. **SSH into your Raspberry Pi**

2. **Clone the repository:**
   ```bash
   mkdir -p /home/pi/projects
   cd /home/pi/projects
   git clone https://github.com/51773ELLIS/mwcdash.git revenue_dashboard
   cd revenue_dashboard
   ```

3. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Make deploy script executable:**
   ```bash
   chmod +x deploy.sh
   ```

6. **Install and start systemd service:**
   ```bash
   sudo cp systemd/revenue_dashboard.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable revenue_dashboard
   sudo systemctl start revenue_dashboard
   ```

7. **Check service status:**
   ```bash
   sudo systemctl status revenue_dashboard
   ```

## Access the Application

Once deployed, access the dashboard at:
- `http://192.168.1.88:5050`

**Note:** This application runs alongside Homebridge on the same Raspberry Pi. Both services can run simultaneously without conflicts.

**Default Login:**
- Username: `ellis`
- Password: `changeme`

**⚠️ IMPORTANT:** Change the password immediately after first login!

## Service Management

### Check Status
```bash
sudo systemctl status revenue_dashboard
```

### View Logs
```bash
# View recent logs
sudo journalctl -u revenue_dashboard -n 50

# Follow logs in real-time
sudo journalctl -u revenue_dashboard -f
```

### Restart Service
```bash
sudo systemctl restart revenue_dashboard
```

### Stop Service
```bash
sudo systemctl stop revenue_dashboard
```

### Start Service
```bash
sudo systemctl start revenue_dashboard
```

## Updating the Application

### Manual Update
```bash
cd /home/pi/projects/revenue_dashboard
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart revenue_dashboard
```

### Automatic Update (via Webhook)

See the [README.md](README.md) for webhook setup instructions.

## Troubleshooting

### Service Won't Start

1. Check logs:
   ```bash
   sudo journalctl -u revenue_dashboard -n 100
   ```

2. Check if port 5050 is in use:
   ```bash
   sudo netstat -tulpn | grep 5050
   ```

3. Verify Python path in service file:
   ```bash
   cat /etc/systemd/system/revenue_dashboard.service
   ```

### Database Issues

If you need to reset the database:
```bash
sudo systemctl stop revenue_dashboard
cd /home/pi/projects/revenue_dashboard
rm database.db
sudo systemctl start revenue_dashboard
```

The database will be recreated automatically on next start.

### Permission Issues

Ensure the `pi` user owns the project directory:
```bash
sudo chown -R pi:pi /home/pi/projects/revenue_dashboard
```

## Next Steps

1. **Change default password** - Log in and change the password immediately
2. **Configure settings** - Set your tax, reinvest, and take-home percentages
3. **Add work entries** - Start tracking your daily work
4. **Set up webhook** - Enable automatic deployment (optional)

For more details, see [README.md](README.md).

