import re
import html
from html.parser import HTMLParser

class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._pieces = []
        self._ignore_stack = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style", "noscript", "svg"):
            self._ignore_stack.append(tag.lower())

    def handle_endtag(self, tag):
        if self._ignore_stack and self._ignore_stack[-1] == tag.lower():
            self._ignore_stack.pop()
        elif tag.lower() in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self._pieces.append("\n")

    def handle_data(self, data):
        if not self._ignore_stack:
            text = data.strip()
            if text:
                self._pieces.append(text + " ")

    def get_text(self) -> str:
        raw = "".join(self._pieces)
        # Unescape HTML entities
        raw = html.unescape(raw)
        # Collapse multiple empty lines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.split("\n")]
        return "\n".join(l for l in lines if l)

def extract_clean_text_from_html(html_content: str, max_chars: int = 12000) -> str:
    parser = SimpleHTMLTextExtractor()
    try:
        parser.feed(html_content)
        text = parser.get_text()
    except Exception:
        # Fallback regex strip
        text = re.sub(r"<[^>]+>", " ", html_content)
        text = html.unescape(text)

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [Truncated after {max_chars} characters]"
    return text

