from pydub import AudioSegment
import os

def mp3_to_wav(mp3_path):
    wav_path = os.path.splitext(mp3_path)[0] + ".wav"
    audio = AudioSegment.from_mp3(mp3_path)
    # Export as PCM 16-bit WAV
    audio.export(wav_path, format="wav", codec="pcm_s16le")
    return wav_path

