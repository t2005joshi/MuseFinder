import os
import tempfile
import numpy as np
import librosa
import soundfile as sf
import whisper
from mp3_wav import mp3_to_wav

MAX_CHUNK_SEC = 20.0
MIN_CHUNK_SEC = 2.0

def extract_text(path: str) -> str:
    file_name = mp3_to_wav(path)
    # Normalize audio to -10dBFS for consistent splitting
    audio_data, sample_rate = librosa.load(file_name, sr=None)
    peak = np.max(np.abs(audio_data))
    if peak > 0:
        audio_data = audio_data / peak * 0.3

    non_silent_intervals = librosa.effects.split(audio_data, top_db=15)

    model = whisper.load_model("small.en")
    text_fragments = []
    with tempfile.TemporaryDirectory() as folder_name:
        for i, (start, end) in enumerate(non_silent_intervals):
            duration = (end - start) / sample_rate
            if duration < MIN_CHUNK_SEC:
                continue
            chunk_starts = np.arange(start, end, int(MAX_CHUNK_SEC * sample_rate))
            for j, chunk_start in enumerate(chunk_starts):
                chunk_end = min(chunk_start + int(MAX_CHUNK_SEC * sample_rate), end)
                chunk_file = os.path.join(folder_name, f"chunk{i}_{j}.wav")
                sf.write(chunk_file, audio_data[chunk_start:chunk_end], sample_rate)
                print(f"Chunk {i}_{j}: {round((chunk_end-chunk_start)/sample_rate, 2)} seconds")
                result = model.transcribe(chunk_file, language="en")
                text = result.get("text", "").strip()
                if text:
                    text_fragments.append(text.capitalize() + ".")
    # Fallback if nothing was transcribed
    if not text_fragments:
        print("No lyrics detected in chunks, trying whole file (first 30 seconds)...")
        result = model.transcribe(file_name, duration=30, language="en")
        text = result.get("text", "").strip()
        if text:
            text_fragments.append(text.capitalize() + ".")
    return " ".join(text_fragments)
