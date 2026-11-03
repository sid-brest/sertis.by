#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор индекса полнотекстового поиска по сайту (search-index.json).

Обходит все *.html и *.shtml в корне репозитория, извлекает из каждого:
  - url (имя файла),
  - <title>,
  - заголовки h1-h4 с их id (для якорных ссылок),
  - текст <main> (без скриптов, стилей, комментариев, разметки).

Результат: search-index.json в корне репозитория.
Запуск после любой правки контента:
    python build-search-index.py
"""

import html
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(ROOT, "search-index.json")

# Строки внутри этих тегов не индексируются
INERT_RE = re.compile(
    r"<(script|style|noscript|svg|template)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HEADING_RE = re.compile(
    r"<h([1-4])\b([^>]*)>(.*?)</h\1>", re.IGNORECASE | re.DOTALL
)
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_tags(fragment):
    """Разметка -> чистый текст (сущности разворачиваются, пробелы схлопываются)."""
    text = TAG_RE.sub(" ", fragment)
    text = html.unescape(text)
    return WS_RE.sub(" ", text).strip()


def extract(raw):
    """(title, [(text, id)...] заголовки, текст main) из сырого HTML."""
    m = TITLE_RE.search(raw)
    title = strip_tags(m.group(1)) if m else ""

    m = MAIN_RE.search(raw)
    main = m.group(1) if m else ""

    # Убираем инертные куски и комментарии до анализа
    main = INERT_RE.sub(" ", main)
    main = COMMENT_RE.sub(" ", main)

    headings = []
    for hm in HEADING_RE.finditer(main):
        text = strip_tags(hm.group(3))
        if not text:
            continue
        idm = ID_RE.search(hm.group(2))
        headings.append({"t": text, "id": idm.group(1) if idm else ""})

    body = strip_tags(main)
    return title, headings, body


def collect_pages():
    pages = []
    for name in sorted(os.listdir(ROOT)):
        if not (name.endswith(".html") or name.endswith(".shtml")):
            continue
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        title, headings, body = extract(raw)
        if not title and not body:
            continue
        pages.append(
            {
                "url": name,
                "title": title or name,
                "headings": headings,
                "text": body,
            }
        )
    return pages


def main():
    pages = collect_pages()
    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages": pages,
    }
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

    total_chars = sum(len(p["text"]) for p in pages)
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(
        "pages: %d, headings: %d, text chars: %d, file: %.1f KB"
        % (
            len(pages),
            sum(len(p["headings"]) for p in pages),
            total_chars,
            size_kb,
        )
    )
    print("written: %s" % OUT_PATH)


if __name__ == "__main__":
    main()
