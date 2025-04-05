import io
import re
import sqlite3
from flask import request, send_file, Blueprint, current_app, session, jsonify
from app.auth.auth import login_required
from gtts import gTTS
import requests
import base64
from app.utils import split_text_into_chunks, scan_voice_profiles

download_bp = Blueprint('download', __name__)

@download_bp.route('/download_audio', methods=['GET'])
@login_required
def download_audio():
    current_app.logger.info("Starting audio download request")
    try:
        # Get story ID from request
        story_id = request.args.get('story_id')
        tts_service = request.args.get('tts_service', 'gtts')
        
        if not story_id:
            current_app.logger.error("No story ID provided")
            return jsonify({'error': 'Story ID is required'}), 400
        
        # Get story content from database
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT content, theme 
                FROM stories 
                WHERE id = ? AND user_id = ?
            ''', (story_id, session['user_id']))
            story_data = cursor.fetchone()
            
            if not story_data:
                current_app.logger.error(f"Story not found: {story_id}")
                return jsonify({'error': 'Story not found'}), 404
            
            story, theme = story_data
            
            # Detect language from story content since it's not stored in the database
            from app.utils import detect_language
            language = detect_language(story)
        
        # Create a BytesIO object to store the audio
        audio_buffer = io.BytesIO()
        
        # Generate audio based on the selected TTS service
        if tts_service == 'gtts':
            # Clean the text for gTTS
            story = re.sub(r'[\[\]\(\)\（\）\{}\"""\'\'\"《》*#]', '', story)
            
            # Generate audio with gTTS
            lang = 'zh-cn' if language == 'zh' else 'en'
            tts = gTTS(text=story, lang=lang)
            tts.write_to_fp(audio_buffer)
        
        elif tts_service == 'f5tts':
            # Clean the text for F5TTS
            story = re.sub(r'《》*#', '', story)
            
            # Get voice profile
            voice_profile = None
            profiles = scan_voice_profiles()
            
            if profiles.get(language) and profiles[language]:
                ref_audio = profiles[language][0]['ref_audio']
                # Convert bytes to base64 string if ref_audio is in bytes
                if isinstance(ref_audio, bytes):
                    ref_audio = {'data': base64.b64encode(ref_audio).decode('utf-8'), 'type': 'base64'}
                ref_text = profiles[language][0]['ref_text']
                voice_name = profiles[language][0].get('name', 'default')
            else:
                current_app.logger.error(f"No voice profile available for language {language}")
                return jsonify({'error': f'No voice profile available for language {language}'}), 400
            
            # Split story into chunks
            story_chunks = split_text_into_chunks(story)
            
            # Process each chunk and combine the audio
            current_app.logger.info(f"Processing {len(story_chunks)} chunks for story ID {story_id}")
            
            # Create a list to store all audio data chunks
            audio_data_chunks = []
            total_audio_size = 0
            
            for i, chunk in enumerate(story_chunks):
                try:
                    current_app.logger.info(f"Processing chunk {i+1}/{len(story_chunks)}")
                    # Check if chunk is in cache
                    cursor.execute('''
                        SELECT audio_data FROM audio_cache 
                        WHERE chunk_text = ? AND voice_profile = ? 
                        AND (user_id = ? OR user_id IS NULL)
                        AND language = ?
                    ''', (chunk, voice_name, session['user_id'], language))
                    cached_audio = cursor.fetchone()
                    
                    if cached_audio and cached_audio[0]:
                        # Store cached audio data
                        current_app.logger.info(f"Using cached audio for chunk {i+1}, size: {len(cached_audio[0])} bytes")
                        audio_data_chunks.append(cached_audio[0])
                        total_audio_size += len(cached_audio[0])
                    else:
                        # Generate new audio
                        current_app.logger.info(f"Generating new audio for chunk {i+1}")
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
                        
                        # Verify the response content is valid audio data
                        if response.content and len(response.content) > 0:
                            # Store the audio data
                            current_app.logger.info(f"Received audio for chunk {i+1}, size: {len(response.content)} bytes")
                            audio_data_chunks.append(response.content)
                            total_audio_size += len(response.content)
                            
                            # Cache the audio data
                            cursor.execute('''
                                INSERT INTO audio_cache (
                                    chunk_text, audio_data, voice_profile, 
                                    user_id, language
                                )
                                VALUES (?, ?, ?, ?, ?)
                            ''', (chunk, response.content, voice_name, 
                                  session['user_id'], language))
                            conn.commit()
                        else:
                            current_app.logger.error(f"Received empty audio data for chunk {i+1}")
                except Exception as e:
                    current_app.logger.error(f"Error processing chunk {i+1}: {str(e)}")
                    raise
                    
            current_app.logger.info(f"Processed all chunks. Total audio size: {total_audio_size} bytes")
            if total_audio_size == 0:
                current_app.logger.error("No valid audio data was generated")
                return jsonify({'error': 'Failed to generate audio data'}), 500
        else:
            current_app.logger.error(f"Invalid TTS service requested: {tts_service}")
            return jsonify({'error': 'Invalid TTS service'}), 400
            
        # Write all audio data to the buffer in sequence
        current_app.logger.info(f"Writing {len(audio_data_chunks)} audio chunks to buffer")
        
        # We need to properly handle MP3 files to ensure correct metadata
        # First, let's install the necessary library if it's not already installed
        try:
            from pydub import AudioSegment
        except ImportError:
            current_app.logger.info("Installing pydub for MP3 processing")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pydub"])
            from pydub import AudioSegment
        
        # Create a combined audio segment
        combined = None
        for i, audio_data in enumerate(audio_data_chunks):
            if not audio_data:
                current_app.logger.warning("Encountered empty audio chunk, skipping")
                continue
                
            current_app.logger.info(f"Processing chunk {i+1} of size {len(audio_data)} bytes")
            
            # Create a temporary file for this chunk
            chunk_buffer = io.BytesIO(audio_data)
            chunk_buffer.seek(0)
            
            # Load the audio segment
            try:
                segment = AudioSegment.from_mp3(chunk_buffer)
                if combined is None:
                    combined = segment
                else:
                    combined += segment
            except Exception as e:
                current_app.logger.error(f"Error processing audio chunk {i+1}: {str(e)}")
        
        # Export the combined audio to a buffer with proper MP3 headers
        audio_buffer = io.BytesIO()
        if combined:
            current_app.logger.info(f"Exporting combined audio of length {len(combined)} ms")
            combined.export(audio_buffer, format="mp3")
            audio_buffer.seek(0)
        else:
            current_app.logger.error("Failed to create combined audio")
            return jsonify({'error': 'Failed to generate audio file'}), 500
        
        # Create a sanitized filename
        safe_theme = re.sub(r'[^\w\s-]', '', theme).strip().replace(' ', '_')
        filename = f"{safe_theme}_story_{story_id}.mp3"
        
        # Send the file
        return send_file(
            audio_buffer,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in download_audio: {str(e)}")
        return jsonify({'error': 'Failed to generate audio file'}), 500