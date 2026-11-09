import logging
import os
import urllib.parse
from html.parser import HTMLParser
from typing import Any

import requests

logger = logging.getLogger(__name__)

DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"


class _DuckDuckGoHTMLParser(HTMLParser):
    """Extract DuckDuckGo result links and snippets without relying on tag types."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self.snippets: list[str] = []
        self._link: dict[str, Any] | None = None
        self._link_depth = 0
        self._snippet_parts: list[str] | None = None
        self._snippet_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "a" and "result__a" in classes:
            self._link = {
                "url": attributes.get("href") or "",
                "title_parts": [],
            }
            self._link_depth = 1
        elif self._link is not None:
            self._link_depth += 1

        if "result__snippet" in classes and self._snippet_parts is None:
            self._snippet_parts = []
            self._snippet_depth = 1
        elif self._snippet_parts is not None:
            self._snippet_depth += 1

    def handle_data(self, data: str) -> None:
        if self._link is not None:
            self._link["title_parts"].append(data)
        if self._snippet_parts is not None:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._link is not None:
            self._link_depth -= 1
            if tag == "a" and self._link_depth <= 0:
                title = " ".join(" ".join(self._link["title_parts"]).split())
                self.links.append({"url": self._link["url"], "title": title})
                self._link = None
                self._link_depth = 0

        if self._snippet_parts is not None:
            self._snippet_depth -= 1
            if self._snippet_depth <= 0:
                snippet = " ".join(" ".join(self._snippet_parts).split())
                self.snippets.append(snippet)
                self._snippet_parts = None
                self._snippet_depth = 0


class SearchProvider:
    """Search provider supporting Tavily, Brave, SerpAPI and DuckDuckGo HTML."""

    def __init__(self) -> None:
        self.provider = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
        self.serpapi_key = os.getenv("SERPAPI_API_KEY", "")

    @staticmethod
    def _normalize_result(title: str, url: str, snippet: str) -> dict[str, str] | None:
        title = " ".join((title or "").split())
        snippet = " ".join((snippet or "").split())
        url = (url or "").strip()
        if not url:
            return None

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return {"title": title, "url": url, "snippet": snippet}

    def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        if not query.strip():
            return []

        if self.provider == "tavily" or (self.tavily_api_key and self.provider == "auto"):
            return self._search_tavily(query, max_results)
        if self.provider == "brave" or (self.brave_api_key and self.provider == "auto"):
            return self._search_brave(query, max_results)
        if self.provider == "serpapi" or (self.serpapi_key and self.provider == "auto"):
            return self._search_serpapi(query, max_results)
        return self._search_duckduckgo_html(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[dict[str, str]]:
        if not self.tavily_api_key:
            logger.warning("Tavily selected but TAVILY_API_KEY is not configured.")
            return self._search_duckduckgo_html(query, max_results)
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={"query": query, "max_results": max_results},
                headers={"Authorization": f"Bearer {self.tavily_api_key}"},
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            return [
                result
                for item in data.get("results", [])
                if (result := self._normalize_result(
                    item.get("title", ""), item.get("url", ""), item.get("content", "")
                ))
            ][:max_results]
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            logger.warning("Tavily search failed; falling back to DuckDuckGo: %s", exc)
            return self._search_duckduckgo_html(query, max_results)

    def _search_brave(self, query: str, max_results: int) -> list[dict[str, str]]:
        if not self.brave_api_key:
            logger.warning("Brave selected but BRAVE_SEARCH_API_KEY is not configured.")
            return self._search_duckduckgo_html(query, max_results)
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"Accept": "application/json", "X-Subscription-Token": self.brave_api_key},
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("web", {}).get("results", [])
            return [
                result
                for item in items
                if (result := self._normalize_result(
                    item.get("title", ""), item.get("url", ""), item.get("description", "")
                ))
            ][:max_results]
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            logger.warning("Brave search failed; falling back to DuckDuckGo: %s", exc)
            return self._search_duckduckgo_html(query, max_results)

    def _search_serpapi(self, query: str, max_results: int) -> list[dict[str, str]]:
        if not self.serpapi_key:
            logger.warning("SerpAPI selected but SERPAPI_API_KEY is not configured.")
            return self._search_duckduckgo_html(query, max_results)
        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self.serpapi_key, "engine": "google", "num": max_results},
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            return [
                result
                for item in data.get("organic_results", [])[:max_results]
                if (result := self._normalize_result(
                    item.get("title", ""), item.get("link", ""), item.get("snippet", "")
                ))
            ][:max_results]
        except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
            logger.warning("SerpAPI search failed; falling back to DuckDuckGo: %s", exc)
            return self._search_duckduckgo_html(query, max_results)

    @staticmethod
    def _decode_duckduckgo_url(raw_url: str) -> str:
        raw_url = urllib.parse.urljoin(DUCKDUCKGO_URL, raw_url.strip())
        parsed = urllib.parse.urlparse(raw_url)
        if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
            target = urllib.parse.parse_qs(parsed.query).get("uddg", [])
            if target:
                raw_url = urllib.parse.unquote(target[0])
        return raw_url

    def _search_duckduckgo_html(self, query: str, max_results: int) -> list[dict[str, str]]:
        try:
            response = requests.get(
                DUCKDUCKGO_URL,
                params={"q": query},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                },
                timeout=15,
            )
            response.raise_for_status()

            parser = _DuckDuckGoHTMLParser()
            parser.feed(response.text)
            parser.close()

            results = []
            for index, link in enumerate(parser.links):
                url = self._decode_duckduckgo_url(link["url"])
                snippet = parser.snippets[index] if index < len(parser.snippets) else ""
                result = self._normalize_result(link["title"], url, snippet)
                if result:
                    results.append(result)
                if len(results) >= max_results:
                    break

            if not results:
                logger.warning(
                    "DuckDuckGo returned HTTP %s but no parseable results for query %r (response length: %s).",
                    response.status_code,
                    query,
                    len(response.text),
                )
            else:
                logger.info("DuckDuckGo returned %s results for query %r.", len(results), query)
            return results
        except (requests.RequestException, ValueError) as exc:
            logger.exception("DuckDuckGo search failed for query %r: %s", query, exc)
            return []


default_search_provider = SearchProvider()
