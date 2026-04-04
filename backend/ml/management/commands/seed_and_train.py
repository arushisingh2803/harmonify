import numpy as np
import random
import joblib
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from core.models import UserProfile
from ml.user_profile import (
    GENRE_VOCABULARY,
    PERSONA_DEFINITIONS,
    AUDIO_WEIGHT,
    MFCC_WEIGHT,
    GENRE_WEIGHT,
    ARTIST_WEIGHT,
    DIVERSITY_WEIGHT,
    _rank_centroid,
    _best_persona_for_centroid,
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'saved_models')
KMEANS_PATH = os.path.join(MODEL_DIR, 'kmeans.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

ARCHETYPES = [
    {"name": "seeker",
     "audio": {"tempo": 128, "centroid": 3800, "zcr": 0.09, "rms": 0.22},
     "genres": ["electronic", "indie", "jazz", "latin", "folk", "reggae", "blues"],
     "diversity": (0.90, 0.95)},

     "audio": {"tempo": 128, "centroid": 3800, "zcr": 0.09, "rms": 0.22},
     "genres": ["electronic", "indie", "jazz", "latin", "folk", "reggae", "blues"],
     "diversity": (0.90, 0.95)},

    {"name": "guardian",
     "audio": {"tempo": 95,  "centroid": 1600, "zcr": 0.04, "rms": 0.16},
     "audio": {"tempo": 95,  "centroid": 1600, "zcr": 0.04, "rms": 0.16},
     "genres": ["indie", "alternative", "folk"],
     "diversity": (0.15, 0.12)},

     "diversity": (0.15, 0.12)},

    {"name": "zealous",
     "audio": {"tempo": 168, "centroid": 5200, "zcr": 0.14, "rms": 0.28},
     "audio": {"tempo": 168, "centroid": 5200, "zcr": 0.14, "rms": 0.28},
     "genres": ["electronic", "metal", "dance", "punk"],
     "diversity": (0.58, 0.62)},

     "diversity": (0.58, 0.62)},

    {"name": "wistful",
     "audio": {"tempo": 68,  "centroid": 1200, "zcr": 0.03, "rms": 0.15},
     "genres": ["soul", "blues", "jazz", "classical"],
     "diversity": (0.38, 0.30)},

     "audio": {"tempo": 68,  "centroid": 1200, "zcr": 0.03, "rms": 0.15},
     "genres": ["soul", "blues", "jazz", "classical"],
     "diversity": (0.38, 0.30)},

    {"name": "socialite",
     "audio": {"tempo": 118, "centroid": 2900, "zcr": 0.07, "rms": 0.24},
     "audio": {"tempo": 118, "centroid": 2900, "zcr": 0.07, "rms": 0.24},
     "genres": ["pop", "dance", "r&b", "latin"],
     "diversity": (0.52, 0.58)},

     "diversity": (0.52, 0.58)},

    {"name": "formalist",
     "audio": {"tempo": 105, "centroid": 2300, "zcr": 0.05, "rms": 0.19},
     "audio": {"tempo": 105, "centroid": 2300, "zcr": 0.05, "rms": 0.19},
     "genres": ["metal"],
     "diversity": (0.06, 0.85)},
     "diversity": (0.06, 0.85)},
]

# maps archetype name to persona definition for majority-vote labelling
ARCHETYPE_TO_PERSONA = {
    "seeker":    "The Seeker",
    "guardian":  "The Guardian",
    "zealous":   "The Zealous",
    "wistful":   "The Wistful",
    "socialite": "The Socialite",
    "formalist": "The Formalist",
}


def _make_feature_vector(archetype, noise=0.05):
    a = archetype["audio"]
    audio_weight = 3.0

    def jitter(val):
        return val * (1 + random.gauss(0, noise))

    audio_vec = [
        jitter(a["tempo"])    * audio_weight,
        jitter(a["centroid"]) * audio_weight,
        jitter(a["zcr"])      * audio_weight,
        jitter(a["rms"])      * audio_weight,
    ]

    mfcc_vec = [
        jitter(random.gauss(0, 1) * (i + 1) * 0.5) * audio_weight
        for i in range(13)
    ]

    genre_set = set(archetype["genres"])
    genre_vec = [
        (1.0 if g in genre_set else 0.0) * GENRE_WEIGHT
        for g in GENRE_VOCABULARY
    ]

    # deterministic artist vector per archetype so same archetype = similar artists
    artist_vec = np.zeros(50)
    base_ids = [hash(archetype["name"] + str(i)) for i in range(10)]
    for i, aid in enumerate(base_ids):
        bucket = aid % 50
        artist_vec[bucket] += (10 - i) / 10
    if artist_vec.sum() > 0:
        artist_vec = artist_vec / artist_vec.sum()
    artist_vec = (artist_vec * ARTIST_WEIGHT).tolist()

    # diversity weighted to match _build_feature_vector
    gd, ad = archetype["diversity"]
    diversity_vec = [jitter(gd) * 5.0, jitter(ad) * 5.0]

    return audio_vec + mfcc_vec + genre_vec + artist_vec + diversity_vec


class Command(BaseCommand):
    help = "Seeds synthetic profiles and trains the initial KMeans model"

    def add_arguments(self, parser):
        parser.add_argument('--users-per-archetype', type=int, default=20)
        parser.add_argument('--clusters', type=int, default=6)
        parser.add_argument('--skip-seed', action='store_true')

    def handle(self, *args, **options):
        n = options['users_per_archetype']
        k = options['clusters']
        os.makedirs(MODEL_DIR, exist_ok=True)

        # creates synthetic user profiles based on predefined archetypes with randomised feature vectors around the defining characteristics
        if not options['skip_seed']:
            self.stdout.write(f"Seeding {n} users x {len(ARCHETYPES)} archetypes...")
            for archetype in ARCHETYPES:
                for i in range(n):
                    username = f"synthetic_{archetype['name']}_{i}"
                    if User.objects.filter(username=username).exists():
                        continue
                    user = User.objects.create_user(username=username, password="synthetic")
                    gd, ad = archetype["diversity"]
                    persona_name = ARCHETYPE_TO_PERSONA[archetype["name"]]
                    definition   = next(
                        p for p in PERSONA_DEFINITIONS
                        if p["name"] == persona_name
                    )
                    UserProfile.objects.create(
                        user=user,
                        top_genres=archetype["genres"],
                        top_artist_ids=[],
                        top_track_ids=[],
                        avg_tempo=archetype["audio"]["tempo"],
                        avg_zcr=archetype["audio"]["zcr"],
                        avg_rms=archetype["audio"]["rms"],
                        avg_centroid=archetype["audio"]["centroid"],
                        avg_mfcc=[],
                        genre_diversity_score=gd,
                        artist_diversity_score=ad,
                        feature_vector=_make_feature_vector(archetype),
                        persona_type=persona_name,
                        persona_tags=definition["tags"],
                        last_synced=timezone.now(),
                    )
            self.stdout.write(self.style.SUCCESS(
                f"Seeded {n * len(ARCHETYPES)} synthetic profiles."
            ))

        # load all user profiles(synthetic + real) with feature vectors and train KMeans to assign cluster
        profiles = list(UserProfile.objects.exclude(feature_vector=[]))
        self.stdout.write(f"Training on {len(profiles)} profiles...")

        if len(profiles) < k:
            self.stdout.write(self.style.ERROR(f"Need at least {k} profiles."))
            return

        vectors = np.array([p.feature_vector for p in profiles])

        # normalises the feature vectors before training to ensure all features are given equal weight in the cluster
        scaler = StandardScaler()
        vectors_scaled = scaler.fit_transform(vectors)

        # train KMeans model on the scaled feature vectors
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(vectors_scaled)

        # rank features of each centroid against overall dataset to determine defining characteristics of each cluster
        # majority vote — each cluster is labelled by the most common pre-assigned persona among its members
        from collections import Counter
        cluster_to_persona = {}
        for cid in range(k):
            cluster_profiles = [
                p for p, label in zip(profiles, kmeans.labels_)
                if label == cid and p.persona_type
            ]
            if cluster_profiles:
                vote       = Counter(p.persona_type for p in cluster_profiles)
                best_name  = vote.most_common(1)[0][0]
                definition = next(
                    p for p in PERSONA_DEFINITIONS if p["name"] == best_name
                )
                cluster_to_persona[cid] = (best_name, definition["tags"])
                self.stdout.write(
                    f"  Cluster {cid} -> {best_name} (votes: {dict(vote)})"
                )
            else:
                # fallback to centroid ranking if cluster has no labelled profiles
                ratings = _rank_centroid(kmeans.cluster_centers_[cid])
                name, tags = _best_persona_for_centroid(ratings)
                cluster_to_persona[cid] = (name, tags)
                self.stdout.write(f"  Cluster {cid} -> {name} (centroid fallback)")

        # assign labels back to each user profile and save to database
        for profile, label in zip(profiles, kmeans.labels_):
            name, tags = cluster_to_persona[int(label)]
            profile.cluster_id   = int(label)
            profile.persona_type = name
            profile.persona_tags = tags

        UserProfile.objects.bulk_update(
            profiles, ["cluster_id", "persona_type", "persona_tags"]
        )

        # model saved to disk for later use in classifying new users in real time
        joblib.dump(kmeans, KMEANS_PATH)
        joblib.dump(scaler, SCALER_PATH)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Model saved. {len(profiles)} profiles labelled."
        ))