from flask import Flask, render_template, request, jsonify
import sqlite3
from gtts import gTTS
from openai import OpenAI
import os

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
        if language == 'zh':
            system_message = "你是一个富有创意的儿童故事作家。"
            
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Write a medium length bedtime story (around 1000 words) about {theme}. Make it appropriate for children aged 3-8."} if language == 'en' else
                {"role": "user", "content": f"写一个关于{theme}的中等长度的睡前故事（大约1000字）。故事要适合3-8岁的儿童。"}
            ],
            stream=False,
        )
        return response.choices[0].message.content
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

@app.route('/generate', methods=['POST'])
def generate():
    theme = request.json['theme']
    language = request.json.get('language', 'en')  # Default to English
    story = generate_story(theme, language)
    save_story(theme, story)
    return jsonify({'story': story})

@app.route('/read', methods=['POST'])
def read():
    story = request.json['story']
    language = request.json.get('language', 'en')  # Default to English
    audio_file = generate_audio(story, language)
    return jsonify({'audio_file': audio_file})

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
                preview = ' '.join(content.split()[:50])  # Get first 50 words
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
                return jsonify({'story': story[0]})
            else:
                return jsonify({'error': 'Story not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
