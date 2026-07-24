"""Regression tests for the bundled atlassian-vpath Confluence converter.

The skill ships executable Markdown->Confluence-storage logic under
.claude/skills/; the main coverage gate measures only src/, so these tests
pin the pure converter here. The network/credential layer (confluence_api)
needs a live Confluence and is not exercised in the gate.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = REPO_ROOT / ".claude" / "skills" / "atlassian-vpath" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import confluence_md as md  # noqa: E402


def test_heading_becomes_h_tag() -> None:
    assert md.convert_markdown("# Title") == "<h1>Title</h1>"
    assert md.convert_markdown("### Three") == "<h3>Three</h3>"


def test_heading_in_blockquote_is_bold_paragraph() -> None:
    # Confluence ignores <hN> inside <blockquote>; the converter must downgrade.
    out = md.convert_markdown("> ### Inside")
    assert "<blockquote>" in out
    assert "<h3>" not in out
    assert "<strong>Inside</strong>" in out


def test_fenced_code_becomes_code_macro() -> None:
    out = md.convert_markdown("```python\nx = 1\n```")
    assert 'ac:name="code"' in out
    assert "<![CDATA[x = 1]]>" in out


def test_table_renders_to_xhtml_table() -> None:
    out = md.convert_markdown("| A | B |\n|---|---|\n| 1 | 2 |")
    assert "<table>" in out
    assert "<th>A</th>" in out and "<th>B</th>" in out
    assert "<td>1</td>" in out and "<td>2</td>" in out


def test_inline_formatting_and_escaping() -> None:
    assert "<strong>bold</strong>" in md.convert_markdown("**bold**")
    assert "<code>x</code>" in md.convert_markdown("`x`")
    # raw angle brackets are escaped
    assert "&lt;tag&gt;" in md.convert_markdown("a <tag> b")


def test_split_title_body_takes_first_h1() -> None:
    title, body = md.split_title_body("# The Title\n\nbody text")
    assert title == "The Title"
    assert "body text" in body
    assert "# The Title" not in body


def test_md_file_to_page_falls_back_to_given_title() -> None:
    title, storage = md.md_file_to_page("no heading here", "fallback")
    assert title == "fallback"
    assert storage == "<p>no heading here</p>"


def test_with_toc_only_for_long_pages() -> None:
    short = "<h2>One</h2>"
    assert md.with_toc(short) == short  # below min_headings
    long_doc = "<h2>1</h2><h2>2</h2><h3>3</h3><h2>4</h2>"
    assert 'ac:name="toc"' in md.with_toc(long_doc)


def test_rewrite_internal_links_to_page_links() -> None:
    out = md.rewrite_internal_links(
        '<a href="02_intro.md">Intro</a>', {"02_intro.md": "Intro Page"}
    )
    assert 'ri:content-title="Intro Page"' in out
    assert "<ac:link>" in out
    # unknown targets are left untouched
    unchanged = '<a href="x.md">x</a>'
    assert md.rewrite_internal_links(unchanged, {}) == unchanged
