import librosa
import numpy as np
import requests
import tempfile

def extract_features_from_url(preview_url):
    audio_bytes = requests.get(preview_url).content


    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    y, sr = librosa.load(tmp_path, sr=22050, duration=30)

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    zcr = np.mean(librosa.feature.zero_crossing_rate(y=y))
    rms = np.mean(librosa.feature.rms(y=y))
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = mfcc.mean(axis=1)

    return {
        "tempo": float(tempo),
        "centroid": float(centroid),
        "zcr": float(zcr),
        "rms": float(rms),
        "mfcc": mfcc_mean.tolist()
    }
