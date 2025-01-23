class Config:
    DATABASE = "stories.db"
    API_KEY = ""
    BASE_RUL = "https://api.deepseek.com"
    TTS_SERVICES = {
    'gtts': 'Google Text-to-Speech',
    'f5tts': 'F5 Text-to-Speech'
    }
    F5TTS_URL = 'http://localhost:8000/tts'
    ALLOW_REGISTER = False
    LOGGING_LEVEL = 'INFO'
    SECRET_KEY = 'your-secret-key-here'  # Set to True to allow user registration
    # Email Configuration
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'your-email@gmail.com'
    SMTP_PASSWORD = 'your-app-specific-password'
    SENDER_EMAIL = 'your-email@gmail.com'