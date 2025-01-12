from flask import jsonify, Response
import sqlite3
import requests
from ..utils.utils import scan_voice_profiles, split_text_into_chunks


def stream_f5tts_audio(story, language, voice_profile,DATABASE):
    try:
        if voice_profile:
            ref_audio = voice_profile.get('ref_audio')
            ref_text = voice_profile.get('ref_text')
            voice_name = voice_profile.get('name', 'default')
        else:
            profiles = scan_voice_profiles()
            if profiles[language] and profiles[language][0]:
                ref_audio = profiles[language][0]['ref_audio']
                ref_text = profiles[language][0]['ref_text']
                voice_name = profiles[language][0].get('name', 'default')
            else:
                return jsonify({'error': f'No voice profile available for language {language}'}), 400

        # Split story into chunks
        story_chunks = split_text_into_chunks(story)
        
        def generate():
            with sqlite3.connect(DATABASE) as conn:
                for chunk in story_chunks:
                    # Check if we have this chunk cached
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT audio_data FROM audio_cache 
                        WHERE chunk_text = ? AND voice_profile = ?
                    ''', (chunk, voice_name))
                    cached_audio = cursor.fetchone()

                    if cached_audio:
                        # Use cached audio
                        yield cached_audio[0]
                    else:
                        # Generate new audio
                        response = requests.post(
                            'http://localhost:8000/tts',
                            json={
                                'text_to_generate': chunk,
                                'ref_audio': ref_audio,
                                'ref_text': ref_text,
                                'remove_silence': True,
                                'cross_fade_duration': 0.15,
                                'nfe_step': 32,
                                'speed': 1.0,
                                'response_type': 'stream'
                            }
                        )
                        
                        if response.status_code != 200:
                            raise Exception('F5 TTS API error')
                        
                        # Get the complete audio data
                        audio_data = response.content
                        
                        # Cache the audio data
                        cursor.execute('''
                            INSERT INTO audio_cache (chunk_text, audio_data, voice_profile)
                            VALUES (?, ?, ?)
                        ''', (chunk, audio_data, voice_name))
                        conn.commit()
                        
                        yield audio_data

        return Response(generate(), mimetype='audio/mpeg')
    except Exception as e:
        print(f"Error in stream_f5tts_audio: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500
