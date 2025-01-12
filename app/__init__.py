from app.db import init_db
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    print(app.config['DATABASE'])
    
    # Initialize the database
    init_db(app.config['DATABASE'])
    print("Database initialized")
    # Register blueprints
    from .story import story_bp
    from .tts import tts_bp
    from .db import db_bp
    from .general import general_bp
    app.register_blueprint(story_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(db_bp)
    app.register_blueprint(general_bp)
    print("Blueprints registered")

    return app