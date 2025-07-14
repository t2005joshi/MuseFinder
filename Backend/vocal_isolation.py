import os
import shutil
from spleeter.separator import Separator


def isolate_vocals(input_path: str, output_folder: str = "separated_audio") -> str:
    """
    Isolate vocals from the input audio using Spleeter (2 stems).
    
    Parameters:
        input_path (str): Path to the input audio file.
        output_folder (str): Folder to store separated stems.
        
    Returns:
        str: Path to the isolated vocal WAV file.
    """
    print("🎤 Isolating vocals...")
    
    # Create a Spleeter separator (2 stems: vocals + accompaniment)
    separator = Separator('spleeter:2stems')
    
    # Separate the audio file
    separator.separate_to_file(input_path, output_folder)

    # Get the filename without extension
    file_stem = os.path.splitext(os.path.basename(input_path))[0]
    vocal_path = os.path.join(output_folder, file_stem, 'vocals.wav')

    if not os.path.exists(vocal_path):
        raise FileNotFoundError(f"Vocal file not found at {vocal_path}")

    print(f"✅ Vocals saved at: {vocal_path}")
    return vocal_path
