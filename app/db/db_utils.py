import sqlite3
import os
from flask import current_app

try:
    import psycopg2
    from psycopg2 import sql
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

def get_db_connection():
    """Get a database connection based on the configured DB_TYPE"""
    db_type = current_app.config.get('DB_TYPE', 'local')
    
    if db_type == 'local':
        # SQLite connection
        conn = sqlite3.connect(current_app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn
    elif db_type == 'postgresql':
        # PostgreSQL connection
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL connections. Install it with 'pip install psycopg2-binary'.")
        
        conn = psycopg2.connect(
            host=current_app.config.get('HOST', 'localhost'),
            port=current_app.config.get('PORT', 5432),
            user=current_app.config.get('USER', 'postgres'),
            password=current_app.config.get('PASSWORD', ''),
            database=current_app.config.get('DATABASE', 'postgres')
        )
        return conn
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def get_placeholder():
    """Get the appropriate placeholder syntax based on the configured DB_TYPE"""
    db_type = current_app.config.get('DB_TYPE', 'local')
    
    if db_type == 'local':
        return '?'  # SQLite uses ? for placeholders
    elif db_type == 'postgresql':
        return '%s'  # PostgreSQL uses %s for placeholders
    else:
        raise ValueError(f"Unsupported database type: {db_type}")