import re
from pathlib import Path

def split_text_into_chunks(text, max_length=100):
    """Split text into chunks, trying to break at sentence boundaries."""
    # For Chinese text, split by punctuation
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        pattern = r'[。！？.!?]+'
    else:
        pattern = r'[.!?]+'
    
    sentences = re.split(pattern, text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def scan_voice_profiles():
    profiles_dir = Path('voice_profiles')
    if not profiles_dir.exists():
        return {'zh': [], 'en': []}
    
    profiles = {'zh': [], 'en': []}
    
    # Get all audio files
    audio_files = [f for f in profiles_dir.glob('*') if f.suffix.lower() in ['.wav', '.mp3', '.m4a']]
    
    for audio_file in audio_files:
        base_name = audio_file.stem
        text_file = profiles_dir / f"{base_name}.txt"
        
        if text_file.exists():
            with open(text_file, 'r', encoding='utf-8') as f:
                ref_text = f.read().strip()
            
            # Detect language from the reference text
            lang = 'zh' if any('\u4e00' <= char <= '\u9fff' for char in ref_text) else 'en'
            
            profiles[lang].append({
                'id': base_name,
                'name': base_name.replace('_', ' ').title(),
                'ref_audio': str(audio_file),
                'ref_text': ref_text
            })
    
    return profiles

TTS_SERVICES = {
    'gtts': 'Google Text-to-Speech',
    'f5tts': 'F5 Text-to-Speech'
}

def detect_language(text):
    """Detect if text contains Chinese characters"""
    return 'zh' if any('\u4e00' <= char <= '\u9fff' for char in text[:100]) else 'en'