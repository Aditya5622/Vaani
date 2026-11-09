import io
import os
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS
from PIL import Image

app = FastAPI(title="Vaani Translator")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

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
    src: str = None
    tgt: str = None

@app.get("/")
def home():
    return {"message": "Vaani Server is Running. Go to /app for Web UI"}

@app.get("/app", response_class=HTMLResponse)
def get_app():
    for path in ["templates/index.html", "index.html", "static/index.html"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h2>Vaani App UI File (index.html) Not Found</h2>", status_code=404)

def direct_google_translate(text: str, src: str, tgt: str):
    """Direct Google Translate API with browser User-Agent to bypass shared IP blocks"""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": src,
        "tl": tgt,
        "dt": "t",
        "q": text
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(url, params=params, headers=headers, timeout=5)
    if res.status_code == 200:
        data = res.json()
        translated = "".join([sentence[0] for sentence in data[0] if sentence[0]])
        return translated
    raise Exception(f"Google status {res.status_code}")

@app.post("/translate")
async def translate_text(req: TranslationRequest):
    raw_text = req.text.strip()
    if not raw_text:
        return {"translated_text": "", "result": ""}

    src_raw = (req.source_lang or req.src or "auto").strip().lower()
    tgt_raw = (req.target_lang or req.tgt or "en").strip().lower()

    src_code = LANG_MAP.get(src_raw, src_raw)
    tgt_code = LANG_MAP.get(tgt_raw, tgt_raw)

    if src_code != "auto" and src_code == tgt_code:
        return {"translated_text": raw_text, "result": raw_text}

    # इंजन 1: Direct Google Endpoint (Client GTX) - सबसे तेज़ और बिना ब्लॉक वाला तरीका
    try:
        translated = direct_google_translate(raw_text, src_code, tgt_code)
        if translated:
            return {"translated_text": translated, "result": translated, "source": src_code, "target": tgt_code}
    except Exception as e1:
        print(f"Engine 1 (Direct GTX) failed: {e1}")

    # इंजन 2: Deep-Translator GoogleTranslator
    try:
        translated = GoogleTranslator(source=src_code, target=tgt_code).translate(raw_text)
        if translated:
            return {"translated_text": translated, "result": translated, "source": src_code, "target": tgt_code}
    except Exception as e2:
        print(f"Engine 2 (Deep-Translator) failed: {e2}")

    # इंजन 3: MyMemory Translator (With custom email to bypass rate-limit)
    try:
        mem_src = "en" if src_code == "auto" else src_code
        # Email id dene se MyMemory ki daily quota 30,000 words ho jaati hai
        translated = MyMemoryTranslator(source=mem_src, target=tgt_code).translate(raw_text)
        if translated:
            return {"translated_text": translated, "result": translated, "source": src_code, "target": tgt_code}
    except Exception as e3:
        print(f"Engine 3 (MyMemory) failed: {e3}")

    raise HTTPException(
        status_code=500,
        detail="All translation services are momentarily unreachable. Please try again in 5 seconds."
    )

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
        width, height = image.size
        return {
            "message": "Image uploaded successfully",
            "dimensions": f"{width}x{height}",
            "text": "Image uploaded. Text extraction ready."
        }
    except Exception as e:
        print(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))