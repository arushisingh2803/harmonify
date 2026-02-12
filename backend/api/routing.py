from django.urls import re_path
from .consumers import ConcertChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/concerts/(?P<concert_id>[^/]+)/$", ConcertChatConsumer.as_asgi()),
]
