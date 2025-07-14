import os
import subprocess
import soundfile as sf
import requests
from mp3_wav import mp3_to_wav

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

def reencode_wav(input_path, output_path):
    """
    Re-encode a WAV file to standard PCM 16-bit mono 44.1kHz using ffmpeg.
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", output_path
    ]
    subprocess.run(cmd, check=True)

def extract_text(path: str) -> str:
    """
    Transcribe the isolated audio file using Deepgram Nova-3 API.
    """
    file_name = mp3_to_wav(path)
    # Re-encode to PCM 16-bit mono 44.1kHz for best compatibility
    reencoded_file = file_name.replace(".wav", "_reencoded.wav")
    reencode_wav(file_name, reencoded_file)
    file_name = reencoded_file

    print("Checking WAV file:", file_name)
    try:
        info = sf.info(file_name)
        print("WAV info:", info)
        print("WAV file size:", os.path.getsize(file_name), "bytes")
    except Exception as e:
        print("WAV file is not valid:", e)
        raise

    url = "https://api.deepgram.com/v1/listen?model=nova-3&punctuate=true&language=en"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav"
    }
    with open(file_name, "rb") as audio:
        print("Uploading audio to Deepgram Nova-3...")
        response = requests.post(url, headers=headers, data=audio)
    response.raise_for_status()
    result = response.json()
    print("Deepgram response:", result)
    return result["results"]["channels"][0]["alternatives"][0]["transcript"]
