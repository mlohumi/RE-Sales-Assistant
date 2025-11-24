import requests
from typing import List, Dict
from django.conf import settings


class LLMClient:
    """
    Wrapper for calling GPT-4o (or Claude, Mistral etc.) via OpenRouter.
    Centralizes authentication and error handling.
    """

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY missing — add it to .env")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        messages: [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            ...
        ]
        Returns the assistant's reply (string).
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "silverland.ai",  # optional but recommended
            "X-Title": "SilverLand Property Assistant",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
        }

        response = requests.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]
