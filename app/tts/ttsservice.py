import re
import sqlite3
from flask import request, jsonify, Blueprint, current_app, session
from .f5tts import stream_f5tts_audio
from .gtts import stream_gtts_audio
from app.utils import scan_voice_profiles
from app.db import get_db_connection, get_placeholder

tts_bp = Blueprint('tts', __name__)
@tts_bp.route('/stream_audio', methods=['POST'])
def stream_audio():
    current_app.logger.info("Starting audio streaming request")
    conn = None
    try:
        story = request.json.get('story')
        if not story:
            current_app.logger.error("No story content provided")
            return jsonify({'error': 'Story content is required'}), 400


        language = request.json.get('language', 'en')
        tts_service = request.json.get('tts_service', 'gtts')
        voice_profile = request.json.get('voice_profile')
        current_app.logger.info(f"Voice profile: {voice_profile}")
        # Load voice profile from database if provided
        if voice_profile and 'user_id' in session:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                placeholder = get_placeholder()
                cursor.execute(f'''
                    SELECT id, audio_data, reference_text, language, name
                    FROM voice_profiles 
                    WHERE user_id = {placeholder} AND id = {placeholder}
                ''', (session['user_id'], voice_profile))
                profile_data = cursor.fetchone()
                
                if profile_data:
                    voice_profile = {
                        'id': profile_data[0],
                        'ref_audio': profile_data[1],
                        'ref_text': profile_data[2],
                        'language': profile_data[3],
                        'name': profile_data[4]
                    }
                else:
                    current_app.logger.warning(f"Voice profile not found: {voice_profile}")
                    voice_profile = None
                
                # Close the connection after use
                conn.close()
                conn = None
            except Exception as e:
                current_app.logger.error(f"Error loading voice profile: {str(e)}")
                voice_profile = None

        current_app.logger.info(f"Processing TTS request: service={tts_service}, language={language}")

        if tts_service == 'gtts':
            story = re.sub(r'[\[\]\(\)\（\）\{}\"""\'\'\"《》*#]', '', story)
            return stream_gtts_audio(story, language)
        elif tts_service == 'f5tts':
            story = re.sub(r'[《》*#]', '', story)
            return stream_f5tts_audio(story, language, voice_profile, current_app.config['DATABASE'])
        else:
            current_app.logger.error(f"Invalid TTS service requested: {tts_service}")
            return jsonify({'error': 'Invalid TTS service'}), 400
    except Exception as e:
        current_app.logger.error(f"Error in stream_audio: {str(e)}")
        return jsonify({'error': 'Failed to process audio stream'}), 500
    finally:
        if conn:
            conn.close()


@tts_bp.route('/tts-options')
def get_tts_options():
    conn = None
    try:
        # Get user's voice profiles
        if 'user_id' in session:
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholder = get_placeholder()
            cursor.execute(f'''
                SELECT id, name, language 
                FROM voice_profiles 
                WHERE user_id = {placeholder}
            ''', (session['user_id'],))
            profiles = [{
                'id': row[0],
                'name': row[1],
                'language': row[2]
            } for row in cursor.fetchall()]
            
            return jsonify({'voices': profiles})
        return jsonify({'voices': []})
    except Exception as e:
        current_app.logger.error(f"Error fetching TTS options: {str(e)}")
        return jsonify({'error': 'Failed to fetch TTS options'}), 500
    finally:
        if conn:
            conn.close()

# @app.route('/read', methods=['POST'])
# def read():
#     story = request.json['story']
#     language = request.json.get('language', 'en')  # Default to English
#     audio_file = generate_audio(story, language)
#     return jsonify({'audio_file': audio_file})

