#!/usr/bin/env python3
"""
Database migration helper script
Run this script to apply database migrations after pulling code updates
"""
import sys
from flask_migrate import upgrade, init, migrate, stamp
from app import app, db

def run_migrations():
    """Run database migrations"""
    with app.app_context():
        try:
            # Check if migrations directory exists
            migrations_dir = app.root_path / 'migrations'
            if not migrations_dir.exists():
                print("Initializing migrations...")
                init()
                print("Creating initial migration...")
                migrate(message='Initial migration')
                print("Stamping database with initial migration...")
                stamp('head')
            
            print("Applying database migrations...")
            upgrade()
            print("✓ Database migrations completed successfully!")
            print("✓ All data has been preserved.")
            return True
        except Exception as e:
            print(f"✗ Error running migrations: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure Flask-Migrate is installed: pip install Flask-Migrate")
            print("2. Check that the database file is accessible")
            print("3. Ensure you have write permissions")
            return False

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)

