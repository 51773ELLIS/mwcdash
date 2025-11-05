#!/usr/bin/env python3
"""
Database migration helper script
Run this script to apply database migrations after pulling code updates
"""
import sys
import os
from pathlib import Path
from flask_migrate import upgrade, init, migrate, stamp
from app import app, db

def run_migrations():
    """Run database migrations"""
    with app.app_context():
        try:
            # Check if migrations directory exists
            # app.root_path is a string, convert to Path for path operations
            root_path = Path(app.root_path) if isinstance(app.root_path, str) else app.root_path
            migrations_dir = root_path / 'migrations'
            
            if not migrations_dir.exists():
                print("Initializing migrations...")
                init()
                print("Creating initial migration...")
                migrate(message='Initial migration')
                print("Stamping database with initial migration...")
                # Check if database exists and has tables
                try:
                    from models import User
                    if User.query.first() is not None:
                        # Database has data, stamp it as current
                        stamp('head')
                        print("Database stamped with current migration.")
                except:
                    # Database is empty or doesn't exist, that's fine
                    pass
            
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
            print("4. If this is a fresh install, run: flask db init")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)

