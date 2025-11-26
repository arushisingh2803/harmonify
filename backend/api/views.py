import base64
import requests
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework import viewsets
from .models import Task
from .serializers import TaskSerializer
from django.conf import settings

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

CLIENT_ID = settings.SPOTIFY_CLIENT_ID
CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI
SCOPES = "user-read-private user-read-email user-top-read"

def spotify_login(request):
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
    )
    return HttpResponseRedirect(auth_url)

def spotify_callback(request):
    code = request.GET.get("code")
    print("\nDEBUG: Code received from Spotify:", code)

    if code is None:
        return JsonResponse({"error": "No code returned", "details": dict(request.GET)}, status=400)

    token_url = "https://accounts.spotify.com/api/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={
            "Authorization": f"Basic {b64_auth}"
        }
    )

    data = response.json()
    print("Spotify token response:", data)

    access_token = data.get("access_token")

    # show spotify error if no access token found
    if not access_token:
        return JsonResponse({
            "error": "Failed to get access token",
            "spotify_response": data
        }, status=400)

    return HttpResponseRedirect(
        f"http://localhost:3000/dashboard?token={access_token}"
    )


def spotify_profile(request):
    token = request.GET.get("token")

    response = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    return JsonResponse(response.json())

def spotify_top_tracks_with_snippets(request):
    token = request.GET.get("token")

    if not token:
        return JsonResponse({"error": "Token is required"}, status=400)

    sp_response = requests.get(
        "https://api.spotify.com/v1/me/top/tracks?limit=10&time_range=long_term",
        headers={"Authorization": f"Bearer {token}"}
    )

    sp_data = sp_response.json()

    if "error" in sp_data:
        return JsonResponse({"error": "Spotify error", "details": sp_data}, status=400)

    tracks = sp_data.get("items", [])

    tracks_with_snippets = []

    for t in tracks:
        track_name = t["name"]
        artist_name = t["artists"][0]["name"]

        preview_url = get_itunes_preview(track_name, artist_name)

        tracks_with_snippets.append({
            "spotify_track": t,
            "preview_url": preview_url
        })

    return JsonResponse(tracks_with_snippets, safe=False)


def spotify_top_artists(request):
    token = request.GET.get("token")

    if not token:
        return JsonResponse({"error": "Token is required"}, status=400)

    response = requests.get(
        "https://api.spotify.com/v1/me/top/artists?limit=10&time_range=long_term",
        headers={"Authorization": f"Bearer {token}"}
)


    return JsonResponse(response.json(), safe=False)

def get_itunes_preview(track_name, artist_name):
    query = f"{track_name} {artist_name}".replace(" ", "+")
    url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"

    try:
        response = requests.get(url).json()

        if response.get("resultCount", 0) > 0:
            return response["results"][0].get("previewUrl")  # may be None

        return None
    except:
        return None
