# Quick Start Guide

## Your Raspberry Pi Details

- **IP Address**: `192.168.1.88`
- **SSH Access**: `ssh pi@192.168.1.88`
- **Dashboard URL**: `http://192.168.1.88:5050`
- **Homebridge**: Already installed (no conflicts)

## Fast Deployment (5 minutes)

### Step 1: SSH into Raspberry Pi
```bash
ssh pi@192.168.1.88
```

### Step 2: Run Setup Script
```bash
cd /home/pi
wget https://raw.githubusercontent.com/51773ELLIS/mwcdash/main/setup_pi.sh
chmod +x setup_pi.sh
./setup_pi.sh
```

### Step 3: Access Dashboard
Open your browser and go to:
```
http://192.168.1.88:5050
```

### Step 4: Login
- **Username**: `ellis`
- **Password**: `changeme`

**⚠️ Change the password immediately after first login!**

## That's It!

The dashboard is now running alongside Homebridge. Both services work independently:
- Homebridge: `http://192.168.1.88:8581` (or your configured port)
- Earnings Dashboard: `http://192.168.1.88:5050`

## Quick Commands

```bash
# Check dashboard status
sudo systemctl status revenue_dashboard

# View dashboard logs
sudo journalctl -u revenue_dashboard -f

# Restart dashboard
sudo systemctl restart revenue_dashboard
```

## Next Steps

1. Change the default password
2. Configure your tax/reinvest/take-home percentages in Settings
3. Add your first work entry
4. View analytics and charts on the dashboard

For more details, see [DEPLOYMENT.md](DEPLOYMENT.md) or [README.md](README.md).

