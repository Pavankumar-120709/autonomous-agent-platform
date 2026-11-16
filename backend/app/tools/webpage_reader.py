import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import httpx
from .base import BaseTool
from ..security.ssrf import validate_url_safe, SSRFValidationError
from ..security.sanitizer import extract_and_sanitize_html, wrap_untrusted_content

logger = logging.getLogger("agent.tools.webpage_reader")


class WebpageReaderInput(BaseModel):
    url: str = Field(..., description="The HTTP or HTTPS URL of the webpage to retrieve and extract.")
    max_chars: int = Field(default=8000, ge=500, le=25000, description="Maximum characters of text content to extract.")

    @field_validator("url")
    def validate_url(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("URL cannot be empty")
        # Validate SSRF immediately on input validation
        validate_url_safe(clean)
        return clean


class WebpageContent(BaseModel):
    url: str
    status_code: int
    content: str
    char_count: int
    truncated: bool


class SafeRedirectTransport(httpx.AsyncHTTPTransport):
    """
    Ensures that every redirect hop is strictly validated against SSRF rules.
    """
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        validate_url_safe(url_str)
        return await super().handle_async_request(request)


class WebpageReaderTool(BaseTool):
    name = "webpage_reader"
    description = (
        "Safely retrieve, clean, and extract readable text from a verified web URL. "
        "Enforces strict SSRF protection, strips scripts/styles, and safely sandboxes untrusted webpage content."
    )
    args_schema = WebpageReaderInput
    timeout_seconds = 15.0

    async def _run(self, url: str, max_chars: int = 8000) -> WebpageContent:
        # Re-verify SSRF at invocation
        validate_url_safe(url)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (AutonomousResearchAgent/1.0)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        }

        transport = SafeRedirectTransport(verify=True)
        try:
            async with httpx.AsyncClient(
                transport=transport,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=True,
                max_redirects=3,
            ) as client:
                response = await client.get(url)

                if response.status_code >= 400:
                    raise ValueError(f"HTTP request to '{url}' failed with status {response.status_code}")

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                raw_text = response.text

                if "text/html" in content_type or "<html" in raw_text[:200].lower():
                    sanitized = extract_and_sanitize_html(raw_text, max_length=max_chars)
                else:
                    # Plain text or json
                    sanitized = raw_text[:max_chars]

                truncated = len(sanitized) >= max_chars
                safe_wrapped = wrap_untrusted_content(sanitized, source=url)

                return WebpageContent(
                    url=str(response.url),
                    status_code=response.status_code,
                    content=safe_wrapped,
                    char_count=len(sanitized),
                    truncated=truncated,
                )

        except SSRFValidationError as e:
            logger.warning(f"SSRF blocked request to '{url}': {e}")
            raise
        except httpx.TimeoutException:
            raise TimeoutError(f"HTTP request to '{url}' timed out after {self.timeout_seconds}s")
        except Exception as e:
            logger.error(f"Error fetching webpage '{url}': {e}")
            raise
