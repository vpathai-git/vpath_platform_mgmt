"""Markdown -> Confluence storage (XHTML) converter. Standard library only.

Pure, side-effect-free rendering helpers used by the publish scripts:
  - convert_markdown(): headings, code fences, tables, blockquotes, lists, rules
  - split_title_body() / md_file_to_page(): take the first H1 as the page title
  - rewrite_internal_links() / with_toc(): page-tree publishing helpers

No network, no credentials — see confluence_api.py for the REST client.
"""

from __future__ import annotations

import html
import re

_TABLE_SEP_CHARS = set("|-: \t")


def _inline(text: str) -> str:
    s = html.escape(text, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_table_separator(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and set(s) <= _TABLE_SEP_CHARS


def _code_macro(code: str, lang: str = "text") -> str:
    safe = code.replace("]]>", "]]]]><![CDATA[>")
    lang = re.sub(r"[^a-zA-Z0-9_+#-]", "", lang) or "text"
    return (
        '<ac:structured-macro ac:name="code">'
        f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
        f"<ac:plain-text-body><![CDATA[{safe}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
    )


def _render_table(header: list[str], rows: list[list[str]]) -> str:
    width = max([len(header)] + [len(r) for r in rows] or [0])

    def pad(cells: list[str]) -> list[str]:
        return cells + [""] * (width - len(cells))

    head = "".join(f"<th>{_inline(c)}</th>" for c in pad(header))
    body = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in pad(r)) + "</tr>"
        for r in rows
    )
    return f"<table><tbody><tr>{head}</tr>{body}</tbody></table>"


def convert_markdown(md: str, heading_as_strong: bool = False) -> str:
    """Markdown -> Confluence storage XHTML. heading_as_strong renders headings
    as a bold paragraph (needed inside blockquotes - Confluence ignores <hN> there)."""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    i, n = 0, len(lines)

    def flush_para() -> None:
        if para:
            txt = " ".join(p.strip() for p in para).strip()
            if txt:
                out.append(f"<p>{_inline(txt)}</p>")
            para.clear()

    while i < n:
        s = lines[i].strip()
        if not s:
            flush_para()
            i += 1
            continue

        if s.startswith("```") or s.startswith("~~~"):
            fence = s[:3]
            lang = s[3:].strip() or "text"
            flush_para()
            i += 1
            buf: list[str] = []
            while i < n and not lines[i].strip().startswith(fence):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(_code_macro("\n".join(buf), lang))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush_para()
            lvl = len(m.group(1))
            inner = _inline(m.group(2).strip())
            out.append(
                f"<p><strong>{inner}</strong></p>"
                if heading_as_strong
                else f"<h{lvl}>{inner}</h{lvl}>"
            )
            i += 1
            continue

        if set(s) <= set("-*_") and len(s) >= 3:
            flush_para()
            out.append("<hr/>")
            i += 1
            continue

        if "|" in s and i + 1 < n and _is_table_separator(lines[i + 1]):
            flush_para()
            header = _split_row(s)
            i += 2
            rows: list[list[str]] = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            out.append(_render_table(header, rows))
            continue

        if s.startswith(">"):
            flush_para()
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = convert_markdown(chr(10).join(quote), heading_as_strong=True)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        if re.match(r"^[-*+]\s+", s):
            flush_para()
            items: list[str] = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*+]\s+", "", lines[i].strip()))
                i += 1
            out.append(
                "<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>"
            )
            continue

        if re.match(r"^\d+\.\s+", s):
            flush_para()
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append(
                "<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ol>"
            )
            continue

        para.append(s)
        i += 1

    flush_para()
    return "".join(out)


def split_title_body(md: str) -> tuple[str, str]:
    lines = md.replace("\r\n", "\n").split("\n")
    title, body_lines, taken = "", [], False
    for line in lines:
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m and not taken:
            title = m.group(1).strip()
            taken = True
            continue
        body_lines.append(line)
    return title, "\n".join(body_lines)


def md_file_to_page(text: str, fallback_title: str) -> tuple[str, str]:
    title, body = split_title_body(text)
    return (title or fallback_title), convert_markdown(body)


def rewrite_internal_links(storage: str, link_map: dict[str, str]) -> str:
    """<a href="NN.md">Text</a> -> Confluence page link by title."""

    def repl(m: re.Match) -> str:
        href, text = m.group(1), m.group(2)
        base = href.split("/")[-1].split("#")[0]
        title = link_map.get(base)
        if not title:
            return m.group(0)
        t = html.escape(title, quote=True)
        return (
            f'<ac:link><ri:page ri:content-title="{t}"/>'
            f"<ac:link-body>{text}</ac:link-body></ac:link>"
        )

    return re.sub(r'<a href="([^"]+)">(.*?)</a>', repl, storage)


def with_toc(storage: str, min_headings: int = 4) -> str:
    if storage.count("<h2>") + storage.count("<h3>") >= min_headings:
        return (
            '<ac:structured-macro ac:name="toc">'
            '<ac:parameter ac:name="maxLevel">3</ac:parameter>'
            "</ac:structured-macro>"
        ) + storage
    return storage
