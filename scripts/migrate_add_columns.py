import sqlite3
import os

def migrate_audio_cache():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stories.db')
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        try:
            # Create temporary table with new schema
            cursor.execute('''
                CREATE TABLE audio_cache_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER,
                    chunk_text TEXT NOT NULL,
                    audio_data BLOB NOT NULL,
                    voice_profile TEXT NOT NULL,
                    user_id TEXT,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(username)
                )
            ''')
            
            # Copy existing data
            cursor.execute('''
                INSERT INTO audio_cache_new (id, story_id, chunk_text, audio_data, voice_profile, created_at)
                SELECT id, story_id, chunk_text, audio_data, voice_profile, created_at FROM audio_cache
            ''')
            
            # Drop old table and rename new one
            cursor.execute('DROP TABLE audio_cache')
            cursor.execute('ALTER TABLE audio_cache_new RENAME TO audio_cache')
            
            # Create indices for better performance
            cursor.execute('CREATE INDEX idx_user_id ON audio_cache(user_id)')
            cursor.execute('CREATE INDEX idx_language ON audio_cache(language)')
            
            print("Successfully added user_id and language columns to audio_cache table")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate_audio_cache() 