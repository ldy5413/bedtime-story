import sqlite3
import argparse
from werkzeug.security import generate_password_hash
import sys
import os
from config import Config
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
    db_type = Config.DB_TYPE
    
    if db_type == 'local':
        # SQLite connection
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    elif db_type == 'postgresql':
        # PostgreSQL connection
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 is required for PostgreSQL connections. Install it with 'pip install psycopg2-binary'.")
        
        conn = psycopg2.connect(
            host=Config.HOST,
            port=Config.PORT,
            user=Config.USER,
            password=Config.PASSWORD,
            database=Config.DATABASE
        )
        return conn
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def get_placeholder():
    """Get the appropriate placeholder syntax based on the configured DB_TYPE"""
    db_type = Config.DB_TYPE
    
    if db_type == 'local':
        return '?'  # SQLite uses ? for placeholders
    elif db_type == 'postgresql':
        return '%s'  # PostgreSQL uses %s for placeholders
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

# Add the parent directory to Python path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def connect_db():
    try:
        return sqlite3.connect(Config.DATABASE)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def add_user(username, password):
    """Add a new user to the database"""
    try:
        placeholder = get_placeholder()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute(f'SELECT username FROM users WHERE username = {placeholder}', (username,))
            if cursor.fetchone():
                print(f"User '{username}' already exists!")
                return False
            
            # Add new user
            password_hash = generate_password_hash(password)
            cursor.execute(
                f'INSERT INTO users (username, password_hash) VALUES ({placeholder}, {placeholder})',
                (username, password_hash)
            )
            print(f"User '{username}' created successfully!")
            return True
            
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

def update_password(username, new_password):
    """Update password for an existing user"""
    try:
        placeholder = get_placeholder()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute(f'SELECT username FROM users WHERE username = {placeholder}', (username,))
            if not cursor.fetchone():
                print(f"User '{username}' not found!")
                return False
            
            # Update password
            password_hash = generate_password_hash(new_password)
            cursor.execute(
                f'UPDATE users SET password_hash = {placeholder} WHERE username = {placeholder}',
                (password_hash, username)
            )
            print(f"Password updated for user '{username}'!")
            return True
            
    except Exception as e:
        print(f"Error updating password: {e}")
        return False

def list_users():
    """List all users in the database"""
    try:
        placeholder = get_placeholder()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username, created_at FROM users ORDER BY created_at')
            users = cursor.fetchall()
            
            if not users:
                print("No users found in database.")
                return
            
            print("\nRegistered Users:")
            print("-----------------")
            for username, created_at in users:
                print(f"Username: {username}")
                print(f"Created: {created_at}")
                print("-----------------")
            
    except Exception as e:
        print(f"Error listing users: {e}")

def main():
    parser = argparse.ArgumentParser(description='Manage users for Bedtime Story Generator')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add user command
    add_parser = subparsers.add_parser('add', help='Add a new user')
    add_parser.add_argument('username', help='Username for the new user')
    add_parser.add_argument('password', help='Password for the new user')
    
    # Update password command
    update_parser = subparsers.add_parser('update-password', help='Update user password')
    update_parser.add_argument('username', help='Username of the user')
    update_parser.add_argument('new_password', help='New password')
    
    # List users command
    subparsers.add_parser('list', help='List all users')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_user(args.username, args.password)
    elif args.command == 'update-password':
        update_password(args.username, args.new_password)
    elif args.command == 'list':
        list_users()
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 