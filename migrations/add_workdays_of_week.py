"""
Manual migration script to add workdays_of_week field to settings table
This handles SQLite's limitation of not allowing NOT NULL columns without defaults
Run this script: python3 migrations/add_workdays_of_week.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text

def add_workdays_of_week():
    """Add workdays_of_week field to settings table"""
    with app.app_context():
        try:
            # Check if column already exists
            conn = db.engine.connect()
            
            # Get table info
            result = conn.execute(text("PRAGMA table_info(settings)"))
            columns = [row[1] for row in result]
            
            # Add column if it doesn't exist
            if 'workdays_of_week' not in columns:
                print("Adding column workdays_of_week...")
                # SQLite limitation: Add as nullable with default (can't add NOT NULL directly)
                conn.execute(text("ALTER TABLE settings ADD COLUMN workdays_of_week VARCHAR(20) DEFAULT '0,1,2,3,4'"))
                conn.commit()
                print("✓ Column workdays_of_week added successfully")
                
                # Update existing rows to have the default value
                conn.execute(text("UPDATE settings SET workdays_of_week = '0,1,2,3,4' WHERE workdays_of_week IS NULL"))
                conn.commit()
                print("✓ Existing rows updated with default workdays")
            else:
                print("Column workdays_of_week already exists, skipping...")
            
            conn.close()
            print("✓ Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Error adding workdays_of_week field: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = add_workdays_of_week()
    sys.exit(0 if success else 1)

