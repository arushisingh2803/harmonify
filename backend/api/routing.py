from . import consumers
from django.urls import path

websocket_urlpatterns = [
    path("ws/concerts/<str:concert_id>/", consumers.ConcertChatConsumer.as_asgi()),
]