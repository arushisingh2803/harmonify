import requests
import numpy as np
from .audio_processing import extract_features_from_url


def get_itunes_preview(track_name, artist_name):
    query = f"{track_name} {artist_name}".replace(" ", "+")
    url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
    try:
        response = requests.get(url).json()
        if response.get("resultCount", 0) > 0:
            return response["results"][0].get("previewUrl")
        return None
    except:
        return None


def fetch_top_tracks(access_token, time_range="long_term", limit=10):
    response = requests.get(
        "https://api.spotify.com/v1/me/top/tracks",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": limit, "time_range": time_range}
    )
    return response.json().get("items", [])


def fetch_top_artists(access_token, time_range="long_term", limit=20):
    response = requests.get(
        "https://api.spotify.com/v1/me/top/artists",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": limit, "time_range": time_range}
    )
    return response.json().get("items", [])


def extract_avg_audio_features(tracks):
    collected = []

    for t in tracks:
        preview_url = get_itunes_preview(t["name"], t["artists"][0]["name"])
        if preview_url:
            try:
                collected.append(extract_features_from_url(preview_url))
            except Exception as e:
                print(f"Audio extraction failed for {t['name']}: {e}")

    if not collected:
        return {}

    return {
        "tempo":    float(np.mean([f["tempo"]    for f in collected])),
        "centroid": float(np.mean([f["centroid"] for f in collected])),
        "zcr":      float(np.mean([f["zcr"]      for f in collected])),
        "rms":      float(np.mean([f["rms"]      for f in collected])),
        "mood":     float(np.mean([f["mood"]     for f in collected])),
        "spectral_contrast": float(np.mean([f["spectral_contrast"] for f in collected])),
        "spectral_flatness": float(np.mean([f["spectral_flatness"] for f in collected])),
    }