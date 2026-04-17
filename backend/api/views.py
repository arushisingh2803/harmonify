# all the core API views for Harmonify are in this file
import base64
import requests
import numpy as np
import urllib.parse

from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

from rest_framework import viewsets
from api.models import Task 
from core.models import Concert, SpotifyToken, UserProfile
from .serializers import TaskSerializer
from .spotify import get_itunes_preview, fetch_top_tracks, fetch_top_artists, extract_avg_audio_features

from django.contrib.auth.models import User
from ml.user_profile import build_user_profile

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

# importing API keys from settings for use in views
CLIENT_ID = settings.SPOTIFY_CLIENT_ID
CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI
TICKETMASTER_API_KEY = settings.TICKETMASTER_API_KEY
SCOPES = "user-read-private user-read-email user-top-read"

# fetches valid access token, returns None if no valid token found, fetches new token if expired
def _get_token_for_user_id(user_id):
    try:
        user = User.objects.get(id=user_id)
        print(f"Found user: {user.username}")
        spotify_token = SpotifyToken.objects.get(user=user)
        print(f"Token found, expired: {spotify_token.is_expired()}")
        if spotify_token.is_expired():
            from ml.user_profile import _get_access_token
            return _get_access_token(user)
        return spotify_token.access_token
    except User.DoesNotExist:
        print(f"No user found for id={user_id}")
        return None
    except SpotifyToken.DoesNotExist:
        print(f"No SpotifyToken found for user_id={user_id}")
        return None
    
# spotify auth and data retrieval
def spotify_login(request):
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={SCOPES}"
    )
    return HttpResponseRedirect(auth_url)

# callback endpoint for spotify OAuth flow
def spotify_callback(request):
    print("CALLBACK HIT")
    print(f"Query params: {dict(request.GET)}")
    code = request.GET.get("code")

    if code is None:
        return JsonResponse({"error": "No code returned", "details": dict(request.GET)}, status=400)

    token_url = "https://accounts.spotify.com/api/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    response = requests.post(
        token_url,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        headers={"Authorization": f"Basic {b64_auth}"}
    )

    data = response.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        return JsonResponse({"error": "Failed to get access token", "spotify_response": data}, status=400)

    # spotify profile to get spotify_user_id, display_name, email
    profile_resp = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    spotify_id   = profile_resp["id"]
    display_name = profile_resp.get("display_name", "")
    email        = profile_resp.get("email", "")

    # create Django user with spotify_id as username
    user, _ = User.objects.get_or_create(username=spotify_id)

    # tokens saved serverside for future API calls
    SpotifyToken.objects.update_or_create(
        user=user,
        defaults={
            "spotify_user_id": spotify_id,
            "display_name":    display_name,
            "email":           email,
            "access_token":    access_token,
            "refresh_token":   refresh_token,
            "expires_at":      timezone.now() + timedelta(seconds=3600),
        }
    )

    # profile built with feature vector
    try:
        build_user_profile(user)
    except Exception as e:
        print(f"[callback] Profile build failed: {e}")

    # raw token not displayed in frontend for security
    return redirect(f"http://localhost:3000/dashboard?user_id={user.id}")

# API endpoint for frontend fetching
def spotify_profile(request):
    user_id = request.GET.get("user_id")
    token = _get_token_for_user_id(user_id) if user_id else request.GET.get("token")

    if not token:
        return JsonResponse({"error": "No valid session"}, status=401)

    response = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    return JsonResponse(response.json())


def spotify_top_tracks_with_snippets(request):
    user_id = request.GET.get("user_id")
    token = _get_token_for_user_id(user_id) if user_id else request.GET.get("token")
    time_range = request.GET.get("time_range", "long_term")

    if not token:
        return JsonResponse({"error": "No valid session"}, status=401)

    tracks = fetch_top_tracks(token, time_range)
    average_features = extract_avg_audio_features(tracks)

    tracks_with_previews = [{
        "spotify_track": t,
        "preview_url": get_itunes_preview(t["name"], t["artists"][0]["name"]),
    } for t in tracks]

    return JsonResponse({
        "tracks": tracks_with_previews,
        "average_features": average_features
    }, safe=False)

# similar endpoint for top artists
def spotify_top_artists(request):
    user_id = request.GET.get("user_id")
    token = _get_token_for_user_id(user_id) if user_id else request.GET.get("token")
    time_range = request.GET.get("time_range", "long_term")

    if not token:
        return JsonResponse({"error": "No valid session"}, status=401)

    return JsonResponse({"items": fetch_top_artists(token, time_range)}, safe=False)

# shared helper for audio feature extraction from audio_processing.py
def extract_features(request):
    from .audio_processing import extract_features_from_url
    url = request.GET.get("url")
    if not url:
        return JsonResponse({"error": "Missing preview URL"}, status=400)
    try:
        features = extract_features_from_url(url)
        return JsonResponse(features)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# endpoint for concert recommendations based on top artists
def concerts_recommendations(request):
    user_id = request.GET.get("user_id")
    token = _get_token_for_user_id(user_id) if user_id else request.GET.get("token")
    time_range = request.GET.get("time_range", "long_term")

    if not token:
        return JsonResponse({"error": "No valid session"}, status=401)

    artists = fetch_top_artists(token, time_range, limit=20)
    concerts = []

    for artist in artists:
        artist_name = artist["name"]
        tm_response = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params={
                "keyword": artist_name,
                "classificationName": "music",
                "countryCode": "IE",
                "size": 3,
                "apikey": TICKETMASTER_API_KEY
            }
        )
        events = tm_response.json().get("_embedded", {}).get("events", [])

        for event in events:
            venue = event["_embedded"]["venues"][0]
            date = event["dates"]["start"].get("localDate")

            concert_obj, _ = Concert.objects.get_or_create(
                spotify_artist_id=artist["id"],
                artist_name=artist_name,
                venue=venue["name"],
                date=date
            )
            concerts.append({
                "id": concert_obj.id,
                "artist": artist_name,
                "event_name": event["name"],
                "venue": venue["name"],
                "city": venue["city"]["name"],
                "date": date,
                "url": event.get("url")
            })

    return JsonResponse({"time_range": time_range, "concerts": concerts})

# endpoint for fetching user persona/profile info
def user_persona(request):
    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id required"}, status=400)
    try:
        user = User.objects.get(id=user_id)
        profile = UserProfile.objects.get(user=user)
        return JsonResponse({
            "persona_type": profile.persona_type or "",
            "persona_tags": profile.persona_tags or [],
            "cluster_id":   profile.cluster_id,
        })
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "Profile not found"}, status=404)

# endpoint for finding similar users based on persona    
def similar_users(request):
    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id required"}, status=400)

    try:
        user = User.objects.get(id=user_id)
        profile = UserProfile.objects.get(user=user)
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return JsonResponse({"error": "Profile not found"}, status=404)

    if profile.cluster_id is None:
        return JsonResponse({"error": "User not yet classified"}, status=400)

    # all users in given cluster are fetched, excluding self and synthetic profiles
    same_cluster = UserProfile.objects.filter(
        cluster_id=profile.cluster_id
    ).exclude(
        user=user
    ).exclude(
        user__username__startswith="synthetic_"
    ).exclude(
        feature_vector=[]
    )

    if not same_cluster.exists():
        return JsonResponse({"matches": [], "persona_type": profile.persona_type})

    # KNN similarity score to calculate percentage match - euclidean distance of the feature vectors is used along with shared genres and artists as additional context
    import numpy as np
    import joblib, os

    model_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'ml', 'saved_models'
    )
    scaler = joblib.load(os.path.join(model_dir, 'scaler.pkl'))

    user_vec = np.array(profile.feature_vector).reshape(1, -1)
    user_vec_scaled = scaler.transform(user_vec)

    matches = []
    for other in same_cluster:
        other_vec = np.array(other.feature_vector).reshape(1, -1)
        other_vec_scaled = scaler.transform(other_vec)

        # euclidean distance — lower = more similar
        distance = float(np.linalg.norm(user_vec_scaled - other_vec_scaled))

        # shared genres using raw spotify genres
        # preserves distinction between e.g. bollywood and pop
        user_genres  = set(g.lower().strip() for g in (profile.top_genres or []))
        other_genres = set(g.lower().strip() for g in (other.top_genres or []))
        shared_genres = list(user_genres & other_genres)

        # shared artists
        user_artist_lookup = {
            aid: {"name": name, "image": img}
            for aid, name, img in zip(
                profile.top_artist_ids or [],
                profile.top_artist_names or [],
                profile.top_artist_images or [],
            )
        }

        user_artists  = set(profile.top_artist_ids or [])
        other_artists = set(other.top_artist_ids or [])
        shared_ids    = user_artists & other_artists

        shared_artists = [
            {
                "id":    aid,
                "name":  user_artist_lookup.get(aid, {}).get("name", "Unknown"),
                "image": user_artist_lookup.get(aid, {}).get("image", ""),
            }
            for aid in shared_ids
        ]
        shared_artist_count = len(shared_ids)

        # match percentage — convert distance to 0-100 score
        # clamp distance to a sensible range then invert
        match_pct = max(0, min(100, round(100 - (distance / 8) * 100)))

        matches.append({
            "user_id":            other.user.id,
            "display_name":       other.user.username,
            "persona_type":       other.persona_type or "",
            "persona_tags":       other.persona_tags or [],
            "shared_genres":      shared_genres,
            "shared_artists":     shared_artists,
            "shared_artist_count": shared_artist_count,
            "match_pct":          match_pct,
            "distance":           distance,
        })

    # sort by distance ascending — closest first
    matches.sort(key=lambda x: x["distance"])

    # return top 10
    return JsonResponse({
        "my_persona":  profile.persona_type,
        "cluster_id":  profile.cluster_id,
        "matches":     matches[:10],
    })