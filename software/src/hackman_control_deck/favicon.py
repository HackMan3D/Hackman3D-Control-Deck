from __future__ import annotations

from html.parser import HTMLParser
import struct
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (compatible; HackMan3D-Control-Deck/1.4)"
MAX_ICON_BYTES = 1_000_000
MAX_PAGE_BYTES = 750_000


class _IconLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.page_images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "meta":
            values = {key.lower(): value or "" for key, value in attrs}
            kind = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if kind in {"og:image", "twitter:image"} and content:
                self.page_images.append(content)
            return
        if tag.lower() != "link":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        relation = values.get("rel", "").lower().split()
        href = values.get("href", "").strip()
        if href and any(item in {"icon", "shortcut", "apple-touch-icon"} for item in relation):
            self.links.append(href)


def normalized_website_url(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    return candidate


def favicon_candidates(value: str, page_html: bytes = b"") -> list[str]:
    website = normalized_website_url(value)
    if not website:
        return []
    parsed = urlparse(website)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = []
    page_images: list[str] = []
    if page_html:
        parser = _IconLinkParser()
        try:
            parser.feed(page_html.decode("utf-8", errors="ignore"))
        except ValueError:
            pass
        candidates.extend(urljoin(website, link) for link in parser.links)
        page_images.extend(urljoin(website, link) for link in parser.page_images)
    candidates.extend(
        (
            "https://www.google.com/s2/favicons?"
            f"domain_url={quote(origin, safe='')}&sz=256",
            f"{origin}/apple-touch-icon.png",
            f"{origin}/favicon.ico",
        )
    )
    candidates.extend(page_images)
    return list(dict.fromkeys(candidates))


def _download(url: str, limit: int) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=4) as response:  # noqa: S310
        content_type = response.headers.get_content_type()
        if limit == MAX_ICON_BYTES and not (
            content_type.startswith("image/") or content_type == "application/octet-stream"
        ):
            return b""
        return response.read(limit + 1)[:limit]


def download_favicon(value: str) -> bytes:
    website = normalized_website_url(value)
    if not website:
        return b""
    try:
        page_html = _download(website, MAX_PAGE_BYTES)
    except (OSError, ValueError):
        page_html = b""
    best_payload = b""
    best_score = 0
    for icon_url in favicon_candidates(website, page_html)[:10]:
        try:
            payload = _download(icon_url, MAX_ICON_BYTES)
        except (OSError, ValueError):
            continue
        width, height = _image_dimensions(payload)
        if width <= 0 or height <= 0:
            continue
        aspect = max(width, height) / min(width, height)
        if aspect > 1.4:
            continue
        score = min(width, height)
        if score > best_score:
            best_payload = payload
            best_score = score
    return best_payload


def _image_dimensions(payload: bytes) -> tuple[int, int]:
    if payload.startswith(b"\x89PNG\r\n\x1a\n") and len(payload) >= 24:
        return struct.unpack(">II", payload[16:24])
    if payload.startswith((b"GIF87a", b"GIF89a")) and len(payload) >= 10:
        return struct.unpack("<HH", payload[6:10])
    if payload.startswith(b"\x00\x00\x01\x00") and len(payload) >= 8:
        width = payload[6] or 256
        height = payload[7] or 256
        return width, height
    if payload.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 9 < len(payload):
            if payload[offset] != 0xFF:
                offset += 1
                continue
            marker = payload[offset + 1]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7}:
                return struct.unpack(">HH", payload[offset + 5 : offset + 9])[::-1]
            if offset + 4 > len(payload):
                break
            length = struct.unpack(">H", payload[offset + 2 : offset + 4])[0]
            offset += max(2, length + 2)
    return 0, 0
