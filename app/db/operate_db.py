import sqlite3


def migrate_existing_stories(DATABASE):
    try:
        with sqlite3.connect(DATABASE) as conn:
            # Check existing columns
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(stories)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns
            if 'user_id' not in columns:
                print("Adding user_id column...")
                conn.execute('''
                    ALTER TABLE stories 
                    ADD COLUMN user_id TEXT DEFAULT 'valley'
                ''')
                conn.execute('''
                    UPDATE stories 
                    SET user_id = 'valley' 
                    WHERE user_id IS NULL
                ''')

            if 'favorite' not in columns:
                print("Adding favorite column...")
                conn.execute('''
                    ALTER TABLE stories 
                    ADD COLUMN favorite BOOLEAN DEFAULT FALSE
                ''')
                conn.execute('''
                    UPDATE stories 
                    SET favorite = FALSE 
                    WHERE favorite IS NULL
                ''')

            # Add audio cache table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audio_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER,
                    chunk_text TEXT NOT NULL,
                    audio_data BLOB NOT NULL,
                    voice_profile TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
                )
            ''')
    except Exception as e:
        print(f"Migration error: {str(e)}")

def cleanup_old_audio_cache(DATABASE,days=30):
    """Remove audio cache entries older than specified days"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.execute('''
                DELETE FROM audio_cache 
                WHERE created_at < datetime('now', '-? days')
            ''', (days,))
    except Exception as e:
        print(f"Error cleaning up audio cache: {str(e)}")