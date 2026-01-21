# app.py ✅ FULL WORKING: Offline Hindi STT (Vosk) + Predefined QA (qa.json) + Hindi TTS (eSpeak-NG)
# Includes: ✅ anti-echo lock + queue flush + cooldown + short-text ignore
#
# Run (from src folder):  py app.py
# Stop: Ctrl + C

import json
import os
import queue
import re
import subprocess
import time

import sounddevice as sd
from vosk import Model, KaldiRecognizer

# ---------- Paths ----------
MODEL_PATH = "../models/vosk-model-small-hi-0.22"
QA_PATH = "../qa.json"
ESPEAK = r"C:\Program Files\eSpeak NG\espeak-ng.exe"

SAMPLE_RATE = 16000
q = queue.Queue()

# Echo control
LISTENING = True
COOLDOWN_SECONDS = 1.2  # increase to 1.5 if still looping
IGNORE_IF_UNDER_CHARS = 3  # ignore tiny recognitions like "हां" / noise


# ---------- Helpers ----------
def normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    # keep Hindi range + word chars/spaces, drop punctuation/symbols
    text = re.sub(r"[^\w\s\u0900-\u097F]", "", text)
    return text


def load_qa(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    fixed = {}
    for k, v in data.items():
        fixed[normalize(k)] = v
    return fixed


def flush_queue():
    """Remove any buffered mic audio so we don't process assistant's own speech after TTS."""
    try:
        while True:
            q.get_nowait()
    except queue.Empty:
        pass


def speak(text: str):
    """Offline Hindi TTS using eSpeak-NG with UTF-8 file input."""
    global LISTENING
    if not text:
        return

    # 1) Stop listening + flush any queued audio
    LISTENING = False
    flush_queue()

    # Write text to temp UTF-8 file (avoids console encoding issues)
    tmp = os.path.join(os.environ.get("TEMP", "."), "tts_hi.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)

    # Speak (tune for clarity)
    subprocess.run(
        [ESPEAK, "-v", "hi", "-s", "105", "-p", "55", "-a", "180", "-f", tmp],
        check=False,
    )

    # 2) Cooldown: let speaker sound die out
    time.sleep(COOLDOWN_SECONDS)

    # 3) Flush again (some audio can still be in buffer)
    flush_queue()

    LISTENING = True


def callback(indata, frames, time_info, status):
    # Always push audio to queue; we decide later whether to ignore it
    q.put(bytes(indata))


# ---------- Main ----------
def main():
    if not os.path.exists(MODEL_PATH):
        print("ERROR: Model folder not found:", os.path.abspath(MODEL_PATH))
        return

    if not os.path.exists(QA_PATH):
        print("ERROR: qa.json not found:", os.path.abspath(QA_PATH))
        return

    if not os.path.exists(ESPEAK):
        print("ERROR: eSpeak-NG not found at:", ESPEAK)
        return

    qa = load_qa(QA_PATH)

    print("Loading Hindi model...")
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, SAMPLE_RATE)

    print("\nSpeak in Hindi. Press Ctrl+C to stop.\n")

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            while True:
                data = q.get()

                # Ignore mic data while speaking/cooldown
                if not LISTENING:
                    continue

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = (result.get("text") or "").strip()
                    if not text:
                        continue

                    key = normalize(text)

                    # Ignore tiny/noisy outputs (often from echo)
                    if len(key) < IGNORE_IF_UNDER_CHARS:
                        continue

                    print("You said:", text)

                    reply = qa.get(key)
                    if reply:
                        print("Assistant:", reply)
                        speak(reply)
                    else:
                        fallback = "माफ कीजिए, इसका जवाब मेरे पास अभी नहीं है।"
                        print("Assistant:", fallback)
                        speak(fallback)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
