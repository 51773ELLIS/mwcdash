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
        
        # Columns to add - SQLite requires adding nullable first, then updating
        columns_to_add = [
            'daily_revenue_goal',
            'monthly_revenue_goal',
            'profitability_target',
            'profit_quota',
            'loss_quota'
        ]
        
        for col_name in columns_to_add:
            if col_name not in columns:
                print(f"Adding column {col_name}...")
                # SQLite limitation: Add as nullable first with default
                cursor.execute(f"ALTER TABLE settings ADD COLUMN {col_name} FLOAT DEFAULT 0.0")
                # Update any NULL values (shouldn't be any due to DEFAULT, but just in case)
                cursor.execute(f"UPDATE settings SET {col_name} = 0.0 WHERE {col_name} IS NULL")
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

