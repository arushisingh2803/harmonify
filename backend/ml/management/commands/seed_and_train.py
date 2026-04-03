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
    _rank_centroid,
    _best_persona_for_centroid,
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'saved_models')
KMEANS_PATH = os.path.join(MODEL_DIR, 'kmeans.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

ARCHETYPES = [
    {"name": "seeker",
     "audio": {"tempo": 130, "centroid": 3000, "zcr": 0.08, "rms": 0.05},
     "genres": ["electronic", "indie", "jazz", "latin", "folk"],
     "diversity": (0.85, 0.80)},
    {"name": "guardian",
     "audio": {"tempo": 110, "centroid": 2000, "zcr": 0.04, "rms": 0.03},
     "genres": ["indie", "alternative", "folk"],
     "diversity": (0.20, 0.15)},
    {"name": "zealous",
     "audio": {"tempo": 160, "centroid": 4500, "zcr": 0.12, "rms": 0.09},
     "genres": ["electronic", "metal", "dance", "punk"],
     "diversity": (0.55, 0.60)},
    {"name": "wistful",
     "audio": {"tempo": 75, "centroid": 1500, "zcr": 0.02, "rms": 0.02},
     "genres": ["soul", "blues", "jazz", "folk", "classical"],
     "diversity": (0.40, 0.35)},
    {"name": "socialite",
     "audio": {"tempo": 120, "centroid": 2800, "zcr": 0.06, "rms": 0.04},
     "genres": ["pop", "dance", "r&b", "latin"],
     "diversity": (0.50, 0.55)},
    {"name": "formalist",
     "audio": {"tempo": 100, "centroid": 2200, "zcr": 0.05, "rms": 0.035},
     "genres": ["metal"],
     "diversity": (0.10, 0.75)},
]


def _make_feature_vector(archetype, noise=0.15):
    a = archetype["audio"]

    def jitter(val):
        return val * (1 + random.gauss(0, noise))

    audio_vec = [jitter(a["tempo"]), jitter(a["centroid"]),
                 jitter(a["zcr"]), jitter(a["rms"])]
    mfcc_vec  = [jitter(random.gauss(0, 1) * (i + 1) * 0.5) for i in range(13)]

    genre_set = set(archetype["genres"])
    genre_vec = [1.0 if g in genre_set else 0.0 for g in GENRE_VOCABULARY]

    artist_vec = np.zeros(50)
    for _ in range(random.randint(5, 15)):
        artist_vec[random.randint(0, 49)] += random.uniform(0.05, 0.3)
    if artist_vec.sum() > 0:
        artist_vec = artist_vec / artist_vec.sum()

    gd, ad = archetype["diversity"]
    diversity_vec = [jitter(gd), jitter(ad)]

    return audio_vec + mfcc_vec + genre_vec + artist_vec.tolist() + diversity_vec


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

        # rank features of each centroid against overall dataset to determine defining characteristics of each cluster and assign persona labels accordingly
        cluster_to_persona = {}
        for cid in range(k):
            ratings = _rank_centroid(kmeans.cluster_centers_[cid])
            name, tags = _best_persona_for_centroid(ratings)
            cluster_to_persona[cid] = (name, tags)
            self.stdout.write(f"  Cluster {cid} -> {name} {tags}")

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