import io
import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from gtts import gTTS
from PIL import Image

app = FastAPI(title="Vaani Translator")

# Static files mount karein (agar static folder exist karta hai)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Comprehensive Language Code Mapping
# User chahe "Hindi" likhe, "hi", ya uppercase/lowercase, sahi code par map hoga
LANG_MAP = {
    "hindi": "hi", "hi": "hi",
    "english": "en", "en": "en",
    "bengali": "bn", "bn": "bn",
    "marathi": "mr", "mr": "mr",
    "telugu": "te", "te": "te",
    "tamil": "ta", "ta": "ta",
    "gujarati": "gu", "gu": "gu",
    "urdu": "ur", "ur": "ur",
    "kannada": "kn", "kn": "kn",
    "malayalam": "ml", "ml": "ml",
    "punjabi": "pa", "pa": "pa",
    "french": "fr", "fr": "fr",
    "german": "de", "de": "de",
    "spanish": "es", "es": "es",
    "japanese": "ja", "ja": "ja",
    "auto": "auto"
}

class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "en"
    # Frontend agar alag key names bhej raha ho to fallback ke liye:
    src: str = None
    tgt: str = None

@app.get("/")
def home():
    return {"message": "Vaani Server is Running. Go to /app for Web UI"}

@app.get("/app", response_class=HTMLResponse)
def get_app():
    # Agar templates/index.html ya index.html exist karti hai to use load karein
    for path in ["templates/index.html", "index.html", "static/index.html"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h2>Vaani App UI File (index.html) Not Found</h2>", status_code=404)

@app.post("/translate")
async def translate_text(req: TranslationRequest):
    try:
        raw_text = req.text.strip()
        if not raw_text:
            return {"translated_text": "", "result": ""}

        # Source aur Target ko nikaalein (fallback support ke saath)
        src_raw = (req.source_lang or req.src or "auto").strip().lower()
        tgt_raw = (req.target_lang or req.tgt or "en").strip().lower()

        src_code = LANG_MAP.get(src_raw, src_raw)
        tgt_code = LANG_MAP.get(tgt_raw, tgt_raw)

        # Agar source aur target dono ek hi hon to direct return karein
        if src_code != "auto" and src_code == tgt_code:
            return {"translated_text": raw_text, "result": raw_text}

        # GoogleTranslator se translation call
        translator = GoogleTranslator(source=src_code, target=tgt_code)
        translated = translator.translate(raw_text)

        # Frontend chahe translated_text read kare ya result, dono format me response
        return {
            "translated_text": translated,
            "result": translated,
            "source": src_code,
            "target": tgt_code
        }

    except Exception as e:
        print(f"Translation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def text_to_speech(text: str = Form(...), lang: str = Form("en")):
    try:
        clean_text = text.strip()
        if not clean_text:
            raise HTTPException(status_code=400, detail="Text is empty")

        lang_code = LANG_MAP.get(lang.strip().lower(), "en")
        if lang_code == "auto":
            lang_code = "en"

        tts = gTTS(text=clean_text, lang=lang_code)
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)

        return StreamingResponse(audio_stream, media_type="audio/mpeg")
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr")
async def process_image(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        # Image successfully load hui ya nahi verification
        width, height = image.size
        return {
            "message": "Image uploaded successfully",
            "dimensions": f"{width}x{height}",
            "text": "Image uploaded. Text extraction ready."
        }
    except Exception as e:
        print(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))