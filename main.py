from flask import Flask, render_template, request, jsonify, Response
import sqlite3
from gtts import gTTS
from openai import OpenAI
import os, re
import io
import json
import requests
from pathlib import Path
import mimetypes

app = Flask(__name__)
DATABASE = 'stories.db'

# Initialize database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                favorite BOOLEAN DEFAULT FALSE,
                user_id TEXT DEFAULT 'valley'
            )
        ''')
        
        # Create a new table for cached audio
        conn.execute('''
            CREATE TABLE IF NOT EXISTS audio_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id INTEGER,
                chunk_text TEXT NOT NULL,
                audio_data BLOB NOT NULL,
                voice_profile TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
            )
        ''')

# Generate story using OpenAI-compatible API
def generate_story(theme, language='en'):
    try:
        api_url = "https://api.deepseek.com"
        api_key = ""
        client = OpenAI(api_key=api_key, base_url=api_url)
        
        system_message = "You are a creative children's story writer."
        content = f"Write a medium length bedtime story (around 1000 words) that combines these themes: {theme}. Make it appropriate for children aged 3-8."
        if language == 'zh':
            system_message = "你是一个富有创意的儿童故事作家。"
            content = f"写一个结合这些主题的中等长度的睡前故事（大约1000字）：{theme}。故事要适合3-8岁的儿童。"
            
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": content},
            ],
            stream=True
        )
        return response
    except Exception as e:
        return f"Error generating story: {str(e)}"

# Save story to database
def save_story(theme, content):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            INSERT INTO stories (theme, content, user_id) 
            VALUES (?, ?, 'valley')
        ''', (theme, content))

# Generate TTS audio
def generate_audio(content, language='en'):
    lang = 'zh-cn' if language == 'zh' else 'en'
    tts = gTTS(text=content, lang=lang)
    audio_file = 'static/story.mp3'
    tts.save(audio_file)
    return f'/static/story.mp3'

# Add TTS service configuration
TTS_SERVICES = {
    'gtts': 'Google Text-to-Speech',
    'f5tts': 'F5 Text-to-Speech'
}

# Load voice profiles
def load_voice_profiles():
    profile_path = Path('voice_profiles/profiles.json')
    if profile_path.exists():
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'zh': [], 'en': []}

# Add this function to scan voice profiles
def scan_voice_profiles():
    profiles_dir = Path('voice_profiles')
    if not profiles_dir.exists():
        return {'zh': [], 'en': []}
    
    profiles = {'zh': [], 'en': []}
    
    # Get all audio files
    audio_files = [f for f in profiles_dir.glob('*') if f.suffix.lower() in ['.wav', '.mp3', '.m4a']]
    
    for audio_file in audio_files:
        base_name = audio_file.stem
        text_file = profiles_dir / f"{base_name}.txt"
        
        if text_file.exists():
            with open(text_file, 'r', encoding='utf-8') as f:
                ref_text = f.read().strip()
            
            # Detect language from the reference text
            lang = 'zh' if any('\u4e00' <= char <= '\u9fff' for char in ref_text) else 'en'
            
            profiles[lang].append({
                'id': base_name,
                'name': base_name.replace('_', ' ').title(),
                'ref_audio': str(audio_file),
                'ref_text': ref_text
            })
    
    return profiles

@app.route('/')
def index():
    return render_template('index.html')

def detect_language(text):
    """Detect if text contains Chinese characters"""
    return 'zh' if any('\u4e00' <= char <= '\u9fff' for char in text[:100]) else 'en'

@app.route('/generate', methods=['POST'])
def generate():
    theme = request.json['theme']
    language = request.json.get('language', 'en')
    
    input_lang = detect_language(theme)
    if input_lang != language:
        return jsonify({
            'warning': f'Your input appears to be in {input_lang}, but the selected language is {language}. Consider changing the language setting.',
            'story': None
        }), 400
    
    def generate_stream():
        try:
            story_chunks = generate_story(theme, language)
            if isinstance(story_chunks, str) and story_chunks.startswith('Error'):
                # Handle error from generate_story
                yield f"data: {json.dumps({'error': story_chunks})}\n\n"
                return
                
            full_story = ""
            
            for chunk in story_chunks:
                if hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_story += content
                        yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"
            
            # Save the complete story
            save_story(theme, full_story)
            yield f"data: {json.dumps({'chunk': '', 'done': True, 'full_story': full_story})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate_stream(), mimetype='text/event-stream')

@app.route('/read', methods=['POST'])
def read():
    story = request.json['story']
    language = request.json.get('language', 'en')  # Default to English
    audio_file = generate_audio(story, language)
    return jsonify({'audio_file': audio_file})

# Add new route to get available TTS services and voice profiles
@app.route('/tts-options', methods=['GET'])
def get_tts_options():
    profiles = scan_voice_profiles()
    return jsonify({
        'services': TTS_SERVICES,
        'voices': profiles
    })

# Modify the stream_audio route to handle different TTS services
@app.route('/stream_audio', methods=['POST'])
def stream_audio():
    story = request.json['story']
    story = re.sub('\[]\(\)\（\）\{}""''\"\《\》*','',story)
    language = request.json.get('language', 'en')
    tts_service = request.json.get('tts_service', 'gtts')
    voice_profile = request.json.get('voice_profile', None)

    if tts_service == 'gtts':
        return stream_gtts_audio(story, language)
    elif tts_service == 'f5tts':
        return stream_f5tts_audio(story, language, voice_profile)
    else:
        return jsonify({'error': 'Invalid TTS service'}), 400

def stream_gtts_audio(story, language):
    lang = 'zh-cn' if language == 'zh' else 'en'

    def split_into_sentences(text, max_length=200):
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += (" " + sentence).strip()
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def generate_audio_chunks():
        chunks = split_into_sentences(story, max_length=200)
        for chunk in chunks:
            tts = gTTS(text=chunk, lang=lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            yield fp.read()
            fp.close()

    return Response(generate_audio_chunks(), content_type='audio/mpeg')

def split_text_into_chunks(text, max_length=100):
    """Split text into chunks, trying to break at sentence boundaries."""
    # For Chinese text, split by punctuation
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        pattern = r'[。！？.!?]+'
    else:
        pattern = r'[.!?]+'
    
    sentences = re.split(pattern, text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def stream_f5tts_audio(story, language, voice_profile):
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

@app.route('/stories', methods=['GET'])
def get_stories():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            print("Fetching stories for user 'valley'...")  # Debug log
            cursor.execute('''
                SELECT id, theme, content, favorite 
                FROM stories 
                WHERE user_id = 'valley' 
                ORDER BY created_at DESC
            ''')
            stories = cursor.fetchall()
            print(f"Found {len(stories)} stories")  # Debug log
            
            formatted_stories = []
            for story in stories:
                story_id, theme, content, favorite = story
                preview = content[:100] if any('\u4e00' <= char <= '\u9fff' for char in content) else ' '.join(content.split()[:50])
                formatted_stories.append({
                    'id': story_id,
                    'theme': theme,
                    'preview': preview,
                    'favorite': bool(favorite)
                })
            
            return jsonify({'stories': formatted_stories})
    except Exception as e:
        print(f"Error in get_stories: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500

@app.route('/stories/<int:story_id>', methods=['GET'])
def get_story(story_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT content 
                FROM stories 
                WHERE id = ? AND user_id = 'valley'
            ''', (story_id,))
            story = cursor.fetchone()
            
            if story:
                language = detect_language(story[0])
                return jsonify({
                    'story': story[0],
                    'language': language
                })
            else:
                return jsonify({'error': 'Story not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stories/<int:story_id>', methods=['DELETE'])
def delete_story(story_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.execute('''
                DELETE FROM stories 
                WHERE id = ? AND user_id = 'valley'
            ''', (story_id,))
            return jsonify({'message': 'Story deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/play_random', methods=['GET'])
def play_random_story():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Get all story IDs
            cursor.execute('SELECT id FROM stories')
            story_ids = [row[0] for row in cursor.fetchall()]
            
            if not story_ids:
                return jsonify({'error': 'No stories available'}), 404
                
            # Select a random story ID
            import random
            random_id = random.choice(story_ids)
            
            # Get the story content
            cursor.execute('SELECT content FROM stories WHERE id = ?', (random_id,))
            story_content = cursor.fetchone()[0]
            
            # Generate audio
            language = detect_language(story_content)
            audio_file = generate_audio(story_content, language)
            
            return jsonify({
                'audio_file': audio_file,
                'story_id': random_id
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stories/<int:story_id>/favorite', methods=['POST'])
def toggle_favorite(story_id):
    try:
        data = request.json
        favorite = data.get('favorite', False)
        
        with sqlite3.connect(DATABASE) as conn:
            conn.execute('''
                UPDATE stories 
                SET favorite = ? 
                WHERE id = ? AND user_id = 'valley'
            ''', (favorite, story_id))
            return jsonify({'message': 'Favorite status updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def migrate_existing_stories():
    try:
        with sqlite3.connect(DATABASE) as conn:
            # Check existing columns
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(stories)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns
            if 'user_id' not in columns:
                print("Adding user_id column...")
                conn.execute('''
                    ALTER TABLE stories 
                    ADD COLUMN user_id TEXT DEFAULT 'valley'
                ''')
                conn.execute('''
                    UPDATE stories 
                    SET user_id = 'valley' 
                    WHERE user_id IS NULL
                ''')

            if 'favorite' not in columns:
                print("Adding favorite column...")
                conn.execute('''
                    ALTER TABLE stories 
                    ADD COLUMN favorite BOOLEAN DEFAULT FALSE
                ''')
                conn.execute('''
                    UPDATE stories 
                    SET favorite = FALSE 
                    WHERE favorite IS NULL
                ''')

            # Add audio cache table if it doesn't exist
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audio_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id INTEGER,
                    chunk_text TEXT NOT NULL,
                    audio_data BLOB NOT NULL,
                    voice_profile TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
                )
            ''')
    except Exception as e:
        print(f"Migration error: {str(e)}")

def cleanup_old_audio_cache(days=30):
    """Remove audio cache entries older than specified days"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.execute('''
                DELETE FROM audio_cache 
                WHERE created_at < datetime('now', '-? days')
            ''', (days,))
    except Exception as e:
        print(f"Error cleaning up audio cache: {str(e)}")

# Call migration when initializing the app
if __name__ == '__main__':
    init_db()
    migrate_existing_stories()
    #cleanup_old_audio_cache(30)  # Clean up audio older than 30 days
    app.run(debug=True,host='0.0.0.0')
