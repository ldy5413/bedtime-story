class Config:
    DATABASE = "stories.db"
    api_key = ""
    base_url = "https://api.deepseek.com"
    TTS_SERVICES = {
    'gtts': 'Google Text-to-Speech',
    'f5tts': 'F5 Text-to-Speech'
    }
    f5tts_url = 'http://localhost:8000/tts'
