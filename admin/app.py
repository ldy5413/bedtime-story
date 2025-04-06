from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from functools import wraps
import os
from app.db import get_db_connection, get_placeholder

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    DATABASE = app.config['DATABASE']
    ADMIN_USERNAME = app.config['ADMIN_USERNAME']
    ADMIN_PASSWORD = app.config['ADMIN_PASSWORD']

    # Admin authentication
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Replace with your admin credentials
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['admin_logged_in'] = True
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials')
                
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/')
    @admin_required
    def dashboard():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get user statistics
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM stories')
                total_stories = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM voice_profiles')
                total_voice_profiles = cursor.fetchone()[0]
                
                return render_template('dashboard.html',
                                    total_users=total_users,
                                    total_stories=total_stories,
                                    total_voice_profiles=total_voice_profiles)
        except Exception as e:
            flash(f'Error: {str(e)}')
            return render_template('dashboard.html')

    @app.route('/users')
    @admin_required
    def users():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, email, created_at,
                        (SELECT COUNT(*) FROM stories WHERE stories.user_id = users.username) as story_count,
                        (SELECT COUNT(*) FROM voice_profiles WHERE voice_profiles.user_id = users.username) as profile_count
                    FROM users
                    ORDER BY created_at DESC
                ''')
                users = cursor.fetchall()
                return render_template('users.html', users=users)
        except Exception as e:
            flash(f'Error: {str(e)}')
            return render_template('users.html', users=[])

    @app.route('/delete_user/<username>', methods=['POST'])
    @admin_required
    def delete_user(username):
        try:
            placeholder = get_placeholder()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Delete user and all related data
                cursor.execute(f'DELETE FROM users WHERE username = {placeholder}', (username,))
                flash(f'User {username} deleted successfully')
        except Exception as e:
            flash(f'Error deleting user: {str(e)}')
        return redirect(url_for('users'))

    return app
