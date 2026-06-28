from dataclasses import dataclass
import ipaddress
from pathlib import Path
import socket
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import httpx


MAX_WEB_PAGE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
REMOVED_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "nav",
    "footer",
    "header",
    "form",
    "aside",
)


class WebImportError(ValueError):
    pass


@dataclass(frozen=True)
class WebPage:
    url: str
    title: str
    html: str


def validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise WebImportError("Only http:// and https:// URLs are supported")
    if not parsed.hostname:
        raise WebImportError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise WebImportError("URLs containing credentials are not supported")

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as error:
        raise WebImportError("Could not resolve the URL hostname") from error

    if not addresses:
        raise WebImportError("URL hostname did not resolve to an address")

    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise WebImportError("Private, local, and reserved network addresses are blocked")


def extract_html_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else "Web page"

    for tag in soup.find_all(REMOVED_TAGS):
        tag.decompose()

    container = soup.find("main") or soup.find("article") or soup.body or soup
    blocks = [title] if title else []
    content_tags = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "table")

    for tag in container.find_all(content_tags):
        if tag.name != "table" and tag.find_parent("table") is not None:
            continue

        if tag.name == "table":
            rows = []
            for row in tag.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(("th", "td"))]
                if any(cells):
                    rows.append("\t".join(cells))
            text = "\n".join(rows)
        else:
            text = tag.get_text(" ", strip=True)

        if text and (not blocks or text != blocks[-1]):
            blocks.append(text)

    return title, "\n\n".join(blocks)


def extract_html_file_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    _, text = extract_html_text(html)
    return text


def fetch_web_page(
    url: str, transport: httpx.BaseTransport | None = None
) -> WebPage:
    current_url = url.strip()
    headers = {"User-Agent": "AI-Learning-Assistant/1.0"}

    with httpx.Client(
        follow_redirects=False,
        timeout=15,
        headers=headers,
        transport=transport,
    ) as client:
        for redirect_count in range(MAX_REDIRECTS + 1):
            validate_public_url(current_url)

            try:
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise WebImportError("Redirect response did not include a location")
                        if redirect_count == MAX_REDIRECTS:
                            raise WebImportError("Web page exceeded the redirect limit")
                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                        raise WebImportError("URL did not return an HTML document")

                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_WEB_PAGE_BYTES:
                            raise WebImportError("Web page is larger than the 2 MB limit")

                    encoding = response.encoding or "utf-8"
                    html = bytes(content).decode(encoding, errors="replace")
                    title, _ = extract_html_text(html)
                    return WebPage(url=str(response.url), title=title, html=html)
            except httpx.HTTPStatusError as error:
                raise WebImportError(
                    f"Web page returned HTTP {error.response.status_code}"
                ) from error
            except httpx.RequestError as error:
                raise WebImportError("Could not download the web page") from error

    raise WebImportError("Could not download the web page")
