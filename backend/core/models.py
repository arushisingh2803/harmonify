from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Concert(models.Model):
    spotify_artist_id = models.CharField(max_length=100)
    artist_name = models.CharField(max_length=255)
    venue = models.CharField(max_length=255)
    date = models.DateField()

    def __str__(self):
        return f"{self.artist_name} @ {self.venue}"


class ChatRoom(models.Model):
    concert = models.OneToOneField(
        Concert,
        on_delete=models.CASCADE,
        related_name="chat_room"
    )

    def __str__(self):
        return f"Chat for {self.concert}"


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

class SpotifyToken(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="spotify_token"
    )
    spotify_user_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"SpotifyToken({self.display_name})"


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    top_artist_ids = models.JSONField(default=list, blank=True)
    top_genres = models.JSONField(default=list, blank=True)
    top_track_ids = models.JSONField(default=list, blank=True)
    top_artist_names  = models.JSONField(default=list, blank=True)
    top_artist_images = models.JSONField(default=list, blank=True)

    avg_tempo = models.FloatField(null=True, blank=True)
    avg_energy = models.FloatField(null=True, blank=True)
    avg_zcr = models.FloatField(null=True, blank=True)
    avg_rms = models.FloatField(null=True, blank=True)
    avg_centroid = models.FloatField(null=True, blank=True)
    avg_mfcc = models.JSONField(default=list, blank=True)
    avg_spectral_contrast = models.FloatField(null=True, blank=True)
    avg_spectral_flatness = models.FloatField(null=True, blank=True)

    genre_diversity_score = models.FloatField(null=True, blank=True)
    artist_diversity_score = models.FloatField(null=True, blank=True)

    cluster_id = models.IntegerField(null=True, blank=True)
    persona_type = models.CharField(max_length=100, blank=True)
    persona_tags = models.JSONField(default=list, blank=True)

    feature_vector = models.JSONField(default=list, blank=True)

    last_synced = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def needs_sync(self, hours=24):
        if not self.last_synced:
            return True
        delta = timezone.now() - self.last_synced
        return delta.total_seconds() > hours * 3600

    def __str__(self):
        return f"Profile({self.user.username} — {self.persona_type or 'unclassified'})"


class UserMatch(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="matches_from"
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="matches_to"
    )
    similarity_score = models.FloatField()
    shared_genres = models.JSONField(default=list, blank=True)
    shared_artists = models.JSONField(default=list, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("from_user", "to_user")
        ordering = ["similarity_score"]

    def __str__(self):
        return (
            f"{self.from_user.username} ↔ {self.to_user.username} "
            f"(score: {self.similarity_score:.3f})"
        )