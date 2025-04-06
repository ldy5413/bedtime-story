import sqlite3
try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

def init_db(DATABASE, app=None):
    # Determine database type from config
    from flask import current_app
    
    # If app is provided, use its config directly
    # Otherwise, try to use current_app (requires application context)
    if app:
        config = app.config
        db_type = config.get('DB_TYPE', 'local')
    else:
        # This will only work within an application context
        db_type = current_app.config.get('DB_TYPE', 'local')
    
    if db_type == 'local':
        # SQLite initialization
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
    elif db_type == 'postgresql':
        # PostgreSQL initialization
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL connections. Install it with 'pip install psycopg2-binary'.")
        
        # Connect to PostgreSQL
        # Use the appropriate config source based on whether app was provided
        config = config if app else current_app.config
        conn = psycopg2.connect(
            host=config.get('HOST', 'localhost'),
            port=config.get('PORT', 5432),
            user=config.get('USER', 'postgres'),
            password=config.get('PASSWORD', ''),
            database=DATABASE
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avatar_url TEXT DEFAULT NULL
            )
        """)
        
        # Create stories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id SERIAL PRIMARY KEY,
                theme TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                favorite BOOLEAN DEFAULT FALSE,
                user_id TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(username)
            )
        """)
        
        # Create audio_cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_cache (
                id SERIAL PRIMARY KEY,
                story_id INTEGER,
                chunk_text TEXT NOT NULL,
                audio_data BYTEA NOT NULL,
                voice_profile TEXT NOT NULL,
                user_id TEXT,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(username)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON audio_cache(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_language ON audio_cache(language)")
        
        # Create voice_profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_profiles (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                audio_data BYTEA NOT NULL,
                reference_text TEXT NOT NULL,
                language TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(username),
                UNIQUE(user_id, name)
            )
        """)
        
        conn.close()
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
