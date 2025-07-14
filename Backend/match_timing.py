import librosa
import numpy as np

def find_best_match_time(query_audio_path, song_audio_path):
    q_audio, q_sr = librosa.load(query_audio_path)
    s_audio, s_sr = librosa.load(song_audio_path)

    if q_sr != s_sr:
        raise ValueError("Sample rates must match")

    q_mfcc = librosa.feature.mfcc(y=q_audio, sr=q_sr)
    s_mfcc = librosa.feature.mfcc(y=s_audio, sr=s_sr)

    similarity = librosa.sequence.dtw(X=q_mfcc, Y=s_mfcc, metric='cosine')[0]
    min_index = np.unravel_index(np.argmin(similarity), similarity.shape)

    match_time_sec = librosa.frames_to_time(min_index[1], sr=s_sr)
    return match_time_sec
