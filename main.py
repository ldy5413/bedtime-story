from flask import Flask, render_template, request, jsonify, Response
import sqlite3
from gtts import gTTS
from openai import OpenAI
import os, re
import io

app = Flask(__name__)
DATABASE = 'stories.db'

# Initialize database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS stories
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         theme TEXT,
                         content TEXT,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

# Generate story using OpenAI-compatible API
def generate_story(theme, language='en'):
    try:
        api_url = "https://api.deepseek.com"  # Replace with actual API base URL
        api_key = ""       # Replace with actual API key
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
            stream=False,
        )
        story = response.choices[0].message.content
        #story = re.sub('[]()（）{}“”‘’"《》*','',story)
        return story
    except Exception as e:
        return f"Error generating story: {str(e)}"

# Save story to database
def save_story(theme, content):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('INSERT INTO stories (theme, content) VALUES (?, ?)',
                    (theme, content))

# Generate TTS audio
def generate_audio(content, language='en'):
    lang = 'zh-cn' if language == 'zh' else 'en'
    tts = gTTS(text=content, lang=lang)
    audio_file = 'static/story.mp3'
    tts.save(audio_file)
    return f'/static/story.mp3'

@app.route('/')
def index():
    return render_template('index.html')

def detect_language(text):
    """Detect if text contains Chinese characters"""
    return 'zh' if any('\u4e00' <= char <= '\u9fff' for char in text[:100]) else 'en'

@app.route('/generate', methods=['POST'])
def generate():
    theme = request.json['theme']
    language = request.json.get('language', 'en')  # Default to English
    
    # Detect input language
    input_lang = detect_language(theme)
    if input_lang != language:
        return jsonify({
            'warning': f'Your input appears to be in {input_lang}, but the selected language is {language}. Consider changing the language setting.',
            'story': None
        }), 400
    
    story = generate_story(theme, language)
    save_story(theme, story)
    return jsonify({'story': story})

@app.route('/read', methods=['POST'])
def read():
    story = request.json['story']
    language = request.json.get('language', 'en')  # Default to English
    audio_file = generate_audio(story, language)
    return jsonify({'audio_file': audio_file})

# @app.route('/stream_audio', methods=['POST'])
# def stream_audio():
#     story = request.json['story']
#     language = request.json.get('language', 'en')  # Default to English
#     lang = 'zh-cn' if language == 'zh' else 'en'
    
#     def generate():
#         # Split story into smaller chunks for faster initial response
#         chunk_size = 100  # Smaller chunks for faster initial audio
#         for i in range(0, len(story), chunk_size):
#             chunk = story[i:i + chunk_size]
#             tts = gTTS(text=chunk, lang=lang)
#             fp = io.BytesIO()
#             tts.write_to_fp(fp)
#             fp.seek(0)
#             yield fp.read()
#             fp.close()
#             # Flush the buffer to ensure immediate streaming
#             # if i == 0:
#             #     import sys
#             #     sys.stdout.flush()

#     # Set headers for immediate streaming
#     headers = {
#         'Cache-Control': 'no-cache',
#         'Content-Type': 'audio/mpeg',
#         'Transfer-Encoding': 'chunked'
#     }
#     return Response(generate(), headers=headers, mimetype='audio/mpeg')
@app.route('/stream_audio', methods=['POST'])
def stream_audio():
    story = request.json['story']
    story = re.sub('\[]\(\)\（\）\{}“”‘’"《》*','',story)
    language = request.json.get('language', 'en')  # Default to English
    lang = 'zh-cn' if language == 'zh' else 'en'

    def split_into_sentences(text, max_length=200):
        """
        Split text into chunks based on sentence boundaries, ensuring chunks are not too large.
        """
        # Use regex to split by sentence boundaries
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Check if adding the next sentence exceeds max_length
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += (" " + sentence).strip()
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence

        # Add the last chunk if any
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def generate_audio_chunks():
        # Split story into sentence-safe chunks
        chunks = split_into_sentences(story, max_length=200)
        for chunk in chunks:
            tts = gTTS(text=chunk, lang=lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            yield fp.read()
            fp.close()

    return Response(generate_audio_chunks(), content_type='audio/mpeg')
@app.route('/stories', methods=['GET'])
def get_stories():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, theme, content FROM stories ORDER BY created_at DESC')
            stories = cursor.fetchall()
            
            formatted_stories = []
            for story in stories:
                story_id, theme, content = story
                # For Chinese, take first 100 characters; for others, first 50 words
                preview = content[:100] if any('\u4e00' <= char <= '\u9fff' for char in content) else ' '.join(content.split()[:50])
                formatted_stories.append({
                    'id': story_id,
                    'theme': theme,
                    'preview': preview
                })
            
            return jsonify({'stories': formatted_stories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stories/<int:story_id>', methods=['GET'])
def get_story(story_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM stories WHERE id = ?', (story_id,))
            story = cursor.fetchone()
            
            if story:
                # Detect the language of the story content
                language = detect_language(story[0])
                #formatted_content = re.sub('[]()（）{}“”‘’"《》*','',story)
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
            conn.execute('DELETE FROM stories WHERE id = ?', (story_id,))
            return jsonify({'message': 'Story deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True,host='0.0.0.0')
