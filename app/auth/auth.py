from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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