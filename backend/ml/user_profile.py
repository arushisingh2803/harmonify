# ml/user_profile.py
import numpy as np
import requests
import base64
from django.utils import timezone
from django.conf import settings
from sklearn.preprocessing import StandardScaler
from core.models import UserProfile, SpotifyToken
# helper functions for building user profile - avoid repetition
from api.spotify import fetch_top_tracks, fetch_top_artists, extract_avg_audio_features

# token managemet for user access and API calls to Spotify - especially for refreshing tokens
def _get_access_token(user):
    """Retrieves a valid access token, refreshing if expired."""
    spotify_token = SpotifyToken.objects.get(user=user)

    if spotify_token.is_expired():
        auth_str = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": spotify_token.refresh_token,
            },
            headers={"Authorization": f"Basic {b64_auth}"}
        )
        data = response.json()
        spotify_token.access_token = data["access_token"]
        # spotify tokens typically last 1 hour
        spotify_token.expires_at = timezone.now() + timezone.timedelta(seconds=3600)
        spotify_token.save()

    return spotify_token.access_token

# computing diversity scores for user's music taste based on their top artists and top genres
def _compute_diversity(top_artists, top_genres):
    total_genres = len(top_genres)
    unique_genres = len(set(top_genres))
    genre_diversity = unique_genres / total_genres if total_genres > 0 else 0.0

    unique_artists = len(set(a["id"] for a in top_artists))
    artist_diversity = unique_artists / max(len(top_artists), 1)

    return genre_diversity, artist_diversity


# converts categorical data(genres, artists) into numerical vectors for ML model
GENRE_VOCABULARY = [
    "pop", "rock", "hip-hop", "electronic", "indie",
    "r&b", "jazz", "classical", "metal", "country",
    "folk", "latin", "soul", "punk", "alternative",
    "dance", "reggae", "blues", "other"
]


# genres are encoded as binary presence vectors based on a fixed vocabulary of popular genres
def _encode_genres(user_genres):
    genre_set = set(g.lower() for g in user_genres)
    return [1.0 if g in genre_set else 0.0 for g in GENRE_VOCABULARY]

# artists are encoded using weighted hashing to create a fixed-size vector that represents the user's top artists with correct importance.
def _encode_artists(top_artists, vocab_size=50):
    vector = np.zeros(vocab_size)
    total = len(top_artists)
    for rank, artist in enumerate(top_artists):
        weight = (total - rank) / total
        bucket = hash(artist["id"]) % vocab_size
        vector[bucket] += weight
    if vector.sum() > 0:
        vector = vector / vector.sum()
    return vector.tolist()

# final feature vector built by combining audio features, genre and artist encodings - also normalised for ML model input.
def _build_feature_vector(audio_features, top_genres, top_artists,
                           genre_diversity, artist_diversity):
    audio_vec = [
        audio_features.get("tempo", 0.0),
        audio_features.get("centroid", 0.0),
        audio_features.get("zcr", 0.0),
        audio_features.get("rms", 0.0),
    ]
    mfcc = audio_features.get("mfcc", [0.0] * 13)
    if len(mfcc) < 13:
        mfcc = mfcc + [0.0] * (13 - len(mfcc))

    genre_vec    = _encode_genres(top_genres)
    artist_vec   = _encode_artists(top_artists)
    diversity_vec = [genre_diversity, artist_diversity]

    return audio_vec + mfcc + genre_vec + artist_vec + diversity_vec

# main function to call all the relevant functions in order to build the user profile.
def build_user_profile(user):
    token = _get_access_token(user)

    print(f"[user_profile] Fetching Spotify data for {user.username}...")

    top_artists = fetch_top_artists(token)
    top_tracks  = fetch_top_tracks(token)

    top_artist_ids = [a["id"] for a in top_artists]
    top_track_ids  = [t["id"] for t in top_tracks]
    top_genres     = [g for a in top_artists for g in a.get("genres", [])]

    print(f"[user_profile] Extracting audio features...")
    audio_features = extract_avg_audio_features(top_tracks)

    genre_diversity, artist_diversity = _compute_diversity(top_artists, top_genres)

    raw_vector = _build_feature_vector(
        audio_features, top_genres, top_artists,
        genre_diversity, artist_diversity
    )

    scaler = StandardScaler()
    normalised_vector = scaler.fit_transform(
        np.array(raw_vector).reshape(1, -1)
    ).flatten().tolist()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.top_artist_ids         = top_artist_ids
    profile.top_track_ids          = top_track_ids
    profile.top_genres             = list(set(top_genres))
    profile.avg_tempo              = audio_features.get("tempo")
    profile.avg_energy             = None
    profile.avg_zcr                = audio_features.get("zcr")
    profile.avg_rms                = audio_features.get("rms")
    profile.avg_centroid           = audio_features.get("centroid")
    profile.avg_mfcc               = audio_features.get("mfcc", [])
    profile.genre_diversity_score  = genre_diversity
    profile.artist_diversity_score = artist_diversity
    profile.feature_vector         = normalised_vector
    profile.last_synced            = timezone.now()
    profile.save()

    print(f"[user_profile] Profile saved for {user.username}.")
    return profile