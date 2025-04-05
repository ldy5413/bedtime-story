import re
from flask import request, jsonify, Blueprint, current_app, session
from .f5tts import stream_f5tts_audio
from .gtts import stream_gtts_audio
from app.utils import scan_voice_profiles
import sqlite3

tts_bp = Blueprint('tts', __name__)
@tts_bp.route('/stream_audio', methods=['POST'])
def stream_audio():
    current_app.logger.info("Starting audio streaming request")
    try:
        story = request.json.get('story')
        if not story:
            current_app.logger.error("No story content provided")
            return jsonify({'error': 'Story content is required'}), 400


        language = request.json.get('language', 'en')
        tts_service = request.json.get('tts_service', 'gtts')
        voice_profile = request.json.get('voice_profile')
        #import pdb; pdb.set_trace()
        current_app.logger.info(f"Voice profile: {voice_profile}")
        # Load voice profile from database if provided
        if voice_profile  and 'user_id' in session:
            try:
                with sqlite3.connect(current_app.config['DATABASE']) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, audio_data, reference_text, language, name
                        FROM voice_profiles 
                        WHERE user_id = ? AND id = ?
                    ''', (session['user_id'], voice_profile))
                    profile_data = cursor.fetchone()
                    
                    if profile_data:
                        voice_profile={
                            'id': profile_data[0],
                            'ref_audio': profile_data[1],
                            'ref_text': profile_data[2],
                            'language': profile_data[3],
                            'name': profile_data[4]
                        }
                    else:
                        current_app.logger.warning(f"Voice profile not found: {voice_profile['name']}")
                        voice_profile = None
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


@tts_bp.route('/tts-options')
def get_tts_options():
    try:
        # Get user's voice profiles
        if 'user_id' in session:
            with sqlite3.connect(current_app.config['DATABASE']) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, language 
                    FROM voice_profiles 
                    WHERE user_id = ?
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

# @app.route('/read', methods=['POST'])
# def read():
#     story = request.json['story']
#     language = request.json.get('language', 'en')  # Default to English
#     audio_file = generate_audio(story, language)
#     return jsonify({'audio_file': audio_file})

