#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вставка модуля поиска во все страницы сайта (одноразово, идемпотентно).

Для каждого *.html / *.shtml в корне:
  1. подключает assets/css/search.css после style.css;
  2. подключает assets/js/search.js после main.js;
  3. добавляет кнопку-лупу в шапке перед переключателем языка.

Сами страницы повторно не трогает, если лупа уже установлена.
Байты файла сохраняются (UTF-8 round-trip), переводы строк не меняются.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

ANCHOR_LANG = "<!-- ====== ПЕРЕКЛЮЧАТЕЛЬ ЯЗЫКА ====== -->"
ANCHOR_CSS = '<link href="assets/css/style.css" rel="stylesheet" />'
ANCHOR_JS = '<script src="assets/js/main.js"></script>'

SEARCH_LINK = '<link href="assets/css/search.css" rel="stylesheet" />'
SEARCH_SCRIPT = '<script src="assets/js/search.js"></script>'


def process(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8")  # round-trip utf-8 -> байты не меняются

    if "headerSearchBtn" in text:
        return "skip (already done)"

    eol = "\r\n" if "\r\n" in text else "\n"
    original = text

    # 1. search.css сразу после style.css (с сохранением отступа строки)
    idx = text.find(ANCHOR_CSS)
    if idx < 0:
        return "FAIL: style.css anchor not found"
    line_start = text.rfind("\n", 0, idx) + 1
    indent = text[line_start:idx]
    insert_at = idx + len(ANCHOR_CSS)
    text = (
        text[:insert_at]
        + eol
        + indent
        + SEARCH_LINK
        + text[insert_at:]
    )

    # 2. search.js сразу после main.js
    idx = text.find(ANCHOR_JS)
    if idx < 0:
        return "FAIL: main.js anchor not found"
    line_start = text.rfind("\n", 0, idx) + 1
    indent = text[line_start:idx]
    insert_at = idx + len(ANCHOR_JS)
    text = (
        text[:insert_at]
        + eol
        + indent
        + SEARCH_SCRIPT
        + text[insert_at:]
    )

    # 3. кнопка-лупа перед комментарием переключателя языка
    idx = text.find(ANCHOR_LANG)
    if idx < 0:
        return "FAIL: lang-switcher anchor not found"
    line_start = text.rfind("\n", 0, idx) + 1
    indent = text[line_start:idx]  # отступ комментария (обычно 8 пробелов)
    # Кнопка собирается под фактический отступ файла:
    button = (
        indent
        + "<!-- ====== ПОИСК ПО САЙТУ ====== -->"
        + eol
        + indent
        + '<button'
        + eol
        + indent
        + '  type="button"'
        + eol
        + indent
        + '  class="header-search-btn"'
        + eol
        + indent
        + '  id="headerSearchBtn"'
        + eol
        + indent
        + '  aria-label="Поиск по сайту"'
        + eol
        + indent
        + '  title="Поиск по сайту (Ctrl+K)"'
        + eol
        + indent
        + ">"
        + eol
        + indent
        + '  <i class="bi bi-search" aria-hidden="true"></i>'
        + eol
        + indent
        + "</button>"
        + eol
        + eol
        + indent
    )
    text = text[:line_start] + button + text[idx:]

    if text == original:
        return "skip (no change)"

    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))
    return "done"


def main():
    done = skipped = failed = 0
    for name in sorted(os.listdir(ROOT)):
        if not (name.endswith(".html") or name.endswith(".shtml")):
            continue
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            continue
        result = process(path)
        if result == "done":
            done += 1
            print("  + %s" % name)
        elif result.startswith("skip"):
            skipped += 1
        else:
            failed += 1
            print("  ! %s: %s" % (name, result))
    print("---")
    print("inserted: %d, skipped: %d, failed: %d" % (done, skipped, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
