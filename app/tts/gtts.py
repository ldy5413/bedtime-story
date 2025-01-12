import re, io
from gtts import gTTS
from flask import Response
def stream_gtts_audio(story, language):
    lang = 'zh-cn' if language == 'zh' else 'en'

    def split_into_sentences(text, max_length=200):
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += (" " + sentence).strip()
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def generate_audio_chunks():
        chunks = split_into_sentences(story, max_length=200)
        for chunk in chunks:
            tts = gTTS(text=chunk, lang=lang)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            yield fp.read()
            fp.close()

    return Response(generate_audio_chunks(), content_type='audio/mpeg')

# Generate TTS audio
def generate_audio(content, language='en'):
    lang = 'zh-cn' if language == 'zh' else 'en'
    tts = gTTS(text=content, lang=lang)
    audio_file = 'static/story.mp3'
    tts.save(audio_file)
    return f'/static/story.mp3'