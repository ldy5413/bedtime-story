from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
from cached_path import cached_path
import soundfile as sf
from importlib.resources import files
import logging
import json
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import necessary F5TTS components
from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_model,
    load_vocoder,
    preprocess_ref_audio_text,
    infer_process
)

app = FastAPI(title="F5TTS API")

# Create directory for generated audio
AUDIO_DIR = Path("static")
AUDIO_DIR.mkdir(exist_ok=True)

# Get default reference audio path
DEFAULT_REF_AUDIO = files("f5_tts").joinpath("infer/examples/basic/basic_ref_zh.wav")

DEFAULT_REF_TEXT = "对,这就是我万人敬仰的太乙真人."

# Load models on startup
def load_f5tts(ckpt_path=str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))):
    F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    return load_model(DiT, F5TTS_model_cfg, ckpt_path)

# Initialize models
try:
    logger.info("Loading F5TTS model...")
    model = load_f5tts()
    logger.info("Loading vocoder...")
    vocoder = load_vocoder()
    logger.info("Models loaded successfully")
except Exception as e:
    logger.error(f"Error loading models: {str(e)}")
    raise

class TTSRequest(BaseModel):
    text_to_generate: str
    ref_audio: str = str(DEFAULT_REF_AUDIO)
    ref_text: str = DEFAULT_REF_TEXT
    remove_silence: bool = True
    cross_fade_duration: float = 0.15
    nfe_step: int = 32
    speed: float = 1.0
    response_type: str = "stream"  # "stream" or "file"

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        logger.info(f"Processing request with text: {request.text_to_generate}")
        logger.info(f"Using reference audio: {request.ref_audio}")
        
        # Process reference audio and text
        try:
            ref_audio, ref_text = preprocess_ref_audio_text(
                request.ref_audio, 
                request.ref_text
            )
            logger.info(f"Reference text processed: {ref_text}")
        except Exception as e:
            logger.error(f"Error in preprocessing: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Preprocessing error: {str(e)}")

        # Generate speech using infer_process
        try:
            final_wave, final_sample_rate, _ = infer_process(
                ref_audio=ref_audio,
                ref_text=ref_text,
                gen_text=request.text_to_generate,
                model_obj=model,
                vocoder=vocoder,
                cross_fade_duration=request.cross_fade_duration,
                nfe_step=request.nfe_step,
                speed=request.speed
            )
            logger.info("Speech generated successfully")
        except Exception as e:
            logger.error(f"Error in speech generation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

        try:
            if request.response_type == "file":
                # Always save as story.wav
                temp_file = AUDIO_DIR / "story.wav"
                sf.write(temp_file, final_wave, final_sample_rate)
                
                return FileResponse(
                    temp_file,
                    media_type="audio/wav",
                    filename="story.wav"
                )
            else:
                # Stream the audio
                audio_buffer = io.BytesIO()
                sf.write(audio_buffer, final_wave, final_sample_rate, format='wav')
                audio_buffer.seek(0)
                
                def iterfile():
                    yield from audio_buffer
                
                return StreamingResponse(
                    iterfile(),
                    media_type="audio/wav"
                )
            
        except Exception as e:
            logger.error(f"Error in response generation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Response generation error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "vocoder_loaded": vocoder is not None
    }

# Add route to get available voice profiles
@app.get("/voices")
async def get_voices():
    try:
        profiles_path = Path("voice_profiles/profiles.json")
        if profiles_path.exists():
            with open(profiles_path, 'r', encoding='utf-8') as f:
                return JSONResponse(content=json.load(f))
        return JSONResponse(content={'zh': [], 'en': []})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 