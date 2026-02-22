from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ConcertConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.artist_name = self.scope["url_route"]["kwargs"]["artist"]

        safe_artist = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', self.artist_name.lower())

        self.room_group_name = f"concert_{safe_artist}"

        # Join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "user": data["user"],
                "message": data["message"],
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "user": event["user"],
            "message": event["message"],
        }))