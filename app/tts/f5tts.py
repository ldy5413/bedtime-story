from flask import jsonify, Response, current_app
import sqlite3
import requests
from app.utils import scan_voice_profiles, split_text_into_chunks

def stream_f5tts_audio(story, language, voice_profile, DATABASE):
    current_app.logger.info(f"Starting F5TTS streaming for language: {language}")
    
    # Get the current app context
    app = current_app._get_current_object()
    
    try:
        if voice_profile:
            ref_audio = voice_profile.get('ref_audio')
            ref_text = voice_profile.get('ref_text')
            voice_name = voice_profile.get('name', 'default')
            
            if not all([ref_audio, ref_text]):
                current_app.logger.error("Invalid voice profile configuration")
                return jsonify({'error': 'Invalid voice profile'}), 400
        else:
            profiles = scan_voice_profiles()
            if not profiles.get(language) or not profiles[language]:
                current_app.logger.error(f"No voice profile available for language {language}")
                return jsonify({'error': f'No voice profile available for language {language}'}), 400
            
            ref_audio = profiles[language][0]['ref_audio']
            ref_text = profiles[language][0]['ref_text']
            voice_name = profiles[language][0].get('name', 'default')

        story_chunks = split_text_into_chunks(story)
        current_app.logger.info(f"Split story into {len(story_chunks)} chunks")

        def generate():
            # Create a new application context for the generator
            with app.app_context():
                with sqlite3.connect(DATABASE) as conn:
                    for i, chunk in enumerate(story_chunks):
                        try:
                            cursor = conn.cursor()
                            cursor.execute('''
                                SELECT audio_data FROM audio_cache 
                                WHERE chunk_text = ? AND voice_profile = ?
                            ''', (chunk, voice_name))
                            cached_audio = cursor.fetchone()

                            if cached_audio:
                                current_app.logger.debug(f"Using cached audio for chunk {i+1}")
                                yield cached_audio[0]
                            else:
                                current_app.logger.debug(f"Generating new audio for chunk {i+1}")
                                response = requests.post(
                                    current_app.config['F5TTS_URL'],
                                    json={
                                        'text_to_generate': chunk,
                                        'ref_audio': ref_audio,
                                        'ref_text': ref_text,
                                        'remove_silence': True,
                                        'cross_fade_duration': 0.15,
                                        'nfe_step': 32,
                                        'speed': 1.0,
                                        'response_type': 'stream'
                                    },
                                    timeout=30
                                )
                                
                                if response.status_code != 200:
                                    raise Exception(f'F5 TTS API error: {response.status_code}')
                                
                                audio_data = response.content
                                cursor.execute('''
                                    INSERT INTO audio_cache (chunk_text, audio_data, voice_profile)
                                    VALUES (?, ?, ?)
                                ''', (chunk, audio_data, voice_name))
                                conn.commit()
                                yield audio_data
                        except Exception as e:
                            current_app.logger.error(f"Error processing chunk {i+1}: {str(e)}")
                            raise

        return Response(generate(), mimetype='audio/mpeg')
    except Exception as e:
        current_app.logger.error(f"Error in stream_f5tts_audio: {str(e)}")
        return jsonify({'error': str(e)}), 500
