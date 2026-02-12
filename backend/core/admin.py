from django.contrib import admin
from .models import Concert, ChatRoom, Message

admin.site.register(Concert)
admin.site.register(ChatRoom)
admin.site.register(Message)

