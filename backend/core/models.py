from django.db import models
from django.contrib.auth.models import User

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

