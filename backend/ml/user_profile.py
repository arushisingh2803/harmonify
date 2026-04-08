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
GENRE_WEIGHT     = 3.0
ARTIST_WEIGHT    = 1.0
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


# computing diversity scores for user's music taste based on their top artists and top genres
def _compute_diversity(top_artists, top_genres):
    # genre diversity — ratio of unique mapped genres to vocabulary size
    # a user with 3 genres gets a lower score than one with 12
    mapped_genres = [_normalise_genre(g) for g in top_genres]
    unique_mapped  = len(set(mapped_genres) - {"other"})
    # genre is normalised to a 0-1 scale based on how many distinct genres the user has
    genre_diversity = unique_mapped / len(GENRE_VOCABULARY)

    # artist diversity — use genre spread across artists instead
    # count how many distinct genre buckets the artists cover
    artist_genres = set()
    for artist in top_artists:
        for g in artist.get("genres", []):
            artist_genres.add(_normalise_genre(g))
    artist_genres.discard("other")
    # artist diversity is normalised to a 0-1 scale
    artist_diversity = min(len(artist_genres) / 10.0, 1.0)

    # genre concentration — how dominant is the single top genre
    # high concentration = user listens mostly to one genre (formalist)
    # low concentration = user spread evenly across genres (seeker)
    clean = [g for g in mapped_genres if g != "other"]
    if clean:
        counts = Counter(clean)
        genre_concentration = counts.most_common(1)[0][1] / len(clean)
    else:
        genre_concentration = 0.0

    return genre_diversity, artist_diversity, genre_concentration


GENRE_VOCABULARY = [
    "pop", "rock", "hip-hop", "electronic", "indie",
    "r&b", "jazz", "classical", "metal", "country",
    "folk", "latin", "soul", "punk", "alternative",
    "dance", "reggae", "blues",
    "singer-songwriter", "ambient", "lo-fi",
    "k-pop", "afrobeats", "gospel", "other"
]

# spotify sub-genres are mapped to a parent genre to reduce dimensionality and create a more generalizable model
GENRE_PARENT_MAP = {
    # Pop variants
    "art pop": "pop", "bedroom pop": "pop", "hyperpop": "pop",
    "indie pop": "pop", "dream pop": "pop", "synth-pop": "pop",
    "electropop": "pop", "k-pop": "k-pop", "j-pop": "pop",
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
    "ambient": "ambient", "dubstep": "electronic", "drum and bass": "electronic",
    "trance": "electronic", "chillwave": "electronic", "lo-fi": "lo-fi",
    "synthwave": "electronic", "vaporwave": "electronic", "idm": "electronic",

    # Indie variants
    "indie folk": "indie", "indie r&b": "indie", "indie soul": "indie",
    "chamber pop": "indie", "lo-fi indie": "indie",

    # R&B variants
    "neo soul": "r&b", "contemporary r&b": "r&b",
    "quiet storm": "r&b", "new jack swing": "r&b", "indie r&b": "r&b",

    # Jazz variants
    "jazz fusion": "jazz", "nu jazz": "jazz", "bebop": "jazz",
    "smooth jazz": "jazz", "acid jazz": "jazz", "jazz rap": "jazz",

    # Metal variants
    "heavy metal": "metal", "death metal": "metal", "black metal": "metal",
    "thrash metal": "metal", "doom metal": "metal", "metalcore": "metal",
    "post-metal": "metal", "nu metal": "metal",

    # Folk variants
    "folk rock": "folk", "anti-folk": "folk", "freak folk": "folk",
    "contemporary folk": "folk", "singer-songwriter": "singer-songwriter",

    # Latin variants
    "reggaeton": "latin", "latin pop": "latin", "salsa": "latin",
    "bossa nova": "latin", "latin rock": "latin", "cumbia": "latin",
    "flamenco": "latin", "latin jazz": "latin",

    # Country variants
    "country pop": "country", "alt-country": "country", "bluegrass": "country",
    "americana": "country", "outlaw country": "country",

    # Soul variants
    "soul": "soul", "classic soul": "soul", "southern soul": "soul",
    "funk": "soul", "motown": "soul",

    # Bollywood / desi
    "bollywood": "other", "desi": "other", "hindi pop": "other",
    "filmi": "other", "punjabi pop": "other",

    # Punk variants
    "post-punk": "punk", "pop punk": "punk", "hardcore punk": "punk",
    "skate punk": "punk", "folk punk": "punk",

    # Dance variants
    "disco": "dance", "dancehall": "dance",
    "afrobeats": "afrobeats", "uk garage": "dance",

    # Blues variants
    "delta blues": "blues", "chicago blues": "blues", "electric blues": "blues",

    # Classical variants
    "orchestral": "classical", "opera": "classical", "baroque": "classical",
    "contemporary classical": "classical", "chamber music": "classical",

    # Gospel
    "gospel": "gospel", "christian music": "gospel",
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
    # fallback — partial match against vocabulary
    for vocab_genre in GENRE_VOCABULARY[:-1]:
        if vocab_genre in g:
            return vocab_genre
    return "other"


# maps all genres to parent categories first
def _encode_genres(user_genres):
    mapped = set(_normalise_genre(g) for g in user_genres)
    return [1.0 if g in mapped else 0.0 for g in GENRE_VOCABULARY]


# artists are encoded as a rank-weighted vector of size 10
# position = rank, value = normalised rank weight
# no hashing — avoids collision noise from hash bucketing
def _encode_artists(top_artists, vocab_size=10):
    vector = np.zeros(vocab_size)
    total  = len(top_artists)
    for rank, artist in enumerate(top_artists[:vocab_size]):
        vector[rank] = (total - rank) / total
    if vector.sum() > 0:
        vector = vector / vector.sum()
    return vector.tolist()


# final feature vector built by combining audio features, genre and artist encodings
# vector layout (42 dims total):
#   [0-3]   audio scalars normalised to 0-1    × AUDIO_WEIGHT     (4)
#   [4-5]   spectral contrast + flatness        × SPECTRAL_WEIGHT  (2)
#   [6-30]  genre one-hot                       × GENRE_WEIGHT     (25)
#   [31-40] artist rank vector                  × ARTIST_WEIGHT    (10)
#   [41-43] diversity (genre, artist, conc.)    × DIVERSITY_WEIGHT (3)
def _build_feature_vector(audio_features, top_genres, top_artists,
                           genre_diversity, artist_diversity, genre_concentration):
    # normalise audio to 0-1 before weighting — prevents scale dominance
    audio_vec = [
        (audio_features.get("tempo",    0.0) / 200.0)  * AUDIO_WEIGHT,
        (audio_features.get("centroid", 0.0) / 6000.0) * AUDIO_WEIGHT,
        (audio_features.get("zcr",      0.0) / 0.20)   * AUDIO_WEIGHT,
        (audio_features.get("rms",      0.0) / 0.30)   * AUDIO_WEIGHT,
    ]

    # spectral features — more musically meaningful than raw MFCC for persona
    spectral_vec = [
        audio_features.get("spectral_contrast", 0.0) * SPECTRAL_WEIGHT,
        audio_features.get("spectral_flatness", 0.0) * SPECTRAL_WEIGHT,
    ]

    # GENRE
    genre_vec = [g * GENRE_WEIGHT for g in _encode_genres(top_genres)]

    # ARTIST
    artist_vec = [a * ARTIST_WEIGHT for a in _encode_artists(top_artists)]

    # DIVERSITY — 3 metrics give KMeans stronger signal
    diversity_vec = [
        genre_diversity     * DIVERSITY_WEIGHT,
        artist_diversity    * DIVERSITY_WEIGHT,
        genre_concentration * DIVERSITY_WEIGHT,
    ]

    return audio_vec + spectral_vec + genre_vec + artist_vec + diversity_vec


# main function to call all the relevant functions in order to build the user profile.
def build_user_profile(user):
    token = _get_access_token(user)

    print(f"[user_profile] Fetching Spotify data for {user.username}...")

    top_artists = fetch_top_artists(token)
    top_tracks  = fetch_top_tracks(token)

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

    genre_diversity, artist_diversity, genre_concentration = _compute_diversity(
        top_artists, top_genres
    )

    raw_vector = _build_feature_vector(
        audio_features, top_genres, top_artists,
        genre_diversity, artist_diversity, genre_concentration
    )
    raw_vector_list = [float(v) for v in raw_vector]

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.top_artist_ids         = top_artist_ids
    profile.top_track_ids          = top_track_ids
    profile.top_artist_names       = top_artist_names
    profile.top_artist_images      = top_artist_images
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


PERSONA_DEFINITIONS = [
    {"name": "The Seeker",    "tags": ["eclectic", "adventurous", "genre-fluid"],
     "dominant": {"genre_diversity": "high", "genre_concentration": "low"}},
    {"name": "The Guardian",  "tags": ["refined", "consistent", "deep-cuts"],
     "dominant": {"artist_diversity": "low", "genre_diversity": "low"}},
    {"name": "The Zealous",   "tags": ["high-energy", "bass-heavy", "intense"],
     "dominant": {"tempo": "high", "rms": "high"}},
    {"name": "The Wistful",   "tags": ["mellow", "sentimental", "slow-burn"],
     "dominant": {"tempo": "low", "rms": "low"}},
    {"name": "The Socialite", "tags": ["mainstream", "pop-driven", "trend-aware"],
     "dominant": {"genre_diversity": "mid", "artist_diversity": "mid"}},
    {"name": "The Formalist", "tags": ["genre-loyal", "deep-listener", "niche"],
     "dominant": {"genre_concentration": "high", "artist_diversity": "high"}},
]

FEAT_TEMPO        = 0
FEAT_RMS          = 3
FEAT_GENRE_DIV    = -3
FEAT_ARTIST_DIV   = -2
FEAT_GENRE_CONC   = -1


def _rank_centroid(vec):
    def level(v, low=-1.0, high=1.0):
        if v < low:  return "low"
        if v > high: return "high"
        return "mid"

    return {
        "tempo":              level(vec[FEAT_TEMPO]),
        "rms":                level(vec[FEAT_RMS]),
        "genre_diversity":    level(vec[FEAT_GENRE_DIV]),
        "artist_diversity":   level(vec[FEAT_ARTIST_DIV]),
        "genre_concentration": level(vec[FEAT_GENRE_CONC]),
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

    vec        = np.array(user_profile.feature_vector).reshape(1, -1)
    vec_scaled = scaler.transform(vec)
    cluster_id = int(kmeans.predict(vec_scaled)[0])

    # use the cluster centroid to determine persona via centroid ranking
    centroid = kmeans.cluster_centers_[cluster_id]
    ratings  = _rank_centroid(centroid)
    name, tags = _best_persona_for_centroid(ratings)

    user_profile.cluster_id   = cluster_id
    user_profile.persona_type = name
    user_profile.persona_tags = tags
    user_profile.save()

    return name, tags