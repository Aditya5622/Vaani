from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from deep_translator import MyMemoryTranslator
from gtts import gTTS
import os
import shutil


app = FastAPI()


# ==========================================
# FOLDERS
# ==========================================

os.makedirs("static", exist_ok=True)
os.makedirs("static/profiles", exist_ok=True)


# ==========================================
# STATIC FOLDER
# ==========================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ==========================================
# SUPPORTED LANGUAGES
# ==========================================

LANGUAGES = {
    "hi": "hindi",
    "en": "english",
    "ja": "japanese",
    "fr": "french",
    "de": "german",
    "es": "spanish",
    "it": "italian",
    "pt": "portuguese",
    "ru": "russian",
    "ko": "korean",
    "zh": "chinese simplified",
    "ar": "arabic",
    "bn": "bengali",
    "gu": "gujarati",
    "mr": "marathi",
    "ta": "tamil india",
    "te": "telugu",
    "ur": "urdu"
}


# ==========================================
# REQUEST MODELS
# ==========================================

class TranslationRequest(BaseModel):
    text: str
    source: str
    target: str


class SpeechRequest(BaseModel):
    text: str
    language: str


# ==========================================
# HOME PAGE
# ==========================================

@app.get("/")
def home():
    return FileResponse("static/home.html")


# ==========================================
# TRANSLATOR APP PAGE
# ==========================================

@app.get("/app")
def vaani_app():
    return FileResponse("static/index.html")


# ==========================================
# LANGUAGES
# ==========================================

@app.get("/languages")
def get_languages():
    return {
        "languages": LANGUAGES
    }


# ==========================================
# TRANSLATION
# ==========================================

@app.post("/translate")
def translate_text(request: TranslationRequest):

    source_language = LANGUAGES.get(request.source)
    target_language = LANGUAGES.get(request.target)

    if not source_language:
        return {
            "error": "Unsupported source language"
        }

    if not target_language:
        return {
            "error": "Unsupported target language"
        }

    try:

        translated = MyMemoryTranslator(
            source=source_language,
            target=target_language
        ).translate(request.text)

        return {
            "original_text": request.text,
            "translated_text": translated,
            "source_language": request.source,
            "target_language": request.target
        }

    except Exception as error:

        return {
            "error": "Translation failed",
            "details": str(error)
        }


# ==========================================
# TEXT TO SPEECH
# ==========================================

@app.post("/speak")
def speak_text(request: SpeechRequest):

    tts_languages = {
        "hi": "hi",
        "en": "en",
        "ja": "ja",
        "fr": "fr",
        "de": "de",
        "es": "es",
        "it": "it",
        "pt": "pt",
        "ru": "ru",
        "ko": "ko",
        "zh": "zh-CN",
        "ar": "ar",
        "bn": "bn",
        "gu": "gu",
        "mr": "mr",
        "ta": "ta",
        "te": "te",
        "ur": "ur"
    }

    voice_language = tts_languages.get(
        request.language,
        "en"
    )

    try:

        tts = gTTS(
            text=request.text,
            lang=voice_language
        )

        file_name = "static/vaani_voice.mp3"

        tts.save(file_name)

        return {
            "message": "Voice generated successfully!",
            "file": "vaani_voice.mp3",
            "language": voice_language
        }

    except Exception as error:

        return {
            "error": "Voice generation failed",
            "details": str(error)
        }


# ==========================================
# USER PROFILE
# ==========================================

@app.post("/profile")
async def create_profile(
    name: str = Form(...),
    preferred_language: str = Form(...),
    voice: str = Form(...),
    photo: UploadFile | None = File(None)
):

    profile_photo = None

    # --------------------------------------
    # SAVE PROFILE PHOTO
    # --------------------------------------

    if photo is not None:

        if photo.filename:

            extension = os.path.splitext(
                photo.filename
            )[1].lower()

            allowed_extensions = [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp"
            ]

            if extension not in allowed_extensions:

                return {
                    "error": "Only JPG, JPEG, PNG and WEBP photos are allowed."
                }

            photo_path = (
                "static/profiles/profile"
                + extension
            )

            with open(
                photo_path,
                "wb"
            ) as buffer:

                shutil.copyfileobj(
                    photo.file,
                    buffer
                )

            profile_photo = (
                "/static/profiles/profile"
                + extension
            )

    # --------------------------------------
    # PROFILE RESPONSE
    # --------------------------------------

    return {
        "message": "Profile created successfully!",
        "profile": {
            "name": name,
            "preferred_language": preferred_language,
            "voice": voice,
            "photo": profile_photo
        }
    }