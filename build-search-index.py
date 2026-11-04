#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор индекса полнотекстового поиска по сайту (search-index.json).

Обходит все *.html и *.shtml в корне репозитория, извлекает из каждого:
  - url (имя файла),
  - <title>,
  - заголовки h1-h4 с их id (для якорных ссылок),
  - текст <main>, разбитый на «сегменты» (предложения / короткие абзацы).

Статьи пишутся только по-русски. Для белорусского режима каждый сегмент,
заголовок и <title> переводятся на беларускую мову (Google Translate gtx,
тот же движок, что и у кнопки BE на сайте) и хранятся В ПАРЕ с оригиналом:
    "segs": [["русский сегмент", "беларускі сегмент"], ...]
Благодаря выровненным парам браузеру посетителя не нужно ничего переводить
на лету: поиск идёт по обоим языкам, а выдача показывается на языке режима.

Кэш переводов — search-index.be.cache.json ({русская строка: перевод}).
При повторном запуске переводятся только новые и изменённые сегменты;
строки, которых больше нет на сайте, из кэша удаляются.

Запуск (обычно — автоматически, см. .github/workflows/search-index.yml):
    py -3 build-search-index.py            # RU + BE
    py -3 build-search-index.py --no-be    # только русский индекс

Код возврата: 0 — всё хорошо; 2 — часть сегментов не удалось перевести
(индекс записан, непереведённые сегменты остались русскими и будут
переведены при следующем запуске).
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(ROOT, "search-index.json")
BE_CACHE_PATH = os.path.join(ROOT, "search-index.be.cache.json")

GTX_URL = (
    "https://translate.googleapis.com/translate_a/single"
    "?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}"
)
REQUEST_SLEEP = 0.15   # пауза между запросами к Google
MAX_RETRIES = 3        # повторы при 429/5xx
BATCH_LIMIT = 900      # максимум символов в одном запросе перевода
BATCH_LINES = 25       # максимум строк в одном запросе перевода
SEG_LIMIT = 300        # максимум символов в одном сегменте
EXIT_PARTIAL = 2       # код возврата: часть переводов не удалась

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
# Границы блоков: между ними сегменты не склеиваются
BLOCK_RE = re.compile(
    r"</?(?:p|div|li|ul|ol|tr|td|th|table|br|h[1-6]|section|article|"
    r"header|footer|blockquote|dd|dt|figcaption)\b[^>]*>",
    re.IGNORECASE,
)
BLOCK_MARK = "\x00"
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def strip_tags(fragment):
    """Разметка -> чистый текст (сущности разворачиваются, пробелы схлопываются)."""
    text = TAG_RE.sub(" ", fragment)
    text = html_unescape(text)
    return WS_RE.sub(" ", text).strip()


def html_unescape(text):
    import html as _html

    return _html.unescape(text)


def text_blocks(fragment):
    """Разметка -> список непустых текстовых блоков (абзацы, пункты, ячейки)."""
    marked = BLOCK_RE.sub(BLOCK_MARK, fragment)
    blocks = (strip_tags(part) for part in marked.split(BLOCK_MARK))
    return [b for b in blocks if b]


def extract(raw):
    """(title, [{t, id}...] заголовки, [сегменты main]) из сырого HTML."""
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

    segments = []
    for block in text_blocks(main):
        segments.extend(split_sentences(block, SEG_LIMIT))
    return title, headings, segments


# ---------------------------------------------------------------------------
# Перевод на беларускую мову (Google Translate, gtx)
# ---------------------------------------------------------------------------

class BeTranslator:
    def __init__(self, cache):
        self.cache = cache          # {исходный фрагмент: перевод}
        self.used = set()           # какие ключи кэша нужны сайту сейчас
        self.requests = 0
        self.failures = 0           # неудачные HTTP-запросы (с повторами)
        self.unresolved = 0         # строки, которые так и остались русскими

    def _call(self, text, sl, tl):
        url = GTX_URL.format(
            sl=sl, tl=tl, q=urllib.parse.quote(text)
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (sertis-search-index)"}
        )
        last_err = None
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                self.requests += 1
                out = "".join(seg[0] for seg in data[0])
                time.sleep(REQUEST_SLEEP)
                return out
            except (urllib.error.URLError, urllib.error.HTTPError,
                    ValueError, OSError) as err:
                last_err = err
                code = getattr(err, "code", None)
                if isinstance(err, urllib.error.HTTPError) and code not in (
                    429, 500, 502, 503, 504
                ):
                    break  # не временная ошибка — не повторяем
                time.sleep(1.5 * (attempt + 1))
        self.failures += 1
        print("    ! перевод не удался: %s" % last_err)
        return None

    def translate_lines(self, lines):
        """Перевод списка строк батчами через "\\n".
        Возвращает список той же длины; строка, которую не удалось
        перевести, остаётся русской (и в кэш не попадает)."""
        if not lines:
            return []
        result = list(lines)
        pending = []  # индексы строк без кэша
        for i, line in enumerate(lines):
            if not line:
                continue
            self.used.add(line)
            cached = self.cache.get(line)
            if cached is not None:
                result[i] = cached
            else:
                pending.append(i)

        batch, batch_idx = [], []

        def flush():
            if not batch:
                return
            out = self._call("\n".join(batch), "ru", "be")
            if out is not None:
                parts = out.split("\n")
                if len(parts) == len(batch):
                    for i, part in zip(batch_idx, parts):
                        result[i] = part
                        self.cache[lines[i]] = part
                    batch.clear()
                    batch_idx.clear()
                    return
            # расхождение строк или сбой — переводим по одной
            for i in list(batch_idx):
                out1 = self._call(lines[i], "ru", "be")
                if out1 is not None:
                    result[i] = out1
                    self.cache[lines[i]] = out1
                else:
                    self.unresolved += 1
            batch.clear()
            batch_idx.clear()

        for i in pending:
            if len(batch) >= BATCH_LINES or (
                batch and sum(len(s) for s in batch) + len(lines[i]) > BATCH_LIMIT
            ):
                flush()
            batch.append(lines[i])
            batch_idx.append(i)
        flush()
        return result

    def prune_cache(self):
        """Убирает из кэша переводы строк, которых больше нет на сайте."""
        dropped = [k for k in self.cache if k not in self.used]
        for key in dropped:
            del self.cache[key]
        return len(dropped)


def split_sentences(text, limit):
    """Разбивает текст на куски не длиннее limit по границам предложений
    (короткие предложения склеиваются, пока помещаются в limit)."""
    parts = re.split(r"(?<=[.!?;:])\s+", text)
    chunks, cur = [], ""
    for part in parts:
        if cur and len(cur) + 1 + len(part) > limit:
            chunks.append(cur)
            cur = part
        else:
            cur = (cur + " " + part) if cur else part
        # сверхдлинное предложение режем по пробелам
        while len(cur) > limit:
            cut = cur.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            chunks.append(cur[:cut].strip())
            cur = cur[cut:].strip()
    if cur:
        chunks.append(cur)
    return chunks


def load_be_cache():
    if os.path.isfile(BE_CACHE_PATH):
        try:
            with open(BE_CACHE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except (ValueError, OSError):
            pass
    return {}


def save_be_cache(cache):
    with open(BE_CACHE_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(cache, fh, ensure_ascii=False, separators=(",", ":"),
                  sort_keys=True)


# ---------------------------------------------------------------------------


def build_page(name, raw, translator):
    """Страница индекса или None, если на ней нечего искать."""
    title, headings, segments = extract(raw)
    if not title and not segments:
        return None
    page = {"url": name, "title": title or name}

    if translator is None:
        page["headings"] = headings
        page["segs"] = [[s] for s in segments]
        return page

    # Один вызов на страницу: [title] + заголовки + сегменты
    sources = [page["title"]] + [h["t"] for h in headings] + segments
    translated = translator.translate_lines(sources)
    n_heads = len(headings)
    page["titleBe"] = translated[0]
    page["headings"] = [
        {"t": h["t"], "b": translated[1 + i], "id": h["id"]}
        for i, h in enumerate(headings)
    ]
    page["segs"] = [
        [segments[i], translated[1 + n_heads + i]]
        for i in range(len(segments))
    ]
    return page


def collect_pages(translator):
    pages = []
    for name in sorted(os.listdir(ROOT)):
        if not (name.endswith(".html") or name.endswith(".shtml")):
            continue
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        if translator is not None:
            print("  be: %s" % name)
        page = build_page(name, raw, translator)
        if page is not None:
            pages.append(page)
    return pages


def main():
    with_be = "--no-be" not in sys.argv
    be_cache = load_be_cache() if with_be else None
    translator = BeTranslator(be_cache) if with_be else None

    print("collecting pages%s..." % ("" if with_be else " (RU only)"))
    pages = collect_pages(translator)

    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages": pages,
    }
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

    if translator is not None:
        dropped = translator.prune_cache()
        save_be_cache(be_cache)
        print(
            "BE: requests=%d, failed requests=%d, untranslated=%d, "
            "cache=%d (dropped stale: %d)"
            % (translator.requests, translator.failures,
               translator.unresolved, len(be_cache), dropped)
        )

    n_segs = sum(len(p["segs"]) for p in pages)
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(
        "pages: %d, headings: %d, segments: %d, file: %.1f KB"
        % (len(pages), sum(len(p["headings"]) for p in pages), n_segs, size_kb)
    )
    print("written: %s" % OUT_PATH)

    if translator is not None and translator.unresolved:
        print("WARNING: %d segments left untranslated" % translator.unresolved)
        return EXIT_PARTIAL
    return 0


if __name__ == "__main__":
    sys.exit(main())
