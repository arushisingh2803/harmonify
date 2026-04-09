import librosa
import numpy as np
import requests
import tempfile
import os

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
        mfcc         = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean    = mfcc.mean(axis=1)
        spectral_contrast = float(np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)))
        spectral_flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        # Energy — RMS per frame averaged, more stable than single RMS value
        energy = float(np.mean(librosa.feature.rms(y=y)))

        # Mood — spectral rolloff at 85% as a proxy for brightness/positivity
        mood = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))

    finally:
        # clean up for temp file - it was causing memory issues
        os.unlink(tmp_path)

    return {
        "tempo":    float(tempo),
        "centroid": float(centroid),
        "zcr":      float(zcr),
        "rms":      float(rms),
        "energy":   energy,
        "mood":     mood,
        "mfcc":     mfcc_mean.tolist(),
        "spectral_contrast": spectral_contrast,
        "spectral_flatness": spectral_flatness,
    }