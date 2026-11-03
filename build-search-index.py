#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор индекса полнотекстового поиска по сайту (search-index.json).

Обходит все *.html и *.shtml в корне репозитория, извлекает из каждого:
  - url (имя файла),
  - <title>,
  - заголовки h1-h4 с их id (для якорных ссылок),
  - текст <main> (без скриптов, стилей, комментариев, разметки).

Дополнительно текст каждой страницы переводится на беларускую мову
(тот же Google Translate, что переводит сайт кнопкой BE) и сохраняется
полями titleBe / headingsBe / textBe — чтобы поиск работал по-беларусски,
включая части слов («адпавед» -> «адпаведнасці»).

Переводы кэшируются в search-index.be.cache.json: при повторном запуске
переводятся только изменившиеся фрагменты. Сбой перевода не ломает сборку:
страница просто остаётся без BE-полей (поиск по ней будет русским).

Запуск после любой правки контента:
    python build-search-index.py            # RU + BE
    python build-search-index.py --no-be    # только русский индекс
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
CHUNK_LIMIT = 900      # максимум символов в одном запросе перевода

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
    text = html_unescape(text)
    return WS_RE.sub(" ", text).strip()


def html_unescape(text):
    import html as _html

    return _html.unescape(text)


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


# ---------------------------------------------------------------------------
# Перевод на беларускую мову (Google Translate, gtx)
# ---------------------------------------------------------------------------

class BeTranslator:
    def __init__(self, cache):
        self.cache = cache          # {исходный фрагмент: перевод}
        self.requests = 0
        self.failures = 0

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

    def translate_chunks(self, text):
        """Перевод длинного текста кусками по ~CHUNK_LIMIT символов."""
        if not text:
            return None
        pieces = split_sentences(text, CHUNK_LIMIT)
        out_pieces = []
        failed = 0
        for piece in pieces:
            cached = self.cache.get(piece)
            if cached is None:
                cached = self._call(piece, "ru", "be")
                if cached is None:
                    failed += 1
                    out_pieces.append(piece)  # оставляем русский кусок
                    continue
                self.cache[piece] = cached
            out_pieces.append(cached)
        if failed and failed == len(pieces):
            return None  # вообще ничего не перевелось
        return WS_RE.sub(" ", " ".join(out_pieces)).strip()

    def translate_lines(self, lines):
        """Перевод списка строк (заголовки): батчами через "\\n".
        Возвращает список той же длиности; при сбое строка остаётся русской."""
        if not lines:
            return []
        result = list(lines)
        # кэшируемые сразу
        pending = []  # индексы строк без кэша
        for i, line in enumerate(lines):
            if not line:
                continue
            cached = self.cache.get(line)
            if cached is not None:
                result[i] = cached
            else:
                pending.append(i)
        # батчи из незакэшированных
        batch, batch_idx = [], []

        def flush():
            if not batch:
                return
            joined = "\n".join(batch)
            out = self._call(joined, "ru", "be")
            if out is not None:
                parts = out.split("\n")
                if len(parts) == len(batch):
                    for i, part in zip(batch_idx, parts):
                        result[i] = part
                        self.cache[lines[i]] = part
                    batch.clear()
                    batch_idx.clear()
                    return
            # расхождение строк — переводим по одному
            for i in list(batch_idx):
                out1 = self._call(lines[i], "ru", "be")
                if out1 is not None:
                    result[i] = out1
                    self.cache[lines[i]] = out1
            batch.clear()
            batch_idx.clear()

        for i in pending:
            if len(batch) >= 25 or (
                batch and len(batch) + len(lines[i]) > CHUNK_LIMIT
            ):
                flush()
            batch.append(lines[i])
            batch_idx.append(i)
        flush()
        return result


def split_sentences(text, limit):
    """Разбивает текст на куски не длиннее limit по границам предложений."""
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
        json.dump(cache, fh, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------


def collect_pages(with_be=True, be_cache=None):
    translator = BeTranslator(be_cache) if with_be else None
    pages = []
    be_ok = be_fail = 0
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
        page = {
            "url": name,
            "title": title or name,
            "headings": headings,
            "text": body,
        }

        if with_be:
            print("  be: %s" % name)
            title_be = translator.translate_lines([page["title"]])[0]
            heads_be = translator.translate_lines([h["t"] for h in headings])
            text_be = translator.translate_chunks(body)
            if text_be:
                page["titleBe"] = title_be
                page["headingsBe"] = [
                    {"t": heads_be[i], "id": headings[i]["id"]}
                    for i in range(len(headings))
                ]
                page["textBe"] = text_be
                be_ok += 1
            else:
                be_fail += 1
        pages.append(page)

    if with_be:
        print(
            "BE: ok=%d, fail=%d, requests=%d, failures=%d, cache=%d"
            % (be_ok, be_fail, translator.requests,
               translator.failures, len(be_cache))
        )
    return pages


def main():
    with_be = "--no-be" not in sys.argv
    be_cache = load_be_cache() if with_be else None

    print("collecting pages%s..." % ("" if with_be else " (RU only)"))
    pages = collect_pages(with_be=with_be, be_cache=be_cache)

    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages": pages,
    }
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

    if with_be and be_cache is not None:
        save_be_cache(be_cache)

    total_chars = sum(len(p["text"]) for p in pages)
    be_chars = sum(len(p.get("textBe", "")) for p in pages)
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(
        "pages: %d (be: %d), headings: %d, text chars: %d (be: %d), "
        "file: %.1f KB"
        % (
            len(pages),
            sum(1 for p in pages if "textBe" in p),
            sum(len(p["headings"]) for p in pages),
            total_chars,
            be_chars,
            size_kb,
        )
    )
    print("written: %s" % OUT_PATH)


if __name__ == "__main__":
    main()
