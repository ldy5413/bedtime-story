import sqlite3

def add_email_column(DATABASE):
    """Add email column to users table if it doesn't exist"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # Check if users table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """)
            if not cursor.fetchone():
                print("Users table doesn't exist yet")
                return
            
            # Check if email column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'email' not in columns:
                print("Adding email column to users table...")
                
                # Create a new table with the desired schema
                cursor.execute('''
                    CREATE TABLE users_new (
                        username TEXT PRIMARY KEY,
                        email TEXT UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        avatar_url TEXT
                    )
                ''')
                
                # Copy data from the old table to the new table
                cursor.execute('''
                    INSERT INTO users_new (username, password_hash, created_at, avatar_url)
                    SELECT username, password_hash, created_at, avatar_url
                    FROM users
                ''')
                
                # Update email for existing users
                cursor.execute('''
                    UPDATE users_new 
                    SET email = username || '@placeholder.com'
                ''')
                
                # Drop the old table
                cursor.execute('DROP TABLE users')
                
                # Rename the new table to the original name
                cursor.execute('ALTER TABLE users_new RENAME TO users')
                
                print("Email column added successfully")
            else:
                print("Email column already exists")
                
    except Exception as e:
        print(f"Error adding email column: {str(e)}")
        raise e

if __name__ == "__main__":
    add_email_column('stories.db')
