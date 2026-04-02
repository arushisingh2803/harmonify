# all the core API views for Harmonify are in this file
import base64
import requests
import numpy as np
import urllib.parse

from django.http import JsonResponse, HttpResponseRedirect
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

from rest_framework import viewsets
from api.models import Task 
from core.models import Concert, SpotifyToken
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
    return HttpResponseRedirect(
        f"http://localhost:3000/dashboard?user_id={user.id}"
    )

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
    token = request.GET.get("token")
    time_range = request.GET.get("time_range", "long_term")

    if not token:
        return JsonResponse({"error": "Token is required"}, status=400)

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