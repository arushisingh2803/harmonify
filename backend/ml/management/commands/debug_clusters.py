import numpy as np
import joblib
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile

class Command(BaseCommand):
    help = "Diagnoses cluster distances for real users"

    def handle(self, *args, **options):
        model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'saved_models')
        kmeans = joblib.load(os.path.join(model_dir, 'kmeans.pkl'))
        scaler  = joblib.load(os.path.join(model_dir, 'scaler.pkl'))

        cluster_labels = {}
        for cid in range(kmeans.n_clusters):
            sample = UserProfile.objects.filter(
                cluster_id=cid,
                user__username__startswith='synthetic_'
            ).first()
            cluster_labels[cid] = sample.persona_type if sample else "?"

        self.stdout.write(f"Cluster map: {cluster_labels}")
        self.stdout.write(f"Model expects {scaler.n_features_in_} features\n")

        # ── Synthetic archetype audio summary ──────────────────────────
        self.stdout.write("=" * 60)
        self.stdout.write("SYNTHETIC ARCHETYPE AUDIO SUMMARY")
        self.stdout.write("=" * 60)

        archetype_names = ['guardian', 'seeker', 'wistful', 'zealous', 'formalist']
        for name in archetype_names:
            profiles = list(UserProfile.objects.filter(
                user__username__startswith=f'synthetic_{name}'
            )[:10])
            if not profiles:
                self.stdout.write(f"\nsynthetic_{name}: NO PROFILES FOUND")
                continue

            tempos    = [p.avg_tempo    for p in profiles if p.avg_tempo]
            centroids = [p.avg_centroid for p in profiles if p.avg_centroid]
            rms_vals  = [p.avg_rms      for p in profiles if p.avg_rms]
            gdivs     = [p.genre_diversity_score for p in profiles if p.genre_diversity_score]

            self.stdout.write(f"\nsynthetic_{name} ({len(profiles)} sampled):")
            self.stdout.write(f"  tempo:    {np.mean(tempos):.1f}  (range {min(tempos):.1f}–{max(tempos):.1f})")
            self.stdout.write(f"  centroid: {np.mean(centroids):.0f}  (range {min(centroids):.0f}–{max(centroids):.0f})")
            self.stdout.write(f"  rms:      {np.mean(rms_vals):.3f}  (range {min(rms_vals):.3f}–{max(rms_vals):.3f})")
            self.stdout.write(f"  gdiv:     {np.mean(gdivs):.2f}  (range {min(gdivs):.2f}–{max(gdivs):.2f})")

        # ── Real user audio summary ────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("REAL USER AUDIO SUMMARY")
        self.stdout.write("=" * 60)

        for user in User.objects.exclude(username__startswith='synthetic_'):
            p = UserProfile.objects.get(user=user)
            self.stdout.write(f"\n{user.username}")
            self.stdout.write(f"  tempo:    {p.avg_tempo:.1f}")
            self.stdout.write(f"  centroid: {p.avg_centroid:.0f}")
            self.stdout.write(f"  rms:      {p.avg_rms:.3f}")
            self.stdout.write(f"  gdiv:     {p.genre_diversity_score:.2f}")
            self.stdout.write(f"  genres:   {p.top_genres[:5]}")

        # ── Cluster distance diagnosis ─────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("CLUSTER DISTANCE DIAGNOSIS")
        self.stdout.write("=" * 60)

        for user in User.objects.exclude(username__startswith='synthetic_'):
            p = UserProfile.objects.get(user=user)
            self.stdout.write(f"\n{user.username}")
            self.stdout.write(f"  vector length: {len(p.feature_vector)}")

            if len(p.feature_vector) != scaler.n_features_in_:
                self.stdout.write(self.style.ERROR(
                    f"  MISMATCH — vector is {len(p.feature_vector)} dims, "
                    f"model expects {scaler.n_features_in_}"
                ))
                continue

            vec        = np.array(p.feature_vector).reshape(1, -1)
            vec_scaled = scaler.transform(vec)
            distances  = kmeans.transform(vec_scaled)[0]
            predicted  = int(kmeans.predict(vec_scaled)[0])

            for cid, d in enumerate(distances):
                marker = " <--" if cid == predicted else ""
                self.stdout.write(
                    f"  cluster {cid} ({cluster_labels[cid]}): {d:.3f}{marker}"
                )

        # ── Feature space gap analysis ─────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("FEATURE SPACE GAP ANALYSIS")
        self.stdout.write("=" * 60)

        real_profiles = [
            UserProfile.objects.get(user=u)
            for u in User.objects.exclude(username__startswith='synthetic_')
        ]
        synth_profiles = list(
            UserProfile.objects.filter(
                user__username__startswith='synthetic_'
            ).exclude(feature_vector=[])[:100]
        )

        if real_profiles and synth_profiles:
            real_vecs  = np.array([p.feature_vector for p in real_profiles
                                   if len(p.feature_vector) == scaler.n_features_in_])
            synth_vecs = np.array([p.feature_vector for p in synth_profiles
                                   if len(p.feature_vector) == scaler.n_features_in_])

            if len(real_vecs) and len(synth_vecs):
                self.stdout.write(f"\nReal user vector mean (first 6 dims):")
                self.stdout.write(f"  {real_vecs.mean(axis=0)[:6].round(3)}")
                self.stdout.write(f"Synthetic vector mean (first 6 dims):")
                self.stdout.write(f"  {synth_vecs.mean(axis=0)[:6].round(3)}")
                self.stdout.write(f"\nDimension-wise gap (real - synthetic mean):")
                gap = real_vecs.mean(axis=0) - synth_vecs.mean(axis=0)
                self.stdout.write(f"  first 6:       {gap[:6].round(3)}")
                self.stdout.write(f"  last 4 (diversity — gdiv, adiv, entropy, track_artist_div): {gap[-4:].round(3)}")
                self.stdout.write(f"\nLargest gaps (dim index: gap value):")
                top_gaps = np.argsort(np.abs(gap))[::-1][:8]
                for idx in top_gaps:
                    label = ""
                    if idx == 0:   label = "(tempo)"
                    elif idx == 1: label = "(centroid)"
                    elif idx == 2: label = "(zcr)"
                    elif idx == 3: label = "(rms)"
                    elif idx == 4: label = "(spectral_contrast)"
                    elif idx == 5: label = "(spectral_flatness)"
                    elif idx == scaler.n_features_in_ - 4: label = "(genre_diversity)"
                    elif idx == scaler.n_features_in_ - 3: label = "(artist_diversity)"
                    elif idx == scaler.n_features_in_ - 2: label = "(genre_entropy)"
                    elif idx == scaler.n_features_in_ - 1: label = "(track_artist_diversity)"
                    self.stdout.write(f"  dim {idx} {label}: {gap[idx]:.3f}")