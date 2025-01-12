import re
from flask import request, jsonify, Blueprint, current_app
from .f5tts import stream_f5tts_audio
from .gtts import stream_gtts_audio
from app.utils import scan_voice_profiles

tts_bp = Blueprint('tts', __name__)
@tts_bp.route('/stream_audio', methods=['POST'])
def stream_audio():
    story = request.json['story']
    story = re.sub('\[]\(\)\（\）\{}""''\"\《\》*#','',story)
    language = request.json.get('language', 'en')
    tts_service = request.json.get('tts_service', 'gtts')
    voice_profile = request.json.get('voice_profile', None)

    if tts_service == 'gtts':
        return stream_gtts_audio(story, language)
    elif tts_service == 'f5tts':
        return stream_f5tts_audio(story, language, voice_profile, current_app.config['DATABASE'])
    else:
        return jsonify({'error': 'Invalid TTS service'}), 400


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

