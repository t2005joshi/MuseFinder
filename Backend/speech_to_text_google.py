import os
import tempfile
import numpy as np
import librosa
import soundfile as sf
import speech_recognition as sr
from mp3_wav import mp3_to_wav
import wave

r = sr.Recognizer()

MAX_CHUNK_SEC = 20.0
MIN_CHUNK_SEC = 2.0

def extract_text(path: str) -> str:
    file_name = mp3_to_wav(path)
    # Normalize audio to -20dBFS for consistent splitting
    audio_data, sample_rate = librosa.load(file_name, sr=None)
    peak = np.max(np.abs(audio_data))
    if peak > 0:
        audio_data = audio_data / peak * 0.3  # scale to ~-10dBFS

    non_silent_intervals = librosa.effects.split(audio_data, top_db=15)

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
                with sr.AudioFile(chunk_file) as source:
                    audio = r.record(source)
                    try:
                        text = r.recognize_google(audio)
                        if text.strip():
                            text_fragments.append(text.capitalize() + ".")
                    except sr.UnknownValueError:
                        continue
    # Fallback if nothing was transcribed
    if not text_fragments:
        with wave.open(file_name, 'rb') as wf:
            duration = wf.getnframes() / wf.getframerate()
            print(f"Fallback file duration: {duration:.2f} seconds")
            print("No lyrics detected in chunks, trying whole file (first 30 seconds)...")
            with sr.AudioFile(file_name) as source:
                # Only read the first 30 seconds
                audio = r.record(source, duration=30)
                try:
                    text = r.recognize_google(audio)
                    if text.strip():
                        text_fragments.append(text.capitalize() + ".")
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"Google API error: {e}")
    return " ".join(text_fragments)
