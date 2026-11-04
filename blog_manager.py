#!/usr/bin/env python3
"""Менеджер новостей сайта Сертис.

Новости лежат прямо в страницах blog.html, blog1.html, ... (по PAGE_SIZE
штук, новые — первыми). Скрипт:
  - добавляет новость (текст, дата, картинка) и пересобирает страницы блога;
  - раскладывает все новости по страницам, обновляет пагинацию, блок
    «Последние публикации» и шапку страниц (title, canonical, description);
  - приводит sitemap.xml в соответствие числу страниц блога.

Тексты самих новостей не пересобираются: блок <article> переносится как есть.
Перед записью проверяется, что ни одна новость не потерялась; если что-то
не сходится — ничего не пишется.

Запуск из любой папки (скрипт сам переходит в папку сайта):
    python blog_manager.py                 # интерактивное меню
    python blog_manager.py add             # добавить новость (вопросы по шагам)
    python blog_manager.py rebuild         # перераспределить страницы
    python blog_manager.py check           # показать, что изменится, ничего не меняя

После правок: git add/commit/push — GitHub Actions пересоберёт поиск.
"""

import argparse
import glob
import html
import os
import re
import shutil
import sys
from datetime import date, datetime, timezone

PAGE_SIZE = 10
SIDEBAR_SIZE = 10
IMG_DIR = "assets/img/blog"
SITE_URL = "https://sertis.by"
SITEMAP = "sitemap.xml"

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

ENTRIES_START = '<div class="col-lg-8 entries">'
RECENT_START = '<div class="sidebar-item recent-posts">'
RECENT_END = "<!-- End sidebar recent posts-->"

ARTICLE_RE = re.compile(
    r'<article class="entry" id="blog-([^"]+)">.*?</article>\s*<!-- End blog entry -->',
    re.S,
)
ARTICLE_OPEN_RE = re.compile(r'<article class="entry"')
TITLE_RE = re.compile(
    r'<h2 class="entry-title">\s*<a\b[^>]*>\s*(.*?)\s*</a\s*>\s*</h2>', re.S
)
TIME_RE = re.compile(r'<time datetime="\s*([^"]*?)\s*"\s*>(.*?)</time\s*>', re.S)
IMG_RE = re.compile(r'<img\b[^>]*?\bsrc="([^"]+)"', re.S)
PAGIN_RE = re.compile(
    r'<div class="blog-pagination">.*?<!-- End blog entries list -->', re.S
)
RECENT_RE = re.compile(
    r'<div class="sidebar-item recent-posts">.*?<!-- End sidebar recent posts-->', re.S
)
PAGE_FILE_RE = re.compile(r"^blog\d*\.html$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(((?:files/|/files/|https?://)[^)\s]+)\)")


class BlogError(Exception):
    """Ошибка, после которой ничего записывать нельзя."""


# --------------------------------------------------------------------------
# Вспомогательное
# --------------------------------------------------------------------------

def collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def format_date_ru(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day} {MONTHS_RU[dt.month]} {dt.year}"


def id_key(art_id):
    """'38-1' -> (38, 1): для устойчивой сортировки новостей одной даты."""
    return tuple(int(n) for n in re.findall(r"\d+", art_id))


def page_file_name(index):
    return "blog.html" if index == 0 else f"blog{index}.html"


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read().replace("\r\n", "\n")


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    os.replace(tmp, path)


def blog_page_files():
    files = [f for f in glob.glob("blog*.html") if PAGE_FILE_RE.match(f)]
    return sorted(files, key=lambda f: int(re.sub(r"\D", "", f) or 0))


# --------------------------------------------------------------------------
# Разбор страниц
# --------------------------------------------------------------------------

def extract_articles(path, html_text):
    """Новости страницы; бросает BlogError, если какую-то не удалось разобрать."""
    found = ARTICLE_RE.findall(html_text)
    opened = len(ARTICLE_OPEN_RE.findall(html_text))
    if len(found) != opened:
        raise BlogError(
            f"{path}: найдено {opened} тегов <article class=\"entry\">, "
            f"а разобрано {len(found)} — проверьте маркеры "
            f"'<!-- End blog entry -->'"
        )
    articles = []
    for m in ARTICLE_RE.finditer(html_text):
        block = m.group(0)
        title_m = TITLE_RE.search(block)
        time_m = TIME_RE.search(block)
        img_m = IMG_RE.search(block)
        if not title_m or not time_m:
            raise BlogError(
                f"{path}: у blog-{m.group(1)} не найден заголовок или дата"
            )
        articles.append({
            "id": m.group(1),
            "date": time_m.group(1).strip(),
            "date_text": collapse(time_m.group(2)),
            "title": collapse(title_m.group(1)),
            "img": img_m.group(1) if img_m else "",
            "block": block,
        })
    return articles


def load_articles():
    """(все новости без дублей, шаблон = blog.html)."""
    page_files = blog_page_files()
    if "blog.html" not in page_files:
        raise BlogError("Не найден blog.html")
    articles, seen = [], set()
    for pf in page_files:
        for art in extract_articles(pf, read_text(pf)):
            if art["id"] in seen:
                print(f"  ПРЕДУПРЕЖДЕНИЕ: повтор blog-{art['id']} в {pf} пропущен")
                continue
            seen.add(art["id"])
            articles.append(art)
    if not articles:
        raise BlogError("Не найдено ни одной новости")
    return articles, read_text("blog.html")


# --------------------------------------------------------------------------
# Генерация новости
# --------------------------------------------------------------------------

def next_blog_number(articles):
    numbers = [id_key(a["id"])[0] for a in articles if id_key(a["id"])]
    return max(numbers) + 1 if numbers else 1


def text_to_html(text):
    """Строки -> абзацы. Текст экранируется; ссылки пишутся как
    [текст](files/документ.pdf) или [текст](https://...)."""
    paragraphs = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        safe = html.escape(line, quote=False)
        safe = LINK_RE.sub(
            lambda m: (
                f'<a href="{html.escape(m.group(2), quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{m.group(1)}</a>'
            ),
            safe,
        )
        paragraphs.append(safe)
    return "<br /><br />\n                  ".join(paragraphs)


def build_article_html(num, title, date_attr, date_ru, content_html):
    return (
        f'              <article class="entry" id="blog-{num}">\n'
        f'                <div class="entry-img">\n'
        f'                  <img loading="lazy" decoding="async"\n'
        f'                    src="{IMG_DIR}/blog-{num}.webp"\n'
        f'                    alt=""\n'
        f'                    class="img-fluid"\n'
        f'                  />\n'
        f'                </div>\n'
        f'                <h2 class="entry-title">\n'
        f'                  <a class="pseudo-link">{title}</a\n'
        f'                  >\n'
        f'                </h2>\n'
        f'                <div class="entry-meta">\n'
        f'                  <ul>\n'
        f'                    <li class="d-flex align-items-center">\n'
        f'                      <i class="bi bi-person"></i>\n'
        f'                      <a class="pseudo-link">Сертис</a>\n'
        f'                    </li>\n'
        f'                    <li class="d-flex align-items-center">\n'
        f'                      <i class="bi bi-clock"></i>\n'
        f'                      <a class="pseudo-link"><time datetime="{date_attr}">{date_ru}</time></a\n'
        f'                      >\n'
        f'                    </li>\n'
        f'                  </ul>\n'
        f'                </div>\n'
        f'                <div class="entry-content">\n'
        f'                  {content_html}\n'
        f'                </div>\n'
        f'              </article>\n'
        f'              <!-- End blog entry -->'
    )


def make_article(num, title, date_str, text):
    date_ru = format_date_ru(date_str)  # ValueError при неверной дате
    title_html = html.escape(collapse(title), quote=False)
    content = text_to_html(text)
    if not title_html or not content:
        raise BlogError("Нужны непустые заголовок и текст")
    return {
        "id": str(num),
        "date": date_str,
        "date_text": date_ru,
        "title": title_html,
        "img": f"{IMG_DIR}/blog-{num}.webp",
        "block": build_article_html(num, title_html, date_str, date_ru, content),
    }


def import_image(src, num):
    """Кладёт картинку в assets/img/blog/blog-N.webp (jpg/png — через Pillow)."""
    dest = f"{IMG_DIR}/blog-{num}.webp"
    src = src.strip().strip('"')
    if not os.path.isfile(src):
        raise BlogError(f"Файл картинки не найден: {src}")
    os.makedirs(IMG_DIR, exist_ok=True)
    if src.lower().endswith(".webp"):
        shutil.copyfile(src, dest)
        return dest
    try:
        from PIL import Image  # необязательная зависимость
    except ImportError:
        raise BlogError(
            "Для jpg/png нужен Pillow (pip install pillow) "
            "или сначала сохраните картинку в формате .webp"
        )
    with Image.open(src) as im:
        im.thumbnail((1200, 1200))
        im.convert("RGB").save(dest, "WEBP", quality=82)
    return dest


# --------------------------------------------------------------------------
# Сборка страниц
# --------------------------------------------------------------------------

def build_sidebar_item(art, page_file):
    inner = [
        '<div class="post-item clearfix">',
        f'  <img loading="lazy" decoding="async" src="{art["img"]}" alt="" />',
        "  <h4>",
        f'    <a href="{page_file}#blog-{art["id"]}"',
        f'      >{art["title"]}</a',
        "    >",
        "  </h4>",
        f'  <time datetime="{art["date"]}">{art["date_text"]}</time>',
        "</div>",
    ]
    return "\n".join(" " * 18 + line for line in inner)


def reindent_block(block):
    return re.sub(r"^\s*<article", "              <article", block, count=1)


def build_pagination(page_count, current):
    links = []
    for i in range(page_count):
        cls = ' class="active"' if i == current else ""
        links.append(
            f'                  <li{cls}><a href="{page_file_name(i)}">{i + 1}</a></li>'
        )
    return (
        '              <div class="blog-pagination">\n'
        '                <ul class="justify-content-center">\n'
        + "\n".join(links) + "\n"
        '                </ul>\n'
        '              </div>\n'
        '            </div>\n'
        '            <!-- End blog entries list -->'
    )


def head_for_page(first_head, index):
    """Шапка страницы N из шапки blog.html: свои title, canonical, og:url,
    og:title и description с пометкой «Страница N»."""
    if index == 0:
        return first_head
    number, file = index + 1, page_file_name(index)
    head = first_head
    subs = [
        ("<title>Сертис - Новости</title>",
         f"<title>Сертис - Новости, страница {number}</title>"),
        (f'href="{SITE_URL}/blog.html"', f'href="{SITE_URL}/{file}"'),
        (f'property="og:url" content="{SITE_URL}/blog.html"',
         f'property="og:url" content="{SITE_URL}/{file}"'),
        ('property="og:title" content="Сертис - Новости"',
         f'property="og:title" content="Сертис - Новости, страница {number}"'),
    ]
    for old, new in subs:
        if old not in head:
            print(f"  ПРЕДУПРЕЖДЕНИЕ: в шапке blog.html не найдено «{old[:50]}…»")
        head = head.replace(old, new)
    head = re.sub(
        r'(content="Новости РУП [^"]*?\.)(")',
        lambda m: f'{m.group(1)} Страница {number}.{m.group(2)}',
        head,
    )
    return head


def compose_pages(articles, template):
    """Возвращает {имя_файла: готовый html} и список страниц (для проверок)."""
    pos = template.find(ENTRIES_START)
    pagin_m = PAGIN_RE.search(template, pos) if pos != -1 else None
    recent_m = RECENT_RE.search(template)
    if pos == -1 or not pagin_m or not recent_m:
        raise BlogError(
            "Шаблон blog.html повреждён: не найдены список новостей, "
            "пагинация или блок «Последние публикации»"
        )
    first_head = template[: pos + len(ENTRIES_START)]
    middle = template[pagin_m.end(): recent_m.start()]
    tail = template[recent_m.end():]

    ordered = sorted(
        articles, key=lambda a: (a["date"], id_key(a["id"])), reverse=True
    )
    pages = [ordered[i: i + PAGE_SIZE] for i in range(0, len(ordered), PAGE_SIZE)]
    page_of = {a["id"]: i for i, page in enumerate(pages) for a in page}

    sidebar = "\n".join(
        build_sidebar_item(a, page_file_name(page_of[a["id"]]))
        for a in ordered[:SIDEBAR_SIZE]
    )
    outputs = {}
    for idx, page in enumerate(pages):
        parts = [head_for_page(first_head, idx), "\n"]
        for art in page:
            parts += [reindent_block(art["block"]), "\n"]
        parts.append(build_pagination(len(pages), idx))
        parts.append(middle)
        parts.append(
            RECENT_START + "\n" + sidebar + "\n"
            + "                </div>\n"
            + "                " + RECENT_END
        )
        parts.append(tail)
        outputs[page_file_name(idx)] = "".join(parts)
    return outputs, pages


def verify(outputs, articles):
    """Страховка: после сборки в страницах те же новости, что и до неё."""
    after = []
    for name, text in outputs.items():
        after += [a["id"] for a in extract_articles(name, text)]
    before = sorted(a["id"] for a in articles)
    if sorted(after) != before:
        lost = set(before) - set(after)
        raise BlogError(
            f"Проверка не пройдена: новости до {len(before)}, после "
            f"{len(after)}; пропали: {', '.join(sorted(lost)) or '—'}"
        )


def check_images(articles):
    for art in articles:
        if not art["img"]:
            print(f"  ПРЕДУПРЕЖДЕНИЕ: у blog-{art['id']} нет картинки")
        elif not os.path.exists(art["img"]):
            print(f"  ПРЕДУПРЕЖДЕНИЕ: нет файла {art['img']} (blog-{art['id']})")


# --------------------------------------------------------------------------
# sitemap.xml
# --------------------------------------------------------------------------

SITEMAP_BLOG_RE = re.compile(
    r"[ \t]*<url>\s*<loc>" + re.escape(SITE_URL) + r"/(blog\d*\.html)</loc>"
    r"\s*<lastmod>[^<]*</lastmod>\s*</url>\n?"
)


def sitemap_entry(file, lastmod):
    return (
        f"    <url>\n        <loc>{SITE_URL}/{file}</loc>\n"
        f"        <lastmod>{lastmod}</lastmod>\n    </url>\n"
    )


def updated_sitemap(page_files, changed):
    """Новый текст sitemap.xml или None, если он не требует изменений."""
    if not os.path.isfile(SITEMAP):
        return None
    text = read_text(SITEMAP)
    entries = list(SITEMAP_BLOG_RE.finditer(text))
    if not entries:
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")
    old_lastmod = {
        m.group(1): re.search(r"<lastmod>([^<]*)</lastmod>", m.group(0)).group(1)
        for m in entries
    }
    block = "".join(
        sitemap_entry(f, today if f in changed or f not in old_lastmod else old_lastmod[f])
        for f in page_files
    )
    first, last = entries[0].start(), entries[-1].end()
    new = text[:first] + block + text[last:]
    return None if new == text else new


# --------------------------------------------------------------------------
# Основные действия
# --------------------------------------------------------------------------

def rebuild(extra_articles=(), dry_run=False):
    print("\n" + "=" * 60)
    print("  Проверка страниц блога" if dry_run else "  Сборка страниц блога")
    print("=" * 60)

    articles, template = load_articles()
    articles = list(articles) + list(extra_articles)
    check_images(articles)

    outputs, pages = compose_pages(articles, template)
    verify(outputs, articles)

    changed = []
    for name, text in outputs.items():
        current = read_text(name) if os.path.isfile(name) else None
        if current != text:
            changed.append(name)
    surplus = [f for f in blog_page_files() if f not in outputs]
    new_sitemap = updated_sitemap(list(outputs), set(changed))

    for name, page in zip(outputs, pages):
        mark = "изменится" if name in changed else "без изменений"
        print(f"  {name}: {len(page)} новостей ({mark})")
    for f in surplus:
        print(f"  {f}: будет удалена (лишняя страница)")
    if new_sitemap is not None:
        print(f"  {SITEMAP}: будет обновлён")

    if dry_run:
        print("\n  Это только проверка — файлы не менялись.")
        return changed
    for name in changed:
        write_text(name, outputs[name])
    for f in surplus:
        os.remove(f)
    if new_sitemap is not None:
        write_text(SITEMAP, new_sitemap)
    print(f"\n  Готово: {len(pages)} страниц, {len(articles)} новостей.")
    print("  Дальше: git add -A, commit, push — поиск пересоберётся сам.")
    return changed


def add_news(title, date_str, text, image=None, dry_run=False):
    articles, _ = load_articles()
    num = next_blog_number(articles)
    article = make_article(num, title, date_str, text)
    if image:
        import_image(image, num)
    elif not os.path.exists(article["img"]):
        print(f"  Не забудьте положить картинку: {article['img']}")
    print(f"\n  Новость blog-{num}: «{collapse(title)}», {article['date_text']}")
    return rebuild(extra_articles=[article], dry_run=dry_run)


def multiline_input(prompt):
    print(prompt)
    print("(Каждая строка — отдельный абзац. Ссылка: [текст](files/файл.pdf). "
          "Закончите пустой строкой.)")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def add_news_interactive():
    print("=" * 60)
    print("  Добавление новости")
    print("=" * 60)
    title = input("\nЗаголовок новости: ").strip()
    date_str = input(f"Дата (ГГГГ-ММ-ДД) [{date.today().isoformat()}]: ").strip()
    date_str = date_str or date.today().isoformat()
    text = multiline_input("\nТекст новости:")
    image = input("\nКартинка (путь к файлу, Enter — добавлю сам позже): ").strip()
    return add_news(title, date_str, text, image or None)


def main(argv=None):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="Менеджер новостей сайта Сертис")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("rebuild", help="перераспределить страницы блога")
    sub.add_parser("check", help="показать, что изменится, ничего не меняя")
    add = sub.add_parser("add", help="добавить новость")
    add.add_argument("--title")
    add.add_argument("--date")
    add.add_argument("--text-file", help="файл с текстом (строка = абзац)")
    add.add_argument("--image", help="картинка (webp, jpg или png)")
    args = parser.parse_args(argv)

    try:
        if args.command == "rebuild":
            rebuild()
        elif args.command == "check":
            rebuild(dry_run=True)
        elif args.command == "add" and args.title and args.date and args.text_file:
            with open(args.text_file, "r", encoding="utf-8") as fh:
                add_news(args.title, args.date, fh.read(), args.image)
        elif args.command == "add":
            add_news_interactive()
        else:
            print("=" * 60)
            print("  Менеджер новостей сайта Сертис")
            print("=" * 60)
            print("\n  1) Добавить новость")
            print("  2) Перераспределить страницы")
            print("  3) Только проверить (ничего не менять)")
            choice = input("\nВыбор [1]: ").strip() or "1"
            if choice == "1":
                add_news_interactive()
            elif choice == "2":
                rebuild()
            elif choice == "3":
                rebuild(dry_run=True)
            else:
                print("Неверный выбор")
    except (BlogError, ValueError) as err:
        print(f"\n  ОШИБКА: {err}\n  Ничего не записано.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
