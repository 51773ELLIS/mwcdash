"""
Manual migration script to add goal fields to settings table
This handles SQLite's limitation of not allowing NOT NULL columns without defaults
Run this script: python3 migrations/add_goal_fields_manual.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text

def add_goal_fields():
    """Add goal fields to settings table"""
    with app.app_context():
        try:
            # Check if columns already exist
            conn = db.engine.connect()
            
            # Get table info
            result = conn.execute(text("PRAGMA table_info(settings)"))
            columns = [row[1] for row in result]
            
            # Add columns one by one if they don't exist
            columns_to_add = [
                ('daily_revenue_goal', 'FLOAT DEFAULT 0.0 NOT NULL'),
                ('monthly_revenue_goal', 'FLOAT DEFAULT 0.0 NOT NULL'),
                ('profitability_target', 'FLOAT DEFAULT 0.0 NOT NULL'),
                ('profit_quota', 'FLOAT DEFAULT 0.0 NOT NULL'),
                ('loss_quota', 'FLOAT DEFAULT 0.0 NOT NULL')
            ]
            
            for col_name, col_def in columns_to_add:
                if col_name not in columns:
                    print(f"Adding column {col_name}...")
                    # SQLite requires adding nullable first, then updating, then making NOT NULL
                    # But we can add with DEFAULT directly
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"✓ Column {col_name} added successfully")
                else:
                    print(f"Column {col_name} already exists, skipping...")
            
            conn.close()
            print("✓ All goal fields added successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Error adding goal fields: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = add_goal_fields()
    sys.exit(0 if success else 1)

