from flask import request, jsonify, Response, Blueprint, current_app
from openai import OpenAI
import json
from app.utils import detect_language
import sqlite3


story_bp = Blueprint('story', __name__)
@story_bp.route('/generate', methods=['POST'])
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

# Generate story using OpenAI-compatible API
def generate_story(theme, language='en'):
    try:
        api_url = current_app.config['base_url']
        api_key = current_app.config['api_key']
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
    with sqlite3.connect(current_app.config['DATABASE']) as conn:
        conn.execute('''
            INSERT INTO stories (theme, content, user_id) 
            VALUES (?, ?, 'valley')
        ''', (theme, content))