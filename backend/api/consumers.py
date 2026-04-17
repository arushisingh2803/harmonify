from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json

class ConcertChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.concert_id = self.scope["url_route"]["kwargs"]["concert_id"]
        self.room_group_name = f"chat_{self.concert_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        history = await self.get_message_history()
        for msg in history:
            await self.send(text_data=json.dumps({
                "message":  msg["content"],
                "username": msg["username"],
                "timestamp": msg["timestamp"],
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data     = json.loads(text_data)
        message  = data.get("message")
        username = data.get("username", "Guest")
        user_id  = data.get("user_id")

        # persist message to database
        await self.save_message(user_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type":     "chat_message",
                "message":  message,
                "username": username,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message":  event["message"],
            "username": event["username"],
        }))

    @database_sync_to_async
    def get_message_history(self):
        from core.models import ChatRoom, Concert, Message
        try:
            concert = Concert.objects.filter(
                ticketmaster_id=self.concert_id
            ).first()
            if not concert:
                return []
            room, _ = ChatRoom.objects.get_or_create(concert=concert)
            messages = Message.objects.filter(room=room).order_by("timestamp")[:100]
            return [
                {
                    "content":   m.content,
                    "username":  m.user.username,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in messages
            ]
        except Exception as e:
            print(f"[chat] History load error: {e}")
            return []

    @database_sync_to_async
    def save_message(self, user_id, content):
        from core.models import ChatRoom, Concert, Message
        from django.contrib.auth.models import User
        try:
            concert = Concert.objects.filter(
                ticketmaster_id=self.concert_id
            ).first()
            if not concert:
                return
            room, _ = ChatRoom.objects.get_or_create(concert=concert)
            user     = User.objects.get(id=user_id)
            Message.objects.create(room=room, user=user, content=content)
        except Exception as e:
            print(f"[chat] Message save error: {e}")