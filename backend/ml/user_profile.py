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
    # genre diversity — ratio of unique MAPPED genres to vocabulary size
    # a user with 3 genres gets a lower score than one with 12
    from ml.user_profile import _normalise_genre
    mapped_genres = [_normalise_genre(g) for g in top_genres]
    unique_mapped  = len(set(mapped_genres) - {"other"})
    # genre is normalised to a 0-1 scale based on how many distinct genres the user has
    genre_diversity = unique_mapped / 18.0

    # artist diversity — use genre spread across artists instead
    # count how many distinct genre buckets the artists cover
    artist_genres = set()
    for artist in top_artists:
        for g in artist.get("genres", []):
            artist_genres.add(_normalise_genre(g))
    artist_genres.discard("other")
    # artist diversity is normalised to a 0-1 scale
    artist_diversity = min(len(artist_genres) / 10.0, 1.0)

    return genre_diversity, artist_diversity


GENRE_VOCABULARY = [
    "pop", "rock", "hip-hop", "electronic", "indie",
    "r&b", "jazz", "classical", "metal", "country",
    "folk", "latin", "soul", "punk", "alternative",
    "dance", "reggae", "blues", "other"
]

# spotify sub-genres are mapped to a parent genre to reduce dimensionality and create a more generalizable model
GENRE_PARENT_MAP = {
    # Pop variants
    "art pop": "pop", "bedroom pop": "pop", "hyperpop": "pop",
    "indie pop": "pop", "dream pop": "pop", "synth-pop": "pop",
    "electropop": "pop", "k-pop": "pop", "j-pop": "pop",
    "power pop": "pop", "bubblegum pop": "pop", "city pop": "pop",

    # Hip-hop variants
    "rap": "hip-hop", "trap": "hip-hop", "drill": "hip-hop",
    "conscious hip hop": "hip-hop", "southern hip hop": "hip-hop",
    "east coast hip hop": "hip-hop", "west coast hip hop": "hip-hop",
    "lo-fi hip hop": "hip-hop", "alternative hip hop": "hip-hop",
    "hip hop": "hip-hop",

    # Rock variants
    "garage rock": "rock", "indie rock": "rock", "alt-rock": "rock",
    "classic rock": "rock", "hard rock": "rock", "psych rock": "rock",
    "neo-psychedelic": "rock", "shoegaze": "rock", "post-rock": "rock",
    "grunge": "rock", "emo": "rock", "math rock": "rock",

    # Electronic variants
    "edm": "electronic", "techno": "electronic", "house": "electronic",
    "ambient": "electronic", "dubstep": "electronic", "drum and bass": "electronic",
    "trance": "electronic", "chillwave": "electronic", "lo-fi": "electronic",
    "synthwave": "electronic", "vaporwave": "electronic", "idm": "electronic",

    # Indie variants
    "indie folk": "indie", "indie r&b": "indie", "indie soul": "indie",
    "chamber pop": "indie", "lo-fi indie": "indie",

    # R&B variants
    "soul": "r&b", "neo soul": "r&b", "contemporary r&b": "r&b",
    "quiet storm": "r&b", "new jack swing": "r&b", "indie r&b": "r&b",

    # Jazz variants
    "jazz fusion": "jazz", "nu jazz": "jazz", "bebop": "jazz",
    "smooth jazz": "jazz", "acid jazz": "jazz", "jazz rap": "jazz",

    # Metal variants
    "heavy metal": "metal", "death metal": "metal", "black metal": "metal",
    "thrash metal": "metal", "doom metal": "metal", "metalcore": "metal",
    "post-metal": "metal", "nu metal": "metal",

    # Folk variants
    "indie folk": "folk", "folk rock": "folk", "anti-folk": "folk",
    "freak folk": "folk", "contemporary folk": "folk", "singer-songwriter": "folk",

    # Latin variants
    "reggaeton": "latin", "latin pop": "latin", "salsa": "latin",
    "bossa nova": "latin", "latin rock": "latin", "cumbia": "latin",
    "flamenco": "latin", "latin jazz": "latin",

    # Country variants
    "country pop": "country", "alt-country": "country", "bluegrass": "country",
    "americana": "country", "outlaw country": "country",

    # Soul variants
    "neo soul": "soul", "classic soul": "soul", "southern soul": "soul",
    "funk": "soul", "motown": "soul",

    # Bollywood / desi
    "bollywood": "other", "desi": "other", "hindi pop": "other",
    "filmi": "other", "punjabi pop": "other",

    # Punk variants
    "post-punk": "punk", "pop punk": "punk", "hardcore punk": "punk",
    "skate punk": "punk", "folk punk": "punk",

    # Dance variants
    "disco": "dance", "funk": "dance", "dancehall": "dance",
    "afrobeats": "dance", "uk garage": "dance",

    # Blues variants
    "delta blues": "blues", "chicago blues": "blues", "electric blues": "blues",

    # Classical variants
    "orchestral": "classical", "opera": "classical", "baroque": "classical",
    "contemporary classical": "classical", "chamber music": "classical",
}

# maps a Spotify sub-genre to its broad parent category
def _normalise_genre(genre: str) -> str:
    g = genre.lower().strip()
    # direct match in vocabulary
    if g in GENRE_VOCABULARY:
        return g
    # check parent mapping for known sub-genres
    if g in GENRE_PARENT_MAP:
        return GENRE_PARENT_MAP[g]
    # fallback to "other" if no match found
    for vocab_genre in GENRE_VOCABULARY[:-1]: 
        if vocab_genre in g:
            return vocab_genre
    return "other"

 # maps all genres to parent categories first
def _encode_genres(user_genres):
    mapped = set(_normalise_genre(g) for g in user_genres)
    return [1.0 if g in mapped else 0.0 for g in GENRE_VOCABULARY]

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
    audio_weight = 3.0

    audio_vec = [
        audio_features.get("tempo", 0.0)    * audio_weight,
        audio_features.get("centroid", 0.0) * audio_weight,
        audio_features.get("zcr", 0.0)      * audio_weight,
        audio_features.get("rms", 0.0)      * audio_weight,
    ]

    mfcc = audio_features.get("mfcc", [0.0] * 13)
    if len(mfcc) < 13:
        mfcc = mfcc + [0.0] * (13 - len(mfcc))
    mfcc = [v * audio_weight for v in mfcc]

    genre_vec     = _encode_genres(top_genres)
    artist_vec    = _encode_artists(top_artists)
    diversity_vec = [genre_diversity * 5.0, artist_diversity * 5.0]

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
    raw_vector_list = [float(v) for v in raw_vector]

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
    profile.feature_vector         = raw_vector_list
    profile.last_synced            = timezone.now()
    profile.save()

    print(f"[user_profile] Profile saved for {user.username}.")
    try:
        classify_new_user(profile)
        print(f"[user_profile] Persona assigned: {profile.persona_type}")
    except FileNotFoundError:
        print("[user_profile] No trained model yet ")

    return profile

FEAT_TEMPO            = 0
FEAT_RMS              = 3
FEAT_GENRE_DIVERSITY  = 86
FEAT_ARTIST_DIVERSITY = 87

PERSONA_DEFINITIONS = [
    {"name": "The Seeker",  "tags": ["eclectic", "adventurous", "genre-fluid"],
     "dominant": {"genre_diversity": "high", "tempo": "high"}},
    {"name": "The Guardian",   "tags": ["refined", "consistent", "deep-cuts"],
     "dominant": {"artist_diversity": "low", "genre_diversity": "low"}},
    {"name": "The Zealous",  "tags": ["high-energy", "bass-heavy", "intense"],
     "dominant": {"tempo": "high", "rms": "high"}},
    {"name": "The Wistful", "tags": ["mellow", "sentimental", "slow-burn"],
     "dominant": {"tempo": "low", "rms": "low"}},
    {"name": "The Socialite", "tags": ["mainstream", "pop-driven", "trend-aware"],
     "dominant": {"genre_diversity": "mid", "artist_diversity": "mid"}},
    {"name": "The Formalist",    "tags": ["genre-loyal", "deep-listener", "niche"],
     "dominant": {"genre_diversity": "low", "artist_diversity": "high"}},
]


def _rank_centroid(centroid):
   # converts centroid values into categorical ratings(low, mid, high)
    def level(value, low, high):
        if value < low:  return "low"
        if value > high: return "high"
        return "mid"
    return {
        "tempo":            level(centroid[FEAT_TEMPO], -0.5, 0.5),
        "rms":              level(centroid[FEAT_RMS], -0.5, 0.5),
        "genre_diversity":  level(centroid[FEAT_GENRE_DIVERSITY], -0.3, 0.3),
        "artist_diversity": level(centroid[FEAT_ARTIST_DIVERSITY], -0.3, 0.3),
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
    model_dir = os.path.join(os.path.dirname(__file__), 'saved_models')
    kmeans = joblib.load(os.path.join(model_dir, 'kmeans.pkl'))
    scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))

    vector = np.array(user_profile.feature_vector).reshape(1, -1)
    vector_scaled = scaler.transform(vector)
    cluster_id = int(kmeans.predict(vector_scaled)[0])

    centroid = kmeans.cluster_centers_[cluster_id]
    ratings = _rank_centroid(centroid)
    persona_name, persona_tags = _best_persona_for_centroid(ratings)

    user_profile.cluster_id   = cluster_id
    user_profile.persona_type = persona_name
    user_profile.persona_tags = persona_tags
    user_profile.save()

    return persona_name, persona_tags