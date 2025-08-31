from __future__ import annotations

from bs4 import BeautifulSoup

from aliexpress_scraper.parsers import detect_antibot, parse_product_id, parse_text


def test_parse_product_id_common_urls():
    assert parse_product_id("https://www.aliexpress.com/item/1005001234567890.html") == "1005001234567890"
    assert parse_product_id("/item/1005009999999999.html?spm=...#hash") == "1005009999999999"
    assert parse_product_id("https://a.aliexpress.com/_ABCDE") is None


def test_detect_antibot_keywords():
    html = """
    <html><body>
      <h1>Please verify you are human</h1>
      <p>Cloudflare</p>
    </body></html>
    """
    assert detect_antibot(html) is True


def test_parse_text_helper():
    soup = BeautifulSoup("<div><span class='x'> Hello <b>world</b> </span></div>", "html.parser")
    assert parse_text(soup, ".x") == "Hello world"
