import json
import os
import queue
import re
import subprocess
import threading
import time
import tkinter as tk

import sounddevice as sd
from vosk import Model, KaldiRecognizer

# ---------- Paths ----------
MODEL_PATH = r"C:\Users\ashik\Downloads\ps1-offline-hindi-voice-assistant-main\ps1-offline-hindi-voice-assistant-main\models\vosk-model-small-hi-0.22"
QA_PATH = r"C:\Users\ashik\Downloads\ps1-offline-hindi-voice-assistant-main\ps1-offline-hindi-voice-assistant-main\src\qa.json"
ESPEAK = r"C:\Program Files\eSpeak NG\espeak-ng.exe"

SAMPLE_RATE = 16000
q = queue.Queue()

# State
RUNNING = False
LISTENING = False
COOLDOWN_SECONDS = 1.2
IGNORE_IF_UNDER_CHARS = 3


# ---------- Helpers ----------
def normalize(text):
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"[^\w\s\u0900-\u097F]", "", text)


def load_qa(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {normalize(k): v for k, v in data.items()}


def flush_queue():
    try:
        while True:
            q.get_nowait()
    except queue.Empty:
        pass


def update_status(msg, color):
    status_label.config(text=f"● {msg}", fg=color)


def speak(text):
    global LISTENING
    LISTENING = False
    update_status("Speaking", "orange")
    flush_queue()

    tmp = os.path.join(os.environ.get("TEMP", "."), "tts_hi.txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)

    subprocess.run(
        [ESPEAK, "-v", "hi", "-s", "105", "-p", "55", "-a", "180", "-f", tmp],
        check=False,
    )

    time.sleep(COOLDOWN_SECONDS)
    flush_queue()
    LISTENING = True
    update_status("Listening", "green")


def callback(indata, frames, time_info, status):
    q.put(bytes(indata))


# ---------- Voice Thread ----------
def voice_loop():
    global RUNNING, LISTENING

    qa = load_qa(QA_PATH)
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, SAMPLE_RATE)

    LISTENING = True
    update_status("Listening", "green")

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        while RUNNING:
            data = q.get()

            if not LISTENING:
                continue

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if not text:
                    continue

                key = normalize(text)
                if len(key) < IGNORE_IF_UNDER_CHARS:
                    continue

                input_box.delete("1.0", tk.END)
                input_box.insert(tk.END, text)

                reply = None
                for qq, a in qa.items():
                   if qq in key or key in qq:
                      reply = a
                      break

                if reply is None:
                   reply = "माफ कीजिए, इसका जवाब मेरे पास अभी नहीं है।"


                output_box.delete("1.0", tk.END)
                output_box.insert(tk.END, reply)
                speak(reply)

    update_status("Stopped", "red")


# ---------- UI Actions ----------
def start_listening():
    global RUNNING
    if RUNNING:
        return
    RUNNING = True
    threading.Thread(target=voice_loop, daemon=True).start()


def stop_listening():
    global RUNNING, LISTENING
    RUNNING = False
    LISTENING = False
    flush_queue()
    update_status("Stopped", "red")


# ---------- GUI ----------
root = tk.Tk()
root.title("Offline Hindi Voice Assistant")
root.geometry("780x560")
root.resizable(False, False)

title = tk.Label(root, text="Offline Hindi Voice Assistant",
                 font=("Segoe UI", 16, "bold"))
title.pack(pady=10)

status_label = tk.Label(root, text="● Idle", font=("Segoe UI", 11), fg="gray")
status_label.pack(pady=5)

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="▶ START", width=14,
          font=("Segoe UI", 11), command=start_listening).pack(side=tk.LEFT, padx=20)

tk.Button(btn_frame, text="⏹ STOP", width=14,
          font=("Segoe UI", 11), command=stop_listening).pack(side=tk.LEFT, padx=20)

# Input Section
tk.Label(root, text="You Said (Live Input)",
         font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20)

input_box = tk.Text(root, height=4, font=("Segoe UI", 12), wrap=tk.WORD)
input_box.pack(fill="x", padx=20, pady=5)

# Output Section
tk.Label(root, text="Assistant Reply (Live Output)",
         font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(10, 0))

output_box = tk.Text(root, height=5, font=("Segoe UI", 12), wrap=tk.WORD)
output_box.pack(fill="x", padx=20, pady=5)

root.mainloop()
