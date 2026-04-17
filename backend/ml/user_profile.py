import math
import numpy as np
import requests
import base64
from collections import Counter
from django.utils import timezone
from django.conf import settings
from core.models import UserProfile, SpotifyToken
from api.spotify import fetch_top_tracks, fetch_top_artists, extract_avg_audio_features

# shared weights for feature vector construction - it is tuned to give more importance to audio features and diversity metrics.
AUDIO_WEIGHT     = 5.0
SPECTRAL_WEIGHT  = 3.0
DIVERSITY_WEIGHT = 8.0

# token management for user access and API calls to Spotify
def _get_access_token(user):
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


# computing diversity scores directly from raw spotify genre strings
# no parent mapping — bollywood and pop are treated as genuinely different genres
# this preserves the distinction between niche/world music listeners and mainstream listeners
def _compute_diversity(top_artists, top_genres, top_tracks):
    raw = [g.lower().strip() for g in top_genres]

    # genre breadth — how many unique raw genres appear
    unique_genres   = len(set(raw))
    genre_diversity = min(unique_genres / 30.0, 1.0)

    # genre entropy — how evenly spread listening is across all genres
    # replaces genre_concentration — entropy is more mathematically rigorous
    # high entropy = seeker (spread evenly), low entropy = formalist (concentrated)
    if raw:
        counts      = Counter(raw)
        total       = len(raw)
        probs       = [c / total for c in counts.values()]
        entropy     = -sum(p * math.log2(p) for p in probs if p > 0)
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
        genre_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    else:
        genre_entropy = 0.0

    # artist diversity — unique genre strings across all top artists
    artist_raw_genres = set()
    for artist in top_artists:
        for g in artist.get("genres", []):
            artist_raw_genres.add(g.lower().strip())
    artist_diversity = min(len(artist_raw_genres) / 20.0, 1.0)

    # track artist diversity — unique artists appearing across top 20 tracks
    # low = few artists dominate (guardian/formalist)
    # high = many different artists in top tracks (seeker)
    track_artist_ids = set()
    for track in top_tracks:
        for artist in track.get("artists", []):
            track_artist_ids.add(artist["id"])
    track_artist_diversity = min(len(track_artist_ids) / 20.0, 1.0)

    return genre_diversity, artist_diversity, genre_entropy, track_artist_diversity


# vector layout (10 dims total):
#   [0-3]  audio scalars normalised to 0-1    × AUDIO_WEIGHT     (4)
#   [4-5]  spectral contrast + flatness        × SPECTRAL_WEIGHT  (2)
#   [6-9]  diversity metrics                   × DIVERSITY_WEIGHT (4)
#           genre_diversity, artist_diversity,
#           genre_entropy, track_artist_diversity

def _build_feature_vector(audio_features, top_genres, top_artists, top_tracks,
                           genre_diversity, artist_diversity,
                           genre_entropy, track_artist_diversity):

    # normalise audio to 0-1 before weighting — prevents scale dominance
    audio_vec = [
        (audio_features.get("tempo",    0.0) / 200.0)  * AUDIO_WEIGHT,
        (audio_features.get("centroid", 0.0) / 6000.0) * AUDIO_WEIGHT,
        (audio_features.get("zcr",      0.0) / 0.20)   * AUDIO_WEIGHT,
        (audio_features.get("rms",      0.0) / 0.30)   * AUDIO_WEIGHT,
    ]

    # spectral features — more stable than MFCC when averaged across tracks
    spectral_vec = [
        audio_features.get("spectral_contrast", 0.0) * SPECTRAL_WEIGHT,
        audio_features.get("spectral_flatness", 0.0) * SPECTRAL_WEIGHT,
    ]

    # diversity — highest weight, most discriminative for persona separation
    diversity_vec = [
        genre_diversity        * DIVERSITY_WEIGHT,
        artist_diversity       * DIVERSITY_WEIGHT,
        genre_entropy          * DIVERSITY_WEIGHT,
        track_artist_diversity * DIVERSITY_WEIGHT,
    ]

    return audio_vec + spectral_vec + diversity_vec


# main function to call all the relevant functions in order to build the user profile.
def build_user_profile(user):
    token = _get_access_token(user)

    print(f"[user_profile] Fetching Spotify data for {user.username}...")

    top_artists  = fetch_top_artists(token, limit=20)
    # fetch 20 tracks for audio analysis and diversity computation
    top_tracks   = fetch_top_tracks(token, limit=20)

    top_artist_ids    = [a["id"]   for a in top_artists]
    top_track_ids     = [t["id"]   for t in top_tracks]
    top_genres        = [g for a in top_artists for g in a.get("genres", [])]
    top_artist_names  = [a.get("name", "") for a in top_artists]
    top_artist_images = [
        a["images"][0]["url"] if a.get("images") else ""
        for a in top_artists
    ]

    print(f"[user_profile] Extracting audio features...")
    audio_features = extract_avg_audio_features(top_tracks)

    genre_diversity, artist_diversity, genre_entropy, track_artist_diversity = _compute_diversity(
        top_artists, top_genres, top_tracks
    )

    raw_vector = _build_feature_vector(
        audio_features, top_genres, top_artists, top_tracks,
        genre_diversity, artist_diversity,
        genre_entropy, track_artist_diversity
    )
    raw_vector_list = [float(v) for v in raw_vector]

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.top_artist_ids        = top_artist_ids
    profile.top_track_ids         = top_track_ids
    profile.top_artist_names      = top_artist_names
    profile.top_artist_images     = top_artist_images
    profile.top_genres            = list(set(top_genres))
    profile.avg_tempo             = audio_features.get("tempo")
    profile.avg_energy            = None
    profile.avg_zcr               = audio_features.get("zcr")
    profile.avg_rms               = audio_features.get("rms")
    profile.avg_centroid          = audio_features.get("centroid")
    profile.avg_mfcc              = audio_features.get("mfcc", [])
    profile.avg_spectral_contrast = audio_features.get("spectral_contrast")
    profile.avg_spectral_flatness = audio_features.get("spectral_flatness")
    profile.genre_diversity_score  = genre_diversity
    profile.artist_diversity_score = artist_diversity
    profile.feature_vector        = raw_vector_list
    profile.last_synced           = timezone.now()
    profile.save()

    print(f"[user_profile] Profile saved for {user.username}.")
    try:
        classify_new_user(profile)
        print(f"[user_profile] Persona assigned: {profile.persona_type}")
    except FileNotFoundError:
        print("[user_profile] No trained model yet")

    return profile


# utility function to rebuild feature vector from stored profile fields without API calls
def rebuild_vector_from_stored(user):
    profile = UserProfile.objects.get(user=user)

    audio_features = {
        "tempo":             profile.avg_tempo              or 0.0,
        "centroid":          profile.avg_centroid           or 0.0,
        "zcr":               profile.avg_zcr                or 0.0,
        "rms":               profile.avg_rms                or 0.0,
        "spectral_contrast": profile.avg_spectral_contrast  or 0.0,
        "spectral_flatness": profile.avg_spectral_flatness  or 0.0,
        "mfcc":              profile.avg_mfcc               or [],
    }

    stored_genres = profile.top_genres or []
    top_artists_stub = []
    for i, aid in enumerate(profile.top_artist_ids or []):
        artist_genre = [stored_genres[i % len(stored_genres)]] if stored_genres else []
        top_artists_stub.append({
            "id":     aid,
            "name":   (profile.top_artist_names or [])[i] if i < len(profile.top_artist_names or []) else "",
            "images": [],
            "genres": artist_genre,
        })

    # approximate track artist diversity from stored top artist ids
    # real per-track artist data not stored — use unique top artists as proxy
    top_tracks_stub = [
        {"artists": [{"id": aid}]}
        for aid in (profile.top_artist_ids or [])[:20]
    ]

    genre_diversity, artist_diversity, genre_entropy, track_artist_diversity = _compute_diversity(
        top_artists_stub, stored_genres, top_tracks_stub
    )

    raw_vector = _build_feature_vector(
        audio_features, stored_genres, top_artists_stub, top_tracks_stub,
        genre_diversity, artist_diversity,
        genre_entropy, track_artist_diversity
    )

    profile.feature_vector         = [float(v) for v in raw_vector]
    profile.genre_diversity_score  = genre_diversity
    profile.artist_diversity_score = artist_diversity
    profile.save()

    print(f"[rebuild] {user.username} — gdiv={genre_diversity:.2f}, adiv={artist_diversity:.2f}, ent={genre_entropy:.2f}, tad={track_artist_diversity:.2f}")
    return profile


PERSONA_DEFINITIONS = [
    {"name": "The Seeker",    "tags": ["eclectic", "adventurous", "genre-fluid"],
     "dominant": {"genre_diversity": "high", "genre_entropy": "high", "track_artist_diversity": "high"}},
    {"name": "The Guardian",  "tags": ["refined", "consistent", "deep-cuts"],
     "dominant": {"artist_diversity": "low", "genre_diversity": "low", "track_artist_diversity": "low"}},
    {"name": "The Zealous",   "tags": ["high-energy", "bass-heavy", "intense"],
     "dominant": {"tempo": "high", "rms": "high"}},
    {"name": "The Wistful",   "tags": ["mellow", "sentimental", "slow-burn"],
     "dominant": {"tempo": "low", "rms": "low"}},
    {"name": "The Formalist", "tags": ["genre-loyal", "deep-listener", "niche"],
     "dominant": {"genre_entropy": "low", "genre_diversity": "low", "track_artist_diversity": "low"}},
]

FEAT_TEMPO             = 0
FEAT_RMS               = 3
FEAT_GENRE_DIV         = -4
FEAT_ARTIST_DIV        = -3
FEAT_GENRE_ENT         = -2
FEAT_TRACK_ARTIST_DIV  = -1

def _rank_centroid(vec):
    def level(v, low=-1.0, high=1.0):
        if v < low:  return "low"
        if v > high: return "high"
        return "mid"
    return {
        "tempo":                  level(vec[FEAT_TEMPO]),
        "rms":                    level(vec[FEAT_RMS]),
        "genre_diversity":        level(vec[FEAT_GENRE_DIV]),
        "artist_diversity":       level(vec[FEAT_ARTIST_DIV]),
        "genre_entropy":          level(vec[FEAT_GENRE_ENT]),
        "track_artist_diversity": level(vec[FEAT_TRACK_ARTIST_DIV]),
    }


def _best_persona_for_centroid(centroid_ratings):
    # matches the centroid ratings to the persona definitions above
    best_score, best_persona = -1, PERSONA_DEFINITIONS[0]
    for persona in PERSONA_DEFINITIONS:
        score = sum(
            1 for trait, expected in persona["dominant"].items()
            if centroid_ratings.get(trait) == expected
        )
        if score > best_score:
            best_score, best_persona = score, persona
    return best_persona["name"], best_persona["tags"]


def classify_new_user(user_profile):
    # loads the pre-trained KMeans model and predicts the cluster for user's feature vector
    # uses joblib to load the model and scaler and then applies the same preprocessing on the user's feature vector
    import joblib, os
    from core.models import UserProfile as UP

    model_dir = os.path.join(os.path.dirname(__file__), 'saved_models')
    kmeans = joblib.load(os.path.join(model_dir, 'kmeans.pkl'))
    scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))

    vec        = np.array(user_profile.feature_vector).reshape(1, -1)
    vec_scaled = scaler.transform(vec)
    cluster_id = int(kmeans.predict(vec_scaled)[0])

    # use majority-vote label from synthetic profiles in this cluster
    # avoids centroid ranking mismatch with majority-vote training labels
    sample = UP.objects.filter(
        cluster_id=cluster_id,
        user__username__startswith='synthetic_'
    ).first()

    if sample and sample.persona_type:
        name = sample.persona_type
        tags = sample.persona_tags or []
    else:
        # fallback to centroid ranking if no synthetic profiles in cluster
        centroid = kmeans.cluster_centers_[cluster_id]
        ratings  = _rank_centroid(centroid)
        name, tags = _best_persona_for_centroid(ratings)

    user_profile.cluster_id   = cluster_id
    user_profile.persona_type = name
    user_profile.persona_tags = tags
    user_profile.save()

    return name, tags