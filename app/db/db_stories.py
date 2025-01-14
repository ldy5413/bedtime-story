from flask import request, jsonify, Blueprint, current_app
from app.utils import detect_language
import sqlite3


db_bp = Blueprint('database', __name__)
@db_bp.route('/stories', methods=['GET'])
def get_stories():
    current_app.logger.info("Fetching stories...")
    try:
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, theme, content, favorite 
                FROM stories 
                WHERE user_id = 'valley' 
                ORDER BY created_at DESC
            ''')
            stories = cursor.fetchall()
            current_app.logger.info(f"Found {len(stories)} stories")
            
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
        current_app.logger.error(f"Error in get_stories: {str(e)}")
        return jsonify({'error': 'Failed to fetch stories'}), 500
    
@db_bp.route('/stories/<int:story_id>', methods=['GET'])
def get_story(story_id):
    try:
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
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

@db_bp.route('/stories/<int:story_id>', methods=['DELETE'])
def delete_story(story_id):
    try:
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            conn.execute('''
                DELETE FROM stories 
                WHERE id = ? AND user_id = 'valley'
            ''', (story_id,))
            return jsonify({'message': 'Story deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@db_bp.route('/stories/<int:story_id>/favorite', methods=['POST'])
def toggle_favorite(story_id):
    try:
        data = request.json
        favorite = data.get('favorite', False)
        
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            conn.execute('''
                UPDATE stories 
                SET favorite = ? 
                WHERE id = ? AND user_id = 'valley'
            ''', (favorite, story_id))
            return jsonify({'message': 'Favorite status updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500