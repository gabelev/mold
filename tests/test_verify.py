"""The verification gate: correctness rules the pipeline enforces."""

from __future__ import annotations

from mold.verify import audit_html

_OK_PAGE = """<!doctype html>
<html><head><title>t</title></head>
<body><h1>Headline</h1><p>copy</p>
<a href="https://suno.com/song/x">the track</a>
</body></html>"""


def test_clean_page_passes() -> None:
    errors, warnings = audit_html(_OK_PAGE)
    assert errors == []


def test_copyright_wall_blocks_rehosted_media() -> None:
    page = _OK_PAGE.replace("<p>copy</p>", '<audio src="https://x/y.mp3"></audio>')
    errors, _ = audit_html(page)
    assert any("copyright wall" in e for e in errors)


def test_no_raster_in_headlines() -> None:
    page = _OK_PAGE.replace("<h1>Headline</h1>", '<h1><img src="head.png"></h1>')
    errors, _ = audit_html(page)
    assert any("type stays in the DOM" in e for e in errors)


def test_missing_links_is_warning_not_failure() -> None:
    page = _OK_PAGE.replace('<a href="https://suno.com/song/x">the track</a>', "")
    errors, warnings = audit_html(page)
    assert errors == []
    assert any("external links" in w for w in warnings)
