import re
from flask import request, jsonify, Blueprint, current_app
from .f5tts import stream_f5tts_audio
from .gtts import stream_gtts_audio
from app.utils import scan_voice_profiles

tts_bp = Blueprint('tts', __name__)
@tts_bp.route('/stream_audio', methods=['POST'])
def stream_audio():
    current_app.logger.info("Starting audio streaming request")
    try:
        story = request.json.get('story')
        if not story:
            current_app.logger.error("No story content provided")
            return jsonify({'error': 'Story content is required'}), 400

        story = re.sub(r'[\[\]\(\)\（\）\{}\"""\'\'\"《》*#]', '', story)
        language = request.json.get('language', 'en')
        tts_service = request.json.get('tts_service', 'gtts')
        voice_profile = request.json.get('voice_profile')

        current_app.logger.info(f"Processing TTS request: service={tts_service}, language={language}")

        if tts_service == 'gtts':
            return stream_gtts_audio(story, language)
        elif tts_service == 'f5tts':
            return stream_f5tts_audio(story, language, voice_profile, current_app.config['DATABASE'])
        else:
            current_app.logger.error(f"Invalid TTS service requested: {tts_service}")
            return jsonify({'error': 'Invalid TTS service'}), 400
    except Exception as e:
        current_app.logger.error(f"Error in stream_audio: {str(e)}")
        return jsonify({'error': 'Failed to process audio stream'}), 500


@tts_bp.route('/tts-options', methods=['GET'])
def get_tts_options():
    profiles = scan_voice_profiles()
    return jsonify({
        'services': current_app.config['TTS_SERVICES'],
        'voices': profiles
    })

# @app.route('/read', methods=['POST'])
# def read():
#     story = request.json['story']
#     language = request.json.get('language', 'en')  # Default to English
#     audio_file = generate_audio(story, language)
#     return jsonify({'audio_file': audio_file})

