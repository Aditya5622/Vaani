from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS
from PIL import Image, ImageOps
import io
import urllib.request
import urllib.parse
import json
import base64

app = FastAPI(title="Vaani - Voice & AI Translator")

app.mount("/static", StaticFiles(directory="static"), name="static")

class TranslationRequest(BaseModel):
    text: str
    source: str
    target: str

class SpeakRequest(BaseModel):
    text: str
    lang: str

LOCALE_MAP = {
    'hi': 'hi-IN', 'en': 'en-GB', 'es': 'es-ES', 'fr': 'fr-FR',
    'de': 'de-DE', 'ja': 'ja-JP', 'bn': 'bn-IN', 'gu': 'gu-IN',
    'mr': 'mr-IN', 'ta': 'ta-IN', 'te': 'te-IN', 'ur': 'ur-PK'
}

def robust_translate(text: str, source: str = "en", target: str = "hi") -> str:
    if not text.strip():
        return ""
    
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    translated_chunks = []
    src = "auto" if source == "en" else source

    for para in paragraphs:
        chunk_res = ""
        try:
            chunk_res = GoogleTranslator(source=src, target=target).translate(para)
        except Exception:
            chunk_res = ""

        if not chunk_res or chunk_res.strip() == para.strip():
            try:
                src_loc = LOCALE_MAP.get(source, source)
                tgt_loc = LOCALE_MAP.get(target, target)
                chunk_res = MyMemoryTranslator(source=src_loc, target=tgt_loc).translate(para)
            except Exception:
                pass

        translated_chunks.append(chunk_res if chunk_res else para)

    return "\n\n".join(translated_chunks)

@app.get("/app")
async def serve_app():
    return FileResponse("static/translator.html")

@app.get("/")
async def root():
    return FileResponse("static/translator.html")

@app.post("/translate")
async def translate_text(req: TranslationRequest):
    res = robust_translate(req.text, req.source, req.target)
    return {"translation": res}

@app.post("/speak")
async def speak_audio(req: SpeakRequest):
    text = req.text.strip()
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    
    sample_text = text[:400]
    try:
        tts = gTTS(text=sample_text, lang=req.lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return Response(content=fp.read(), media_type="audio/mpeg")
    except Exception:
        try:
            tts = gTTS(text=sample_text, lang='hi', slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return Response(content=fp.read(), media_type="audio/mpeg")
        except Exception as err:
            return JSONResponse({"error": str(err)}, status_code=500)

# Multi-Key Rotation
OCR_KEYS = [
    "helloworld",
    "K87899142388957",
    "K89376663288957",
    "K82811462988957"
]

def fetch_ocr(base64_img: str, engine_no: int = 1):
    for key in OCR_KEYS:
        try:
            payload = {
                "base64Image": f"data:image/jpeg;base64,{base64_img}",
                "language": "eng",
                "isOverlayRequired": False,
                "detectOrientation": True,
                "scale": True,
                "OCREngine": engine_no
            }
            req = urllib.request.Request(
                "https://api.ocr.space/parse/image",
                data=urllib.parse.urlencode(payload).encode('utf-8'),
                headers={"apikey": key}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                parsed = res.get("ParsedResults", [])
                if parsed:
                    text = parsed[0].get("ParsedText", "").strip()
                    if text:
                        return text
        except urllib.error.HTTPError as err:
            if err.code == 429:
                continue
            else:
                continue
        except Exception:
            continue
    return ""

@app.post("/ocr")
async def ocr_process(file: UploadFile = File(...), source: str = Form("en"), target: str = Form("hi")):
    try:
        contents = await file.read()
        
        image = Image.open(io.BytesIO(contents))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image.thumbnail((1200, 1200))
        
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=80)
        optimized_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        extracted_text = fetch_ocr(optimized_base64, engine_no=1)
        if not extracted_text:
            extracted_text = fetch_ocr(optimized_base64, engine_no=2)

        if not extracted_text:
            return JSONResponse({"error": "Free OCR server limit reached. Please wait 1-2 minutes or upload again."}, status_code=400)

        # Demo watermark aur notices ko filter out karein
        lines = []
        for line in extracted_text.splitlines():
            line_lower = line.lower()
            if any(term in line_lower for term in ["helloworld", "ocr.space", "demo key", "testing only", "freekey"]):
                continue
            lines.append(line)
        cleaned_ocr_text = "\n".join(lines).strip()

        target_lang = target if target else "hi"
        source_lang = source if source else "en"
        translated = robust_translate(cleaned_ocr_text, source=source_lang, target=target_lang)

        return {
            "scanned_text": cleaned_ocr_text,
            "translated_text": translated
        }
    except Exception as e:
        return JSONResponse({"error": f"OCR Failed: {str(e)}"}, status_code=500)