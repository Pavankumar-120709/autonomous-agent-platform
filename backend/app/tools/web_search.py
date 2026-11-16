import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import httpx
from bs4 import BeautifulSoup
from .base import BaseTool

logger = logging.getLogger("agent.tools.web_search")


class SearchItem(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query terms to find information on the web.")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of search results to retrieve (1-10).")

    @field_validator("query")
    def validate_query(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Search query cannot be empty")
        if len(clean) > 300:
            clean = clean[:300]
        return clean


class WebSearchResult(BaseModel):
    query: str
    total_found: int
    results: List[SearchItem]


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the live web for accurate, up-to-date information, news, documentation, or facts. "
        "Returns a structured list of results with title, URL, and a text snippet."
    )
    args_schema = WebSearchInput
    timeout_seconds = 15.0

    async def _run(self, query: str, max_results: int = 5) -> WebSearchResult:
        # First attempt: use duckduckgo_search package
        results = await self._search_via_ddg(query, max_results)
        if not results:
            # Fallback attempt: HTTP html search
            results = await self._search_via_html_fallback(query, max_results)

        if not results:
            return WebSearchResult(
                query=query,
                total_found=0,
                results=[]
            )

        return WebSearchResult(
            query=query,
            total_found=len(results),
            results=results
        )

    async def _search_via_ddg(self, query: str, max_results: int) -> List[SearchItem]:
        def _sync_ddg():
            try:
                from duckduckgo_search import DDGS
                with DDGS(timeout=10) as ddgs:
                    raw_results = list(ddgs.text(query, max_results=max_results))
                    items = []
                    for r in raw_results:
                        url = r.get("href") or r.get("link") or ""
                        title = r.get("title") or "Untitled"
                        snippet = r.get("body") or r.get("snippet") or ""
                        if url:
                            items.append(SearchItem(title=title.strip(), url=url.strip(), snippet=snippet.strip()))
                    return items
            except Exception as e:
                logger.warning(f"DDGS query failed: {e}. Attempting fallback.")
                return []

        return await asyncio.to_thread(_sync_ddg)

    async def _search_via_html_fallback(self, query: str, max_results: int) -> List[SearchItem]:
        """Direct HTTP search fallback to html duckduckgo endpoint."""
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        data = {"q": query}

        try:
            async with httpx.AsyncClient(headers=headers, timeout=8.0, follow_redirects=True) as client:
                resp = await client.post(url, data=data)
                if resp.status_code != 200:
                    logger.warning(f"HTML search fallback returned status {resp.status_code}")
                    return []

                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for result in soup.find_all("div", class_="result"):
                    if len(results) >= max_results:
                        break
                    title_elem = result.find("a", class_="result__a")
                    snippet_elem = result.find("a", class_="result__snippet")
                    if title_elem:
                        href = title_elem.get("href", "")
                        # Unpack DDG redirect url if needed
                        if "uddg=" in href:
                            import urllib.parse
                            parsed_href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            actual_url = parsed_href.get("uddg", [href])[0]
                        else:
                            actual_url = href

                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        if actual_url.startswith("http"):
                            results.append(SearchItem(title=title, url=actual_url, snippet=snippet))
                return results
        except Exception as e:
            logger.error(f"HTML search fallback error: {e}")
            return []
