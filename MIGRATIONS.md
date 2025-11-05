# Database Migrations Guide

This application uses Flask-Migrate (Alembic) to manage database schema changes. This ensures that when you pull code updates, your database is automatically upgraded without losing any data.

## How It Works

When you pull code updates that include database changes (new models, new columns, etc.), the deployment script automatically runs migrations to update your database schema while preserving all your existing data.

## Automatic Migration

The `deploy.sh` script automatically runs migrations when you pull updates via the webhook. It will:
1. Pull latest code
2. Install/update dependencies
3. **Run database migrations** (preserves your data)
4. Restart the service

## Manual Migration

If you need to run migrations manually:

```bash
cd /home/ellis/projects/revenue_dashboard
source venv/bin/activate
python3 migrate_db.py
```

## First-Time Migration Setup

If you're upgrading from a version without migrations, you'll need to initialize migrations:

```bash
cd /home/ellis/projects/revenue_dashboard
source venv/bin/activate
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## Troubleshooting

### Migration Fails

If migrations fail, you can check the status:

```bash
flask db current
flask db history
```

### Rollback Migration

If a migration causes issues, you can rollback:

```bash
flask db downgrade -1  # Rollback one migration
```

### Manual Schema Update

If you need to manually update the schema (not recommended):

```bash
# Backup your database first!
cp database.db database.db.backup

# Then run migrations
python3 migrate_db.py
```

## Important Notes

- **Always backup your database** before running migrations manually
- Migrations preserve all existing data
- The database file is `database.db` in the project directory
- Migrations are stored in the `migrations/` directory

## Migration Files

Migration files are stored in `migrations/versions/` and should be committed to git. This ensures all deployments have the same migration history.

