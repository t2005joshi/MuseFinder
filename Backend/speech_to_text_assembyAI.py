import os
import tempfile
import numpy as np
import librosa
import soundfile as sf
import requests
import time
import subprocess
from mp3_wav import mp3_to_wav

ASSEMBLYAI_API_KEY = "5d421ef3fd2e4c53972c197dc29d4b21"
UPLOAD_ENDPOINT = "https://api.assemblyai.com/v2/upload"
TRANSCRIBE_ENDPOINT = "https://api.assemblyai.com/v2/transcript"

MAX_CHUNK_SEC = 30.0
MIN_CHUNK_SEC = 10.0

def upload_to_assemblyai(filename):
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    with open(filename, 'rb') as f:
        response = requests.post(UPLOAD_ENDPOINT, headers=headers, files={'file': f})
    response.raise_for_status()
    return response.json()['upload_url']

def transcribe_with_assemblyai(audio_url, timeout=300):
    headers = {
        'authorization': ASSEMBLYAI_API_KEY,
        'content-type': 'application/json'
    }
    json = { "audio_url": audio_url, "language_code": "en" }
    response = requests.post(TRANSCRIBE_ENDPOINT, json=json, headers=headers)
    response.raise_for_status()
    transcript_id = response.json()['id']

    polling_endpoint = f"{TRANSCRIBE_ENDPOINT}/{transcript_id}"
    start_time = time.time()
    while True:
        poll_response = requests.get(polling_endpoint, headers=headers)
        poll_response.raise_for_status()
        status = poll_response.json()['status']
        print(f"AssemblyAI status: {status} (waiting...)")  # <-- Status update
        if status == 'completed':
            return poll_response.json()['text']
        elif status == 'failed' or status == 'error':
            print("AssemblyAI error details:", poll_response.json())
            raise Exception("Transcription failed:", poll_response.json())
        if time.time() - start_time > timeout:
            raise TimeoutError("AssemblyAI transcription timed out.")
        time.sleep(3)

def extract_text(path: str) -> str:
    """
    Transcribe the isolated audio file using AssemblyAI's official API pattern.
    """
    # Convert to wav if needed
    file_name = mp3_to_wav(path)
    import soundfile as sf
    import os

    # Re-encode to standard PCM 16-bit mono 44.1kHz
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

    # Upload audio file
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    with open(file_name, 'rb') as f:
        print("Uploading audio to AssemblyAI...")
        upload_response = requests.post(UPLOAD_ENDPOINT, headers=headers, files={'file': f})
    upload_response.raise_for_status()
    audio_url = upload_response.json()['upload_url']

    # Start transcription
    transcript_request = {
        'audio_url': audio_url,
        'language_code': 'en'
    }
    print("Requesting transcription from AssemblyAI...")
    transcript_response = requests.post(
        TRANSCRIBE_ENDPOINT, json=transcript_request, headers=headers
    )
    transcript_response.raise_for_status()
    transcript_id = transcript_response.json()['id']
    polling_endpoint = f"{TRANSCRIBE_ENDPOINT}/{transcript_id}"

    # Poll for completion
    print("Polling AssemblyAI for transcription status...")
    start_time = time.time()
    timeout = 300  # 5 minutes
    while True:
        poll_response = requests.get(polling_endpoint, headers=headers)
        poll_response.raise_for_status()
        status = poll_response.json()['status']
        print(f"AssemblyAI status: {status} (waiting...)")
        if status == 'completed':
            return poll_response.json().get('text', '')
        elif status == 'failed' or status == 'error':
            print("AssemblyAI error details:", poll_response.json())
            raise Exception("Transcription failed:", poll_response.json())
        if time.time() - start_time > timeout:
            raise TimeoutError("AssemblyAI transcription timed out.")
        time.sleep(3)

def reencode_wav(input_path, output_path):
    """
    Re-encode a WAV file to standard PCM 16-bit mono 44.1kHz using ffmpeg.
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1", output_path
    ]
    subprocess.run(cmd, check=True)
