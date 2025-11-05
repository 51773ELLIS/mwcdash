#!/usr/bin/env python3
"""
Fix migration script for adding goal fields to settings table
This script manually adds the columns with proper SQLite handling
"""
import sys
from pathlib import Path
import sqlite3

def fix_migration():
    """Manually add goal fields to settings table"""
    # Find database file
    db_path = Path(__file__).parent / 'database.db'
    
    if not db_path.exists():
        print(f"✗ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(settings)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Columns to add with default values
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
                # SQLite allows adding with DEFAULT directly
                cursor.execute(f"ALTER TABLE settings ADD COLUMN {col_name} {col_def}")
                print(f"✓ Column {col_name} added successfully")
            else:
                print(f"Column {col_name} already exists, skipping...")
        
        conn.commit()
        conn.close()
        
        print("✓ All goal fields added successfully!")
        print("✓ Migration completed!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = fix_migration()
    sys.exit(0 if success else 1)

