import os
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

class SearchProvider:
    """Configurable Search Provider interface supporting Tavily, Brave, SerpAPI, or DuckDuckGo HTML fallback."""
    def __init__(self):
        self.provider = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
        self.serpapi_key = os.getenv("SERPAPI_API_KEY", "")

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        # 1. Tavily if configured
        if self.provider == "tavily" or (self.tavily_api_key and self.provider == "auto"):
            return self._search_tavily(query, max_results)
        
        # 2. Brave if configured
        if self.provider == "brave" or (self.brave_api_key and self.provider == "auto"):
            return self._search_brave(query, max_results)

        # 3. SerpAPI if configured
        if self.serpapi_key:
            return self._search_serpapi(query, max_results)

        # 4. Fallback: DuckDuckGo HTML / Instant Answers
        return self._search_duckduckgo_html(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.tavily_api_key:
            return self._search_duckduckgo_html(query, max_results)
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"query": query, "max_results": max_results, "include_snippets": True},
                headers={"Authorization": f"Bearer {self.tavily_api_key}"},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")
                })
            return results
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}. Falling back to default search.")
            return self._search_duckduckgo_html(query, max_results)

    def _search_brave(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        if not self.brave_api_key:
            return self._search_duckduckgo_html(query, max_results)
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"Accept": "application/json", "X-Subscription-Token": self.brave_api_key},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", "")
                })
            return results
        except Exception as e:
            logger.warning(f"Brave search failed: {e}. Falling back to default search.")
            return self._search_duckduckgo_html(query, max_results)

    def _search_serpapi(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self.serpapi_key, "engine": "google", "num": max_results},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("organic_results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
            return results
        except Exception as e:
            logger.warning(f"SerpAPI failed: {e}. Falling back to default search.")
            return self._search_duckduckgo_html(query, max_results)

    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Zero-dependency HTML search fallback for DuckDuckGo."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            resp = requests.get(url, headers=headers, timeout=12)
            resp.raise_for_status()

            # Parse results from HTML with regex
            import re
            body = resp.text
            results = []
            # DuckDuckGo HTML results have class 'result__snippet' and 'result__url'
            pattern = re.compile(
                r'<a[^>]+class="result__url"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
                re.DOTALL
            )
            for match in pattern.finditer(body):
                res_url = match.group("url").strip()
                # Duckduckgo uddg redirects
                if "uddg=" in res_url:
                    parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(res_url).query)
                    if "uddg" in parsed_qs:
                        res_url = parsed_qs["uddg"][0]

                raw_title = re.sub(r"<[^>]+>", "", match.group("title")).strip()
                raw_snippet = re.sub(r"<[^>]+>", "", match.group("snippet")).strip()

                if res_url and (raw_title or raw_snippet):
                    results.append({
                        "title": raw_title,
                        "url": res_url,
                        "snippet": raw_snippet
                    })
                if len(results) >= max_results:
                    break

            if not results:
                # Broader anchor match fallback
                anchor_pattern = re.compile(
                    r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<text>.*?)</a>',
                    re.DOTALL
                )
                for match in anchor_pattern.finditer(body):
                    u = match.group("url")
                    if "uddg=" in u:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
                        if "uddg" in parsed_qs:
                            u = parsed_qs["uddg"][0]
                    txt = re.sub(r"<[^>]+>", "", match.group("text")).strip()
                    results.append({"title": txt[:60], "url": u, "snippet": txt})
                    if len(results) >= max_results:
                        break

            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search fallback failed: {e}")
            return []

default_search_provider = SearchProvider()

