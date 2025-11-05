# Earnings & Productivity Dashboard

A lightweight Flask web application designed to run on a Raspberry Pi, providing daily work entry tracking, revenue analytics, and productivity metrics with Chart.js visualizations.

## Features

- **User Authentication**: Simple local username/password authentication
- **Daily Work Entry Tracking**: Record date, hours, revenue, worker name, and notes
- **Revenue Analytics**: View totals, averages, and breakdowns by percentage
- **Interactive Charts**: Chart.js visualizations for daily/weekly/monthly trends
- **Settings Configuration**: Configure tax, reinvest, and take-home percentages
- **Auto-Deployment**: GitHub webhook-triggered automatic deployment

## Project Structure

```
/home/pi/projects/revenue_dashboard/
├── app.py                    # Flask application entry point
├── models.py                 # SQLAlchemy database models
├── config.py                 # Configuration management
├── requirements.txt          # Python dependencies
├── deploy.sh                 # Auto-deployment script
├── hooks.json                # Webhook configuration template
├── .gitignore               # Git ignore rules
├── README.md                 # This file
├── database.db               # SQLite database (auto-generated)
├── instance/
│   └── config.json          # Instance-specific config (secrets)
├── templates/
│   ├── base.html            # Base template with navigation
│   ├── login.html           # Login page
│   ├── dashboard.html       # Main dashboard with charts
│   ├── add_entry.html       # Add/edit work entry form
│   └── settings.html        # Configure percentages
├── static/
│   ├── style.css            # Custom styling
│   └── charts.js            # Chart.js initialization helpers
└── systemd/
    └── revenue_dashboard.service  # Systemd service file
```

## Prerequisites

- Raspberry Pi OS (Linux)
- Python 3.11 or higher
- Git
- Systemd (included with Raspberry Pi OS)

## Running Alongside Homebridge

This application is designed to run alongside Homebridge on the same Raspberry Pi:

- **Homebridge**: Typically runs on port 8581 (web UI) and 8087 (API)
- **Earnings Dashboard**: Runs on port 5050
- **No conflicts**: Both services use different ports and can run simultaneously
- **Minimal footprint**: Lightweight Flask app with SQLite database
- **Shared resources**: Both services run as systemd services independently

The application uses minimal resources and won't interfere with Homebridge operations.

## Initial Setup

### 1. Clone Repository

```bash
cd /home/pi/projects
git clone <your-repo-url> revenue_dashboard
cd revenue_dashboard
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Initialize Database

The database will be automatically created on first run. To manually initialize:

```bash
python3 -c "from app import app, init_db; init_db()"
```

### 5. Create Default User

The application will create a default user on first run:
- **Username**: `ellis`
- **Password**: `changeme`

**IMPORTANT**: Change the default password immediately after first login!

### 6. Configure Systemd Service

```bash
sudo cp systemd/revenue_dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable revenue_dashboard
sudo systemctl start revenue_dashboard
```

### 7. Check Service Status

```bash
sudo systemctl status revenue_dashboard
```

The application should now be accessible at `http://192.168.1.88:5050` on your local network.

**Note:** This application runs alongside Homebridge on the same Raspberry Pi. Both services can run simultaneously without conflicts.

## Configuration

### Instance Configuration

Create `instance/config.json` for production settings:

```json
{
  "SECRET_KEY": "your-secret-key-here-change-this",
  "DATABASE_URL": "sqlite:///database.db"
}
```

### Environment Variables

You can also set environment variables:

```bash
export SECRET_KEY="your-secret-key"
export FLASK_ENV="production"
export DATABASE_URL="sqlite:///database.db"
```

## GitHub Webhook Auto-Deployment

### 1. Install Webhook

```bash
# Option 1: Install from package manager (if available)
sudo apt install webhook

# Option 2: Build from source
# See: https://github.com/adnanh/webhook
```

### 2. Configure Webhook

Edit `hooks.json` and update the secret:

```json
{
  "secret": "your-webhook-secret-here-change-this"
}
```

Copy the configuration to the webhook directory:

```bash
sudo mkdir -p /etc/webhook
sudo cp hooks.json /etc/webhook/hooks.json
sudo chmod 644 /etc/webhook/hooks.json
```

### 3. Make Deploy Script Executable

```bash
chmod +x deploy.sh
```

### 4. Start Webhook Service

Create a systemd service for webhook (if not already running):

```bash
sudo systemctl start webhook
sudo systemctl enable webhook
```

### 5. Configure GitHub Webhook

1. Go to your GitHub repository
2. Navigate to **Settings** → **Webhooks**
3. Click **Add webhook**
4. Set the **Payload URL** to: `http://192.168.1.88:9000/hooks/deploy-revenue-dashboard`
5. Set **Content type** to: `application/json`
6. Set **Secret** to match the secret in `hooks.json`
7. Select **Just the push event**
8. Click **Add webhook**

### 6. Test Deployment

Push to the main branch:

```bash
git push origin main
```

The webhook should trigger `deploy.sh`, which will:
1. Pull latest changes
2. Activate virtual environment
3. Install/update dependencies
4. Restart the systemd service

## Usage

### Accessing the Dashboard

1. Open a web browser on a device connected to your local network
2. Navigate to: `http://192.168.1.88:5050`
3. Log in with your credentials

### Adding Work Entries

1. Click **Add Entry** in the navigation
2. Fill in the form:
   - Date (required)
   - Hours (required, must be > 0)
   - Revenue (required, must be >= 0)
   - Worker Name (optional)
   - Notes (optional)
3. Click **Add Entry**

### Configuring Settings

1. Click **Settings** in the navigation
2. Set your percentages:
   - Tax Percentage
   - Reinvest Percentage
   - Take-Home Percentage
3. **Note**: Percentages must sum to exactly 100%
4. Click **Save Settings**

### Viewing Analytics

The dashboard displays:
- **Total Revenue**: Sum of all entries
- **Total Hours**: Sum of all hours worked
- **Entries**: Number of work entries
- **Average Daily Revenue**: Average revenue per entry
- **Average Hours/Day**: Average hours per entry
- **Take-Home Amount**: Calculated based on settings

Charts are available for:
- **Daily**: Last 30 days
- **Weekly**: Last 12 weeks
- **Monthly**: Last 12 months

## Troubleshooting

### Service Not Starting

Check service status and logs:

```bash
sudo systemctl status revenue_dashboard
sudo journalctl -u revenue_dashboard -n 50
```

### Database Issues

If you need to reset the database:

```bash
# Stop the service
sudo systemctl stop revenue_dashboard

# Remove database
rm database.db

# Restart service (database will be recreated)
sudo systemctl start revenue_dashboard
```

### Port Conflicts

If port 5050 is already in use, modify `app.py`:

```python
app.run(host='0.0.0.0', port=5051, debug=True)  # Change port
```

And update the systemd service file accordingly.

**Note:** If you're running Homebridge, check which ports it uses:
```bash
sudo netstat -tulpn | grep homebridge
```

Homebridge typically uses port 8581 for the web UI, so there should be no conflict with port 5050. Both services can run simultaneously without issues.

### Webhook Not Triggering

1. Check webhook service status:
   ```bash
   sudo systemctl status webhook
   ```

2. Check webhook logs:
   ```bash
   sudo journalctl -u webhook -n 50
   ```

3. Verify GitHub webhook delivery in repository settings
4. Ensure firewall allows connections on port 9000

## Security Considerations

- **Change default password** immediately after first login
- **Use strong SECRET_KEY** in production
- **Restrict network access** to local network only
- **Use HTTPS** in production (requires reverse proxy setup)
- **Validate webhook secret** to prevent unauthorized deployments
- **Regular backups** of `database.db`

## Development

### Running Locally

```bash
source venv/bin/activate
python app.py
```

The application will run in debug mode on `http://localhost:5050`

### Database Models

- **User**: Authentication and user management
- **Entry**: Daily work entries with date, hours, revenue, worker, notes
- **Settings**: User-specific percentage configurations

### API Endpoints

- `GET /` - Redirect to login or dashboard
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - Logout user
- `GET /dashboard` - Main dashboard
- `GET /api/chart_data?period=daily|weekly|monthly` - Chart data JSON
- `GET /add_entry` - Add entry form
- `POST /add_entry` - Create/update entry
- `GET /delete_entry/<id>` - Delete entry
- `GET /settings` - Settings page
- `POST /settings` - Update settings

## License

This project is for personal use only. Modify and use as needed.

## Support

For issues or questions, check the logs and ensure all prerequisites are met. The application is designed to run with minimal dependencies and should work out of the box on Raspberry Pi OS.

