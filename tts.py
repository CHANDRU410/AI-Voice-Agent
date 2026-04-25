'''import os
import tempfile
import pyttsx3

# ─── pyttsx3 engine for English (offline, fast) ───────────────────────────
_engine = pyttsx3.init()
_engine.setProperty("rate", 155)
_engine.setProperty("volume", 1.0)





def _speak_gtts(text, lang_code):
    """
    Use gTTS for Tamil (ta) and Malayalam (ml).
    Saves to a temp MP3 file, plays with pygame, then deletes the file.
    Works on Windows, macOS, and Linux.
    """
    tmp_path = None
    try:
        from gtts import gTTS
        import pygame

        # Generate speech MP3 via Google TTS
        tts = gTTS(text=text, lang=lang_code, slow=False)

        # Save to a named temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
            tts.save(tmp_path)

        # Play using pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        # Wait until playback finishes
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.music.unload()
        pygame.mixer.music.stop()
        pygame.mixer.quit()

    except ImportError as e:
        print(f"[TTS] Missing library ({e}) — falling back to English engine")
        _speak_english(text)

    except Exception as e:
        print(f"[TTS] gTTS/pygame error: {e} — falling back to English engine")
        _speak_english(text)

    finally:
        # Always clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def speak(text, lang="en"):
    if not text or not text.strip():
        return

    print(f"[TTS] Speaking ({lang}): {text[:70]}")

    if lang in ["ta", "ml", "en"]:
        _speak_gtts(text, lang)
    else:
        _speak_gtts(text, "en")'''

from gtts import gTTS
import uuid
import os
import threading, time
def delete_file_later(filepath):
    time.sleep(10)
    if os.path.exists(filepath):
        os.remove(filepath)
def generate_audio(text, lang="en"):
    os.makedirs("static", exist_ok=True)

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join("static", filename)

    tts = gTTS(text=text, lang=lang)
    tts.save(filepath)
    threading.Thread(target=delete_file_later, args=(filepath,)).start()
    return filename