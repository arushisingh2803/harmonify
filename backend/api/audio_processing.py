import librosa
import numpy as np
import requests
import tempfile
import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="librosa")
warnings.filterwarnings("ignore", category=FutureWarning, module="librosa")

def extract_features_from_url(preview_url):
    audio_bytes = requests.get(preview_url).content

    with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        y, sr = librosa.load(tmp_path, sr=22050, duration=30)

        tempo, _     = librosa.beat.beat_track(y=y, sr=sr)
        centroid     = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        zcr          = np.mean(librosa.feature.zero_crossing_rate(y=y))
        rms          = np.mean(librosa.feature.rms(y=y))
        spectral_contrast = float(np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)))
        spectral_flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        mood = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))

    finally:
        # clean up for temp file - it was causing memory issues
        os.unlink(tmp_path)

    return {
        "tempo":    float(tempo),
        "centroid": float(centroid),
        "zcr":      float(zcr),
        "rms":      float(rms),
        "mood":     mood,
        "spectral_contrast": spectral_contrast,
        "spectral_flatness": spectral_flatness,
    }