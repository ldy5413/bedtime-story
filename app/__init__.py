from flask import Flask
from app.db import init_db
from app.utils.logger import setup_logger

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Setup logging
    app = setup_logger(app)
    
    # Initialize the database
    try:
        init_db(app.config['DATABASE'])
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization failed: {str(e)}")
    
    # Register blueprints
    try:
        from .story import story_bp
        from .tts import tts_bp
        from .db import db_bp
        from .general import general_bp
        
        app.register_blueprint(story_bp)
        app.register_blueprint(tts_bp)
        app.register_blueprint(db_bp)
        app.register_blueprint(general_bp)
        app.logger.info("All blueprints registered successfully")
    except Exception as e:
        app.logger.error(f"Blueprint registration failed: {str(e)}")

    return app