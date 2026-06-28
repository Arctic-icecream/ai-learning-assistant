import socket
import unittest
from unittest.mock import patch

import httpx

from backend.app.web_parser import (
    WebImportError,
    extract_html_text,
    fetch_web_page,
    validate_public_url,
)


PUBLIC_ADDRESS = "93.184.216.34"


def public_dns_result(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_ADDRESS, 443))]


class WebParserTests(unittest.TestCase):
    def test_extracts_content_and_removes_page_chrome(self) -> None:
        html = """
        <html>
          <head><title>Routing Notes</title><script>ignore()</script></head>
          <body>
            <nav>Site navigation</nav>
            <main>
              <h1>AODV</h1>
              <p>AODV discovers routes only when needed.</p>
              <ul><li>Reactive protocol</li></ul>
              <table>
                <tr><th>Protocol</th><th>Type</th></tr>
                <tr><td>AODV</td><td>Reactive</td></tr>
              </table>
            </main>
            <footer>Copyright text</footer>
          </body>
        </html>
        """

        title, text = extract_html_text(html)

        self.assertEqual(title, "Routing Notes")
        self.assertIn("AODV discovers routes only when needed.", text)
        self.assertIn("Protocol\tType", text)
        self.assertNotIn("Site navigation", text)
        self.assertNotIn("Copyright text", text)
        self.assertNotIn("ignore()", text)

    def test_blocks_local_and_non_http_urls(self) -> None:
        with self.assertRaises(WebImportError):
            validate_public_url("http://127.0.0.1/admin")
        with self.assertRaises(WebImportError):
            validate_public_url("file:///etc/passwd")
        with self.assertRaises(WebImportError):
            validate_public_url("https://user:secret@example.com/private")

    @patch("backend.app.web_parser.socket.getaddrinfo", side_effect=public_dns_result)
    def test_fetches_an_html_page(self, _: object) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="<html><head><title>Study Page</title></head><body><main><p>Useful material.</p></main></body></html>",
                request=request,
            )

        page = fetch_web_page(
            "https://example.com/notes",
            transport=httpx.MockTransport(handler),
        )

        self.assertEqual(page.title, "Study Page")
        self.assertIn("Useful material.", page.html)
        self.assertEqual(page.url, "https://example.com/notes")

    def test_revalidates_redirect_destinations(self) -> None:
        def dns_result(host: str, *args: object, **kwargs: object) -> list[tuple[object, ...]]:
            address = "127.0.0.1" if host == "127.0.0.1" else PUBLIC_ADDRESS
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 80))]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                302,
                headers={"location": "http://127.0.0.1/private"},
                request=request,
            )

        with patch("backend.app.web_parser.socket.getaddrinfo", side_effect=dns_result):
            with self.assertRaises(WebImportError):
                fetch_web_page(
                    "http://example.com/start",
                    transport=httpx.MockTransport(handler),
                )


if __name__ == "__main__":
    unittest.main()
