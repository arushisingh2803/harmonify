# this file defines the URL routing for the Django backend
from django.contrib import admin
from django.urls import path, include
from api import views

urlpatterns = [
    path("callback/", views.spotify_callback),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path("login/", views.spotify_login),
    path("profile/", views.spotify_profile),
    path('top-tracks-with-snippets/', views.spotify_top_tracks_with_snippets),
    path("top-artists/", views.spotify_top_artists),
    path("extract-features/", views.extract_features),
    path("concerts-recommendations/", views.concerts_recommendations),
    path('user-persona/', views.user_persona),
    path('similar-users/', views.similar_users),
    path("currently-playing/", views.currently_playing),
]