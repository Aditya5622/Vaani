
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from gtts import gTTS
import os
import shutil

app = FastAPI()

# FOLDERS
os.makedirs("static", exist_ok=True)
os.makedirs("static/profiles", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


# LANGUAGES
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


# LIBRETRANSLATE LANGUAGE CODES
LIBRE_LANGUAGES = {
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
    "zh": "zh",
    "ar": "ar",
    "bn": "bn",
    "gu": "gu",
    "mr": "mr",
    "ta": "ta",
    "te": "te",
    "ur": "ur"
}


# REQUEST MODELS
class TranslationRequest(BaseModel):
    text: str
    source: str
    target: str


class SpeechRequest(BaseModel):
    text: str
    language: str


# HOME PAGE
@app.get("/")
def home():
    return FileResponse("static/home.html")


# TRANSLATOR APP PAGE
@app.get("/app")
def vaani_app():
    return FileResponse("static/translator.html")


# LANGUAGES API
@app.get("/languages")
def get_languages():
    return {"languages": LANGUAGES}


# TRANSLATION
@app.post("/translate")
def translate_text(request: TranslationRequest):

    source_language = LIBRE_LANGUAGES.get(request.source)
    target_language = LIBRE_LANGUAGES.get(request.target)

    if not source_language:
        return {
            "error": "Unsupported source language"
        }

    if not target_language:
        return {
            "error": "Unsupported target language"
        }

    if not request.text.strip():
        return {
            "error": "Please enter some text"
        }

    try:

        response = requests.post(
            "http://127.0.0.1:5000/translate",
            json={
                "q": request.text,
                "source": source_language,
                "target": target_language,
                "format": "text"
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        if "translatedText" not in data:
            return {
                "error": "Translation failed",
                "details": data
            }

        translated = data["translatedText"]

        return {
            "original_text": request.text,
            "translated_text": translated,
            "source_language": request.source,
            "target_language": request.target
        }

    except requests.exceptions.ConnectionError:
        return {
            "error": "Translation service is not running",
            "details": "Please start LibreTranslate on port 5000"
        }

    except requests.exceptions.Timeout:
        return {
            "error": "Translation service timed out"
        }

    except Exception as error:
        return {
            "error": "Translation failed",
            "details": str(error)
        }


# TEXT TO SPEECH
@app.post("/speak")
def speak_text(request: SpeechRequest):

    try:

        language = request.language

        if language not in LANGUAGES:
            return {
                "error": "Unsupported language"
            }

        audio_file = "static/vaani_voice.mp3"

        tts = gTTS(
            text=request.text,
            lang=language
        )

        tts.save(audio_file)

        return {
            "message": "Speech generated successfully",
            "audio_url": "/static/vaani_voice.mp3"
        }

    except Exception as error:

        return {
            "error": "Speech generation failed",
            "details": str(error)
        }


# PROFILE
@app.post("/profile")
async def update_profile(
    name: str = Form(""),
    preferred_language: str = Form("en"),
    voice: str = Form("female"),
    photo: UploadFile = File(None)
):

    try:

        profile_data = {
            "name": name,
            "preferred_language": preferred_language,
            "voice": voice
        }

        photo_url = None

        if photo:

            filename = photo.filename

            file_path = os.path.join(
                "static",
                "profiles",
                filename
            )

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(
                    photo.file,
                    buffer
                )

            photo_url = "/static/profiles/" + filename

        return {
            "message": "Profile updated successfully",
            "profile": profile_data,
            "photo_url": photo_url
        }

    except Exception as error:

        return {
            "error": "Profile update failed",
            "details": str(error)
        }


# START SERVER
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )

