import os
from typing import Optional

import requests
from django.conf import settings


class WebSearchTool:
    """
    Simple web search wrapper for project-related information.

    This is intentionally minimal and pluggable:
    - It expects an HTTP endpoint that can take a query string and return a JSON summary.
    - You can back this endpoint with any search provider (SerpAPI, internal RAG API, etc.).

    Configuration:
    - Set WEB_SEARCH_API_URL in Django settings or environment.
      For example, an endpoint that accepts POST {"query": "..."} and returns:
        {"summary": "some text"}
    """

    def __init__(self) -> None:
        self.api_url: Optional[str] = getattr(settings, "WEB_SEARCH_API_URL", None) or os.getenv(
            "WEB_SEARCH_API_URL"
        )

    def search_project_info(self, project_name: str, city: Optional[str] = None) -> Optional[str]:
        """
        Search the web for additional info about a project.
        Returns a short summary string, or None if search not configured or fails.
        """

        if not self.api_url:
            # Web search not configured – graceful no-op
            return None

        query_parts = [project_name]
        if city:
            query_parts.append(city)
        query = " ".join(query_parts)

        try:
            resp = requests.post(
                self.api_url,
                json={"query": query},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            summary = data.get("summary")
            if isinstance(summary, str) and summary.strip():
                return summary.strip()
        except Exception:
            # For robustness, swallow errors and return None
            return None

        return None


web_search_tool = WebSearchTool()
