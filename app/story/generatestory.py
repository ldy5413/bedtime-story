from flask import request, jsonify, Response, Blueprint, current_app, session
from openai import OpenAI
import json
from app.utils import detect_language
import sqlite3
from app.auth.auth import login_required


story_bp = Blueprint('story', __name__)
@story_bp.route('/generate', methods=['GET'])
@login_required
def generate():
    current_app.logger.info("Starting story generation")
    theme = request.args.get('theme')
    language = request.args.get('language', 'en')
    
    # Get user_id from session while in request context
    user_id = session['user_id']
    
    current_app.logger.info(f"Received request - Theme: {theme}, Language: {language}")
    
    if not theme:
        current_app.logger.error("No theme provided")
        return jsonify({'error': 'Theme is required'}), 400

    input_lang = detect_language(theme)
    current_app.logger.info(f"Detected language: {input_lang}")
    
    if input_lang != language:
        current_app.logger.warning(f"Language mismatch: input={input_lang}, selected={language}")
        return jsonify({
            'warning': f'Your input appears to be in {input_lang}, but the selected language is {language}. Consider changing the language setting.',
            'story': None
        }), 400
    
    # Get the current app context
    app = current_app._get_current_object()
    
    def generate_stream():
        # Create a new application context for the generator
        with app.app_context():
            try:
                current_app.logger.info("Starting story generation stream")
                story_chunks = generate_story(theme, language)
                
                if isinstance(story_chunks, str) and story_chunks.startswith('Error'):
                    current_app.logger.error(f"Story generation failed: {story_chunks}")
                    yield f"data: {json.dumps({'error': story_chunks})}\n\n"
                    return
                    
                current_app.logger.info("Processing story chunks")
                full_story = ""
                chunk_count = 0
                
                for chunk in story_chunks:
                    chunk_count += 1
                    if hasattr(chunk.choices[0].delta, 'content'):
                        content = chunk.choices[0].delta.content
                        if content:
                            full_story += content
                            yield f"data: {json.dumps({'chunk': content, 'done': False})}\n\n"
                
                current_app.logger.info(f"Story generation complete. Total chunks: {chunk_count}")
                
                try:
                    save_story(theme, full_story, user_id)
                    current_app.logger.info("Story saved successfully")
                except Exception as e:
                    current_app.logger.error(f"Error saving story: {str(e)}")
                    
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'full_story': full_story})}\n\n"
            
            except Exception as e:
                current_app.logger.error(f"Error in generate_stream: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate_stream(), mimetype='text/event-stream')

# Generate story using OpenAI-compatible API
def generate_story(theme, language='en'):
    try:
        api_url = current_app.config['BASE_URL']
        api_key = current_app.config['API_KEY']
        
        current_app.logger.info(f"Initializing story generation with theme: {theme}, language: {language}")
        
        if not api_url or not api_key:
            current_app.logger.error("Missing API configuration")
            return "Error generating story: Missing API configuration"
            
        current_app.logger.info(f"Using API URL: {api_url}")
        
        client = OpenAI(api_key=api_key, base_url=api_url)
        
        system_message = "You are a creative children's story writer."
        content = f"Write a medium length bedtime story (around 1000 words) that combines these themes: {theme}. Make it appropriate for children aged 3-8."
        if language == 'zh':
            system_message = "你是一个富有创意的儿童故事作家。"
            content = f"写一个结合这些主题的中等长度的睡前故事（大约1000字）：{theme}。故事要适合3-8岁的儿童。"
        
        current_app.logger.info("Making API request...")
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": content},
                ],
                stream=True
            )
            current_app.logger.info("API request successful, starting stream")
            return response
        except Exception as api_error:
            error_msg = f"API request failed: {str(api_error)}"
            current_app.logger.error(error_msg)
            return f"Error generating story: {str(api_error)}"
            
    except Exception as e:
        error_msg = f"Error in generate_story: {str(e)}"
        current_app.logger.error(error_msg)
        return f"Error generating story: {str(e)}"
    
# Save story to database
def save_story(theme, content, user_id):
    try:
        current_app.logger.info(f"Attempting to save story with theme: {theme}")
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            conn.execute('''
                INSERT INTO stories (theme, content, user_id) 
                VALUES (?, ?, ?)
            ''', (theme, content, user_id))
            current_app.logger.info("Story saved successfully")
    except Exception as e:
        current_app.logger.error(f"Failed to save story: {str(e)}")
        raise