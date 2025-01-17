import sqlite3
def init_db(DATABASE):
    with sqlite3.connect(DATABASE) as conn:
        # Create users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avatar_url TEXT DEFAULT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                favorite BOOLEAN DEFAULT FALSE,
                user_id TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(username)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS audio_cache (
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
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON audio_cache(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_language ON audio_cache(language)')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS voice_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                audio_data BLOB NOT NULL,
                reference_text TEXT NOT NULL,
                language TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(username),
                UNIQUE(user_id, name)
            )
        ''')