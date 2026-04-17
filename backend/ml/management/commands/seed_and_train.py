import numpy as np
import random
import joblib
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from collections import Counter
from core.models import UserProfile
from ml.user_profile import (
    PERSONA_DEFINITIONS,
    AUDIO_WEIGHT,
    SPECTRAL_WEIGHT,
    DIVERSITY_WEIGHT,
    _rank_centroid,
    _best_persona_for_centroid,
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'saved_models')
KMEANS_PATH = os.path.join(MODEL_DIR, 'kmeans.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

ARCHETYPES = [
    {
        "name":   "seeker",
        "genres": ["electronic", "indie", "jazz", "latin", "folk", "reggae", "blues"],
        "audio":  {
            "tempo":             lambda: random.uniform(110, 145),
            "centroid":          lambda: random.uniform(2500, 4500),
            "zcr":               lambda: random.uniform(0.06, 0.12),
            "rms":               lambda: random.uniform(0.18, 0.28),
            "spectral_contrast": lambda: random.uniform(20, 32),
            "spectral_flatness": lambda: random.uniform(0.08, 0.18),
        },
        "diversity": lambda: (
            random.uniform(0.65, 0.95),   # genre diversity — high
            random.uniform(0.60, 0.90),   # artist diversity — high
            random.uniform(0.75, 0.95),   # genre entropy — high
            random.uniform(0.70, 0.95),   # track artist diversity — high
        ),
    },
    {
        "name":   "guardian",
        "genres": ["indie", "alternative", "pop", "r&b", "art pop", "dream pop", "rock"],
        "audio":  {
            "tempo":             lambda: random.uniform(95, 130),
            "centroid":          lambda: random.uniform(1400, 2500),
            "zcr":               lambda: random.uniform(0.04, 0.09),
            "rms":               lambda: random.uniform(0.18, 0.28),
            "spectral_contrast": lambda: random.uniform(14, 26),
            "spectral_flatness": lambda: random.uniform(0.07, 0.16),
        },
        "diversity": lambda: (
            random.uniform(0.10, 0.30),   # genre diversity — low
            random.uniform(0.15, 0.40),   # artist diversity — low
            random.uniform(0.35, 0.60),   # genre entropy — medium
            random.uniform(0.20, 0.45),   # track artist diversity — low
        ),
    },
    {
        "name":   "zealous",
        "genres": ["metal", "electronic", "punk", "dance"],
        "audio":  {
            "tempo":             lambda: random.uniform(150, 190),
            "centroid":          lambda: random.uniform(4000, 6000),
            "zcr":               lambda: random.uniform(0.11, 0.18),
            "rms":               lambda: random.uniform(0.24, 0.32),
            "spectral_contrast": lambda: random.uniform(28, 42),
            "spectral_flatness": lambda: random.uniform(0.03, 0.08),
        },
        "diversity": lambda: (
            random.uniform(0.30, 0.55),
            random.uniform(0.45, 0.70),
            random.uniform(0.50, 0.72),
            random.uniform(0.40, 0.65),
        ),
    },
    {
        "name":   "wistful",
        "genres": ["soul", "blues", "jazz", "classical", "folk"],
        "audio":  {
            "tempo":             lambda: random.uniform(58, 88),
            "centroid":          lambda: random.uniform(800, 1800),
            "zcr":               lambda: random.uniform(0.02, 0.05),
            "rms":               lambda: random.uniform(0.12, 0.20),
            "spectral_contrast": lambda: random.uniform(8, 16),
            "spectral_flatness": lambda: random.uniform(0.15, 0.28),
        },
        "diversity": lambda: (
            random.uniform(0.25, 0.50),
            random.uniform(0.20, 0.42),
            random.uniform(0.52, 0.72),
            random.uniform(0.30, 0.55),
        ),
    },
    {
        "name":   "formalist",
        "genres": ["metal"],
        "audio":  {
            "tempo":             lambda: random.uniform(140, 185),
            "centroid":          lambda: random.uniform(3800, 5800),
            "zcr":               lambda: random.uniform(0.10, 0.16),
            "rms":               lambda: random.uniform(0.22, 0.32),
            "spectral_contrast": lambda: random.uniform(30, 45),
            "spectral_flatness": lambda: random.uniform(0.02, 0.06),
        },
        "diversity": lambda: (
            random.uniform(0.02, 0.10),   # genre diversity — very low
            random.uniform(0.80, 0.99),   # artist diversity — high within genre
            random.uniform(0.00, 0.12),   # genre entropy — very low
            random.uniform(0.05, 0.20),   # track artist diversity — very low
        ),
    },
]

ARCHETYPE_TO_PERSONA = {
    "seeker":    "The Seeker",
    "guardian":  "The Guardian",
    "zealous":   "The Zealous",
    "wistful":   "The Wistful",
    "formalist": "The Formalist",
}


def _make_feature_vector(archetype):
    a = archetype["audio"]

    audio_vec = [
        (a["tempo"]()             / 200.0)  * AUDIO_WEIGHT,
        (a["centroid"]()          / 6000.0) * AUDIO_WEIGHT,
        (a["zcr"]()               / 0.20)   * AUDIO_WEIGHT,
        (a["rms"]()               / 0.30)   * AUDIO_WEIGHT,
    ]

    spectral_vec = [
        a["spectral_contrast"]() * SPECTRAL_WEIGHT,
        a["spectral_flatness"]() * SPECTRAL_WEIGHT,
    ]

    # 4 diversity values — gdiv, adiv, gentropy, track_artist_div
    # concentration removed — redundant with entropy
    # artist rank vector removed — replaced by track_artist_diversity
    gd, ad, ge, tad = archetype["diversity"]()
    diversity_vec = [
        gd  * DIVERSITY_WEIGHT,
        ad  * DIVERSITY_WEIGHT,
        ge  * DIVERSITY_WEIGHT,
        tad * DIVERSITY_WEIGHT,
    ]

    return audio_vec + spectral_vec + diversity_vec


class Command(BaseCommand):
    help = "Seeds synthetic profiles and trains the initial KMeans model"

    def add_arguments(self, parser):
        parser.add_argument('--users-per-archetype', type=int, default=20)
        parser.add_argument('--clusters',            type=int, default=5)
        parser.add_argument('--skip-seed',           action='store_true')

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

                    a       = archetype["audio"]
                    tempo   = a["tempo"]()
                    centroid = a["centroid"]()
                    zcr     = a["zcr"]()
                    rms     = a["rms"]()
                    gd, ad, ge, tad = archetype["diversity"]()

                    persona_name = ARCHETYPE_TO_PERSONA[archetype["name"]]
                    definition   = next(
                        p for p in PERSONA_DEFINITIONS if p["name"] == persona_name
                    )

                    UserProfile.objects.create(
                        user=user,
                        top_genres=archetype["genres"],
                        top_artist_ids=[],
                        top_track_ids=[],
                        avg_tempo=tempo,
                        avg_zcr=zcr,
                        avg_rms=rms,
                        avg_centroid=centroid,
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

        # load synthetic profiles only — real users classified separately after training
        profiles = list(UserProfile.objects.filter(
            user__username__startswith='synthetic_'
        ).exclude(feature_vector=[]))

        self.stdout.write(f"Training on {len(profiles)} synthetic profiles...")

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

        # assign labels back to each synthetic profile and save to database
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