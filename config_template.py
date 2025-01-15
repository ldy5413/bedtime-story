class Config:
    DATABASE = "stories.db"
    API_KEY = ""
    BASE_RUL = "https://api.deepseek.com"
    TTS_SERVICES = {
    'gtts': 'Google Text-to-Speech',
    'f5tts': 'F5 Text-to-Speech'
    }
    F5TTS_URL = 'http://localhost:8000/tts'
