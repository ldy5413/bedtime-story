from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.db_utils import get_db_connection, get_placeholder
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import base64
from app.utils import detect_language
import io
from app.utils.email_service import send_verification_email, generate_verification_code

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
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholder = get_placeholder()
            cursor.execute(f'SELECT username, password_hash FROM users WHERE username = {placeholder}', (username,))            
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
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        verification_code = request.form.get('verification_code')
        
        if not username or not password or not email:
            flash('All fields are required')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('auth/register.html')
            
        try:
            # Get verification data from session
            verification_data = session.get('verification_data')
            
            if not verification_data:
                flash('Please request a verification code first')
                return render_template('auth/register.html')
            
            # Convert expiry time to naive datetime for comparison
            expiry_time = verification_data['expires'].replace(tzinfo=None)
            if datetime.now() > expiry_time:
                session.pop('verification_data', None)
                flash('Verification code expired')
                return render_template('auth/register.html')
            
            if verification_code != verification_data['code']:
                flash('Invalid verification code')
                return render_template('auth/register.html')
            
            # If verification successful, create the user
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholder = get_placeholder()
            password_hash = generate_password_hash(password)
            try:
                cursor.execute(f'''
                    INSERT INTO users (username, email, password_hash) 
                    VALUES ({placeholder}, {placeholder}, {placeholder})
                ''', (username, email, password_hash))
                conn.commit()
            finally:
                conn.close()
                
            # Clear verification data
            session.pop('verification_data', None)
            
            # Return success response
            return jsonify({
                'success': True,
                'message': 'Registration successful! Redirecting to login...'
            })
                
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'An error occurred during registration'
            })
            
    return render_template('auth/register.html')

@auth_bp.route('/verify_email', methods=['POST'])
def verify_email():
    verification_code = request.form.get('verification_code')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Get verification data from session
    verification_data = session.get('verification_data')
    
    if not verification_data:
        flash('Verification session expired')
        return redirect(url_for('auth.register'))
        
    if datetime.now() > verification_data['expires']:
        session.pop('verification_data', None)
        flash('Verification code expired')
        return redirect(url_for('auth.register'))
        
    if verification_code != verification_data['code']:
        flash('Invalid verification code')
        return render_template('auth/register.html', 
                             show_verification=True,
                             email=email,
                             username=username,
                             password=password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        password_hash = generate_password_hash(password)
        cursor.execute(f'''
            INSERT INTO users (username, email, password_hash) 
            VALUES ({placeholder}, {placeholder}, {placeholder})
        ''', (username, email, password_hash))
        conn.commit()
        conn.close()
            
        # Clear verification data
        session.pop('verification_data', None)
        flash('Registration successful! Please login.')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        flash('An error occurred during registration')
        return redirect(url_for('auth.register'))

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
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        
        # Get user info
        cursor.execute(f'''
            SELECT username, created_at, avatar_url 
            FROM users 
            WHERE username = {placeholder}
        ''', (session['user_id'],))
        user_data = cursor.fetchone()
            
            # Get statistics
        db_type = current_app.config.get('DB_TYPE', 'local')
        date_function = "date('now', '-30 days')" if db_type == 'local' else "CURRENT_DATE - INTERVAL '30 days'"
            
        # Use different syntax for boolean comparison based on database type
        favorite_condition = "favorite = TRUE" if db_type == 'postgresql' else "favorite = 1"
        
        cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_stories,
                    SUM(CASE WHEN {favorite_condition} THEN 1 ELSE 0 END) as favorite_stories,
                    SUM(CASE WHEN created_at >= {date_function} THEN 1 ELSE 0 END) as stories_this_month
                FROM stories 
                WHERE user_id = {placeholder}
            ''', (session['user_id'],))
        stats_data = cursor.fetchone()
            
            # Get recent activities
        cursor.execute(f'''
                SELECT created_at, theme 
                FROM stories 
                WHERE user_id = {placeholder} 
                ORDER BY created_at DESC 
                LIMIT 5
            ''', (session['user_id'],))
        activities = cursor.fetchall()
            
            # Get voice profiles
        cursor.execute(f'''
                SELECT id, name, language, created_at, reference_text 
                FROM voice_profiles 
                WHERE user_id = {placeholder} 
                ORDER BY created_at DESC
            ''', (session['user_id'],))
        voice_profiles = [{
                'id': row[0],
                'name': row[1],
                'language': row[2],
                'created_at': row[3],
                'reference_text': row[4]
            } for row in cursor.fetchall()]
            
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
                                 recent_activities=recent_activities,
                                 voice_profiles=voice_profiles)

    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard')
        return redirect(url_for('general.index'))
    finally:
        conn.close()
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
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholder = get_placeholder()
            try:
                cursor.execute(f'''
                    UPDATE users 
                    SET avatar_url = {placeholder} 
                    WHERE username = {placeholder}
                ''', (avatar_url, session['user_id']))
                conn.commit()
            finally:
                conn.close()
                
            flash('Avatar updated successfully')
        except Exception as e:
            current_app.logger.error(f"Avatar upload error: {str(e)}")
            flash('Error uploading avatar')
            
    return redirect(url_for('auth.dashboard')) 

@auth_bp.route('/create_voice_profile', methods=['POST'])
@login_required
def create_voice_profile():
    try:
        name = request.form.get('name')
        reference_text = request.form.get('reference_text')
        input_method = request.form.get('input_method')
        
        if not name or not reference_text:
            flash('Profile name and reference text are required')
            return redirect(url_for('auth.dashboard'))
            
        # Detect language of reference text
        language = detect_language(reference_text)
        
        # Get audio data based on input method
        if input_method == 'upload':
            if 'audio_file' not in request.files:
                flash('No audio file uploaded')
                return redirect(url_for('auth.dashboard'))
                
            audio_file = request.files['audio_file']
            if audio_file.filename == '':
                flash('No audio file selected')
                return redirect(url_for('auth.dashboard'))
                
            audio_data = audio_file.read()
        else:  # input_method == 'record'
            recorded_audio = request.form.get('recorded_audio')
            if not recorded_audio:
                flash('No recorded audio data received')
                return redirect(url_for('auth.dashboard'))
                
            try:
                # Handle the complete base64 string (including data URI prefix)
                if ',' in recorded_audio:
                    # Split off the data URI prefix if present
                    recorded_audio = recorded_audio.split(',', 1)[1]
                
                # Ensure the base64 string is properly padded
                padding = 4 - (len(recorded_audio) % 4)
                if padding != 4:
                    recorded_audio += '=' * padding
                
                # Convert base64 to binary
                audio_data = base64.b64decode(recorded_audio)
                
                # Debug logging
                current_app.logger.info(f"Decoded audio data size: {len(audio_data)} bytes")
                
            except Exception as e:
                current_app.logger.error(f"Error decoding base64 audio: {str(e)}")
                flash('Error processing recorded audio')
                return redirect(url_for('auth.dashboard'))
        
        # Debug logging
        current_app.logger.info(f"Creating voice profile: {name}, Language: {language}")
        current_app.logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        try:
            cursor.execute(f'''
                INSERT INTO voice_profiles (user_id, name, audio_data, reference_text, language)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            ''', (session['user_id'], name, audio_data, reference_text, language))
            conn.commit()
        finally:
            conn.close()
            
        flash('Voice profile created successfully')
    except Exception as e:
        current_app.logger.error(f"Error creating voice profile: {str(e)}")
        flash('Error creating voice profile')
        
    return redirect(url_for('auth.dashboard'))

@auth_bp.route('/profile_audio/<int:profile_id>')
@login_required
def get_profile_audio(profile_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        try:
            cursor.execute(f'''
                SELECT audio_data FROM voice_profiles 
                WHERE id = {placeholder} AND user_id = {placeholder}
            ''', (profile_id, session['user_id']))
            result = cursor.fetchone()
            
            if result:
                return send_file(
                    io.BytesIO(result[0]),
                    mimetype='audio/wav'
                )
        finally:
            conn.close()
    except Exception as e:
        current_app.logger.error(f"Error retrieving profile audio: {str(e)}")
    return '', 404 

@auth_bp.route('/delete_voice_profile/<int:profile_id>', methods=['POST'])
@login_required
def delete_voice_profile(profile_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        try:
            # Verify ownership before deleting
            cursor.execute(f'''
                DELETE FROM voice_profiles 
                WHERE id = {placeholder} AND user_id = {placeholder}
            ''', (profile_id, session['user_id']))
            conn.commit()
        finally:
            conn.close()
            
        flash('Voice profile deleted successfully')
    except Exception as e:
        current_app.logger.error(f"Error deleting voice profile: {str(e)}")
        flash('Error deleting voice profile')
        
    return redirect(url_for('auth.dashboard')) 

@auth_bp.route('/voice_profiles')
@login_required
def get_voice_profiles():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        try:
            cursor.execute(f'''
                SELECT id, name, language 
                FROM voice_profiles 
                WHERE user_id = {placeholder} 
                ORDER BY name
            ''', (session['user_id'],))
            profiles = [{
                'id': row[0],
                'name': row[1],
                'language': row[2]
            } for row in cursor.fetchall()]
            
            return jsonify({'profiles': profiles})
        finally:
            conn.close()
    except Exception as e:
        current_app.logger.error(f"Error fetching voice profiles: {str(e)}")
        return jsonify({'error': 'Failed to fetch voice profiles'}), 500 

@auth_bp.route('/send_verification', methods=['POST'])
def send_verification():
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username')
        
        if not email or not username:
            return jsonify({'success': False, 'message': 'Email and username are required'}), 400
            
        # Check if username exists
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholder = get_placeholder()
        try:
            cursor.execute(f'SELECT username FROM users WHERE username = {placeholder}', (username,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Username already exists'}), 400
            
            # Check if email exists
            cursor.execute(f'SELECT email FROM users WHERE email = {placeholder}', (email,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
        finally:
            conn.close()
        
        # Generate verification code
        verification_code = generate_verification_code()
        
        # Store verification data in session with naive datetime
        session['verification_data'] = {
            'code': verification_code,
            'email': email,
            'username': username,
            'expires': datetime.now().replace(tzinfo=None) + timedelta(minutes=10)
        }
        
        # Send verification email
        if send_verification_email(email, verification_code):
            return jsonify({'success': True, 'message': 'Verification code sent'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send verification code'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error sending verification code: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500