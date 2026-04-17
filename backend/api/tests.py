from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock
from core.models import UserProfile, SpotifyToken, Concert, ChatRoom, Message
from ml.user_profile import _compute_diversity, _build_feature_vector
import json


# ── Authentication Tests ────────────────────────────────────────────────────

class AuthenticationTests(TestCase):

    def test_login_redirects_to_spotify(self):
        client = Client()
        response = client.get("/login/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.spotify.com/authorize", response["Location"])

    def test_login_url_contains_required_scopes(self):
        client = Client()
        response = client.get("/login/")
        location = response["Location"]
        self.assertIn("user-read-private", location)
        self.assertIn("user-read-email", location)
        self.assertIn("user-top-read", location)

    def test_callback_missing_code_returns_400(self):
        client = Client()
        response = client.get("/callback/")
        self.assertEqual(response.status_code, 400)

    def test_spotify_token_is_expired(self):
        user = User.objects.create_user(username="testuser", password="test")
        token = SpotifyToken.objects.create(
            user=user,
            spotify_user_id="test_spotify_id",
            access_token="old_token",
            refresh_token="refresh_token",
            expires_at=timezone.now() - timezone.timedelta(seconds=10),
        )
        self.assertTrue(token.is_expired())

    def test_spotify_token_is_not_expired(self):
        user = User.objects.create_user(username="testuser2", password="test")
        token = SpotifyToken.objects.create(
            user=user,
            spotify_user_id="test_spotify_id_2",
            access_token="valid_token",
            refresh_token="refresh_token",
            expires_at=timezone.now() + timezone.timedelta(seconds=3600),
        )
        self.assertFalse(token.is_expired())

    def test_profile_endpoint_without_token_returns_401(self):
        client = Client()
        response = client.get("/profile/")
        self.assertEqual(response.status_code, 401)


# ── Feature Vector Tests ────────────────────────────────────────────────────

class FeatureVectorTests(TestCase):

    def setUp(self):
        self.top_artists = [
            {"id": f"artist_{i}", "genres": ["pop", "indie"]}
            for i in range(10)
        ]
        self.top_genres  = ["pop", "indie", "rock", "jazz", "electronic"]
        self.top_tracks  = [
            {"artists": [{"id": f"artist_{i}"}]}
            for i in range(10)
        ]
        self.audio_features = {
            "tempo":             120.0,
            "centroid":          3000.0,
            "zcr":               0.10,
            "rms":               0.20,
            "spectral_contrast": 25.0,
            "spectral_flatness": 0.10,
        }

    def test_zero_audio_features_produces_valid_vector(self):
        zero_features = {
            "tempo": 0.0, "centroid": 0.0, "zcr": 0.0,
            "rms": 0.0, "spectral_contrast": 0.0, "spectral_flatness": 0.0,
        }
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, self.top_genres, self.top_tracks
        )
        vector = _build_feature_vector(
            zero_features, self.top_genres,
            self.top_artists, self.top_tracks,
            gd, ad, ge, tad
        )
        self.assertEqual(len(vector), 10)

    def test_feature_vector_all_numeric(self):
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, self.top_genres, self.top_tracks
        )
        vector = _build_feature_vector(
            self.audio_features, self.top_genres,
            self.top_artists, self.top_tracks,
            gd, ad, ge, tad
        )
        for val in vector:
            self.assertIsInstance(val, float)

    def test_feature_vector_no_negative_values(self):
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, self.top_genres, self.top_tracks
        )
        vector = _build_feature_vector(
            self.audio_features, self.top_genres,
            self.top_artists, self.top_tracks,
            gd, ad, ge, tad
        )
        for val in vector:
            self.assertGreaterEqual(val, 0.0)


    def test_zero_audio_features_produces_valid_vector(self):
        zero_features = {
            "tempo": 0.0, "centroid": 0.0, "zcr": 0.0,
            "rms": 0.0, "spectral_contrast": 0.0, "spectral_flatness": 0.0,
        }
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, self.top_genres, self.top_tracks
        )
        vector = _build_feature_vector(
            zero_features, self.top_genres,
            self.top_artists, self.top_tracks,
            gd, ad, ge, tad
        )
        self.assertEqual(len(vector), 10)

    def test_high_diversity_genres_produce_high_diversity_score(self):
        many_genres = [f"genre_{i}" for i in range(25)]
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, many_genres, self.top_tracks
        )
        self.assertGreater(gd, 0.5)

    def test_single_genre_produces_low_entropy(self):
        single_genre = ["pop"] * 20
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, single_genre, self.top_tracks
        )
        self.assertLess(ge, 0.1)

    def test_many_unique_track_artists_produce_high_track_diversity(self):
        diverse_tracks = [
            {"artists": [{"id": f"unique_artist_{i}"}]}
            for i in range(20)
        ]
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, self.top_genres, diverse_tracks
        )
        self.assertGreater(tad, 0.8)

    def test_same_artist_all_tracks_produces_low_track_diversity(self):
        loyal_tracks = [
            {"artists": [{"id": "same_artist"}]}
            for _ in range(20)
        ]
        gd, ad, ge, tad = _compute_diversity(
            self.top_artists, self.top_genres, loyal_tracks
        )
        self.assertLess(tad, 0.1)


# ── Persona Classification Tests ────────────────────────────────────────────

class PersonaClassificationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testclassify", password="test"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            feature_vector=[0.0] * 10,
            persona_type="The Guardian",
            cluster_id=0,
        )

    def test_user_profile_created_correctly(self):
        self.assertEqual(self.profile.persona_type, "The Guardian")
        self.assertEqual(self.profile.cluster_id, 0)

    def test_feature_vector_stored_as_list(self):
        self.assertIsInstance(self.profile.feature_vector, list)

    def test_feature_vector_length_stored_correctly(self):
        self.assertEqual(len(self.profile.feature_vector), 10)

    def test_persona_endpoint_returns_correct_data(self):
        client = Client()
        response = client.get(f"/user-persona/?user_id={self.user.id}")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["persona_type"], "The Guardian")
        self.assertEqual(data["cluster_id"], 0)

    def test_persona_endpoint_missing_user_id_returns_400(self):
        client = Client()
        response = client.get("/user-persona/")
        self.assertEqual(response.status_code, 400)

    def test_persona_endpoint_invalid_user_returns_404(self):
        client = Client()
        response = client.get("/user-persona/?user_id=99999")
        self.assertEqual(response.status_code, 404)


# ── Similar Users Tests ─────────────────────────────────────────────────────

class SimilarUsersTests(TestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="test")
        self.user2 = User.objects.create_user(username="user2", password="test")
        self.user3 = User.objects.create_user(username="user3", password="test")

        self.profile1 = UserProfile.objects.create(
            user=self.user1,
            cluster_id=0,
            persona_type="The Guardian",
            feature_vector=[1.0, 0.5, 0.3, 0.2, 0.1, 0.1, 0.8, 0.4, 0.3, 0.2],
            top_genres=["pop", "indie"],
            top_artist_ids=["artist_1", "artist_2"],
            top_artist_names=["Artist One", "Artist Two"],
            top_artist_images=["", ""],
        )
        self.profile2 = UserProfile.objects.create(
            user=self.user2,
            cluster_id=0,
            persona_type="The Guardian",
            feature_vector=[1.1, 0.6, 0.3, 0.2, 0.1, 0.1, 0.7, 0.4, 0.3, 0.2],
            top_genres=["pop", "rock"],
            top_artist_ids=["artist_1", "artist_3"],
            top_artist_names=["Artist One", "Artist Three"],
            top_artist_images=["", ""],
        )
        self.profile3 = UserProfile.objects.create(
            user=self.user3,
            cluster_id=1,
            persona_type="The Seeker",
            feature_vector=[2.0, 1.5, 1.0, 0.9, 0.8, 0.7, 0.1, 0.1, 0.1, 0.1],
            top_genres=["jazz", "electronic"],
            top_artist_ids=["artist_4"],
            top_artist_names=["Artist Four"],
            top_artist_images=[""],
        )

    def test_similar_users_endpoint_returns_200(self):
        client   = Client()
        response = client.get(f"/similar-users/?user_id={self.user1.id}")
        self.assertEqual(response.status_code, 200)

    def test_similar_users_only_returns_same_cluster(self):
        client   = Client()
        response = client.get(f"/similar-users/?user_id={self.user1.id}")
        data     = json.loads(response.content)
        returned_ids = [m["user_id"] for m in data["matches"]]
        self.assertIn(self.user2.id, returned_ids)
        self.assertNotIn(self.user3.id, returned_ids)

    def test_similar_users_excludes_self(self):
        client   = Client()
        response = client.get(f"/similar-users/?user_id={self.user1.id}")
        data     = json.loads(response.content)
        returned_ids = [m["user_id"] for m in data["matches"]]
        self.assertNotIn(self.user1.id, returned_ids)

    def test_shared_genres_identified_correctly(self):
        client   = Client()
        response = client.get(f"/similar-users/?user_id={self.user1.id}")
        data     = json.loads(response.content)
        match    = next(m for m in data["matches"] if m["user_id"] == self.user2.id)
        self.assertIn("pop", match["shared_genres"])
        self.assertNotIn("rock", match["shared_genres"])

    def test_shared_artists_identified_correctly(self):
        client   = Client()
        response = client.get(f"/similar-users/?user_id={self.user1.id}")
        data     = json.loads(response.content)
        match    = next(m for m in data["matches"] if m["user_id"] == self.user2.id)
        shared_ids = [a["id"] for a in match["shared_artists"]]
        self.assertIn("artist_1", shared_ids)
        self.assertNotIn("artist_3", shared_ids)

    def test_match_percentage_between_0_and_100(self):
        client   = Client()
        response = client.get(f"/similar-users/?user_id={self.user1.id}")
        data     = json.loads(response.content)
        for match in data["matches"]:
            self.assertGreaterEqual(match["match_pct"], 0)
            self.assertLessEqual(match["match_pct"], 100)

    def test_similar_users_missing_user_id_returns_400(self):
        client   = Client()
        response = client.get("/similar-users/")
        self.assertEqual(response.status_code, 400)

    def test_similar_users_unclassified_user_returns_400(self):
        unclassified = User.objects.create_user(username="unclassified", password="test")
        UserProfile.objects.create(
            user=unclassified,
            cluster_id=None,
            feature_vector=[],
        )
        client   = Client()
        response = client.get(f"/similar-users/?user_id={unclassified.id}")
        self.assertEqual(response.status_code, 400)


# ── Concert and Chat Tests ──────────────────────────────────────────────────

class ConcertTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="concertuser", password="test")
        self.concert = Concert.objects.create(
            spotify_artist_id="artist_1",
            artist_name="Test Artist",
            venue="Test Venue",
            date="2026-06-01",
            ticketmaster_id="TM123456",
        )
        self.room = ChatRoom.objects.create(concert=self.concert)

    def test_concert_created_correctly(self):
        self.assertEqual(self.concert.artist_name, "Test Artist")
        self.assertEqual(self.concert.ticketmaster_id, "TM123456")

    def test_chatroom_linked_to_concert(self):
        self.assertEqual(self.room.concert, self.concert)

    def test_message_persisted_correctly(self):
        message = Message.objects.create(
            room=self.room,
            user=self.user,
            content="Hello from the test",
        )
        self.assertEqual(message.content, "Hello from the test")
        self.assertEqual(message.user, self.user)
        self.assertEqual(message.room, self.room)

    def test_messages_ordered_by_timestamp(self):
        Message.objects.create(room=self.room, user=self.user, content="First")
        Message.objects.create(room=self.room, user=self.user, content="Second")
        messages = list(Message.objects.filter(room=self.room))
        self.assertEqual(messages[0].content, "First")
        self.assertEqual(messages[1].content, "Second")

    def test_concert_str_representation(self):
        self.assertEqual(str(self.concert), "Test Artist @ Test Venue")

    def test_get_or_create_does_not_duplicate_concert(self):
        Concert.objects.get_or_create(
            ticketmaster_id="TM123456",
            defaults={
                "spotify_artist_id": "artist_1",
                "artist_name":       "Test Artist",
                "venue":             "Test Venue",
                "date":              "2026-06-01",
            }
        )
        count = Concert.objects.filter(ticketmaster_id="TM123456").count()
        self.assertEqual(count, 1)


# ── Audio Processing Tests ──────────────────────────────────────────────────

class AudioProcessingTests(TestCase):

    @patch("api.audio_processing.requests.get")
    @patch("api.audio_processing.librosa.load")
    @patch("api.audio_processing.librosa.beat.beat_track")
    def test_extract_features_returns_expected_keys(
        self, mock_beat, mock_load, mock_get
    ):
        from api.audio_processing import extract_features_from_url
        import numpy as np

        mock_get.return_value.content = b"fake_audio_bytes"
        mock_load.return_value        = (np.zeros(22050), 22050)
        mock_beat.return_value        = (120.0, None)

        with patch("api.audio_processing.librosa.feature.spectral_centroid",
                   return_value=np.array([[3000.0]])), \
             patch("api.audio_processing.librosa.feature.zero_crossing_rate",
                   return_value=np.array([[0.1]])), \
             patch("api.audio_processing.librosa.feature.rms",
                   return_value=np.array([[0.2]])), \
             patch("api.audio_processing.librosa.feature.spectral_contrast",
                   return_value=np.array([[25.0]])), \
             patch("api.audio_processing.librosa.feature.spectral_flatness",
                   return_value=np.array([[0.1]])), \
             patch("api.audio_processing.librosa.feature.spectral_rolloff",
                   return_value=np.array([[4000.0]])), \
             patch("api.audio_processing.os.unlink"):
            features = extract_features_from_url("http://fake-url.com/preview.m4a")

        expected_keys = ["tempo", "centroid", "zcr", "rms", "mood",
                         "spectral_contrast", "spectral_flatness"]
        for key in expected_keys:
            self.assertIn(key, features)

    def test_itunes_preview_returns_none_for_empty_result(self):
        from api.spotify import get_itunes_preview
        with patch("api.spotify.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"resultCount": 0, "results": []}
            result = get_itunes_preview("Unknown Track", "Unknown Artist")
            self.assertIsNone(result)