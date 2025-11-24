# ui/views.py
from django.shortcuts import render

def chat_ui(request):
    return render(request, "chat.html")
