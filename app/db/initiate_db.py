import sqlite3
def init_db(DATABASE):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                favorite BOOLEAN DEFAULT FALSE,
                user_id TEXT DEFAULT 'valley'
            )
        ''')
        
        # Create a new table for cached audio
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