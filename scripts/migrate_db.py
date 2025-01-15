import sqlite3
import sys
import os

# Add the parent directory to Python path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def migrate_database():
    try:
        with sqlite3.connect(Config.DATABASE) as conn:
            cursor = conn.cursor()
            
            # Check if avatar_url column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'avatar_url' not in columns:
                print("Adding avatar_url column to users table...")
                # Add the new column
                cursor.execute('''
                    ALTER TABLE users 
                    ADD COLUMN avatar_url TEXT DEFAULT NULL
                ''')
                print("Migration successful!")
            else:
                print("avatar_url column already exists.")
                
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    print("Starting database migration...")
    if migrate_database():
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!") 