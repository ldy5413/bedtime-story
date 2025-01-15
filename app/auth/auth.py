from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            with sqlite3.connect(current_app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username, password_hash FROM users WHERE username = ?', (username,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user[1], password):
                    session['user_id'] = user[0]
                    return redirect(url_for('general.index'))
                else:
                    flash('Invalid username or password')
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login')
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config['ALLOW_REGISTER']:
        flash('Registration is currently disabled')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('auth/register.html')
            
        try:
            with sqlite3.connect(current_app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
                if cursor.fetchone():
                    flash('Username already exists')
                    return render_template('auth/register.html')
                    
                password_hash = generate_password_hash(password)
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                             (username, password_hash))
                flash('Registration successful! Please login.')
                return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration')
            
    return render_template('auth/register.html', allow_register=current_app.config['ALLOW_REGISTER'])

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login')) 

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    current_app.logger.info("Accessing dashboard route")
    try:
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute('''
                SELECT username, created_at, avatar_url 
                FROM users 
                WHERE username = ?
            ''', (session['user_id'],))
            user_data = cursor.fetchone()
            
            # Get statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_stories,
                    SUM(CASE WHEN favorite = 1 THEN 1 ELSE 0 END) as favorite_stories,
                    SUM(CASE WHEN created_at >= date('now', '-30 days') THEN 1 ELSE 0 END) as stories_this_month
                FROM stories 
                WHERE user_id = ?
            ''', (session['user_id'],))
            stats_data = cursor.fetchone()
            
            # Get recent activities
            cursor.execute('''
                SELECT created_at, theme 
                FROM stories 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            ''', (session['user_id'],))
            activities = cursor.fetchall()
            
            user = {
                'username': user_data[0],
                'created_at': user_data[1],
                'avatar_url': user_data[2] if user_data[2] else 'avatars/default_avatar.png'  # Set default avatar path
            }
            
            stats = {
                'total_stories': stats_data[0],
                'favorite_stories': stats_data[1],
                'stories_this_month': stats_data[2]
            }
            
            recent_activities = [{
                'date': activity[0],
                'description': f'Created story: {activity[1]}'
            } for activity in activities]
            
            return render_template('dashboard.html', 
                                 user=user, 
                                 stats=stats, 
                                 recent_activities=recent_activities)
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard')
        return redirect(url_for('general.index'))

@auth_bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('auth.dashboard'))
        
    file = request.files['avatar']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('auth.dashboard'))
        
    if not allowed_file(file.filename):
        flash('Invalid file type')
        return redirect(url_for('auth.dashboard'))
        
    if file and allowed_file(file.filename):
        try:
            # Check file size
            file.seek(0, os.SEEK_END)
            size = file.tell()
            if size > MAX_FILE_SIZE:
                flash('File size exceeds 2MB limit')
                return redirect(url_for('auth.dashboard'))
            file.seek(0)
            
            # Save file
            filename = secure_filename(f"{session['user_id']}_{int(datetime.now().timestamp())}.{file.filename.rsplit('.', 1)[1]}")
            # Update path to use app/static/avatars
            avatar_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)
            avatar_path = os.path.join(avatar_dir, filename)
            file.save(avatar_path)
            
            # Store only the relative path in database, using forward slashes
            avatar_url = 'avatars/' + filename  # Use forward slash explicitly
            
            # Update database
            with sqlite3.connect(current_app.config['DATABASE']) as conn:
                conn.execute('''
                    UPDATE users 
                    SET avatar_url = ? 
                    WHERE username = ?
                ''', (avatar_url, session['user_id']))
                
            flash('Avatar updated successfully')
        except Exception as e:
            current_app.logger.error(f"Avatar upload error: {str(e)}")
            flash('Error uploading avatar')
            
    return redirect(url_for('auth.dashboard')) 