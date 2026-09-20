#!/usr/bin/env python3
"""Менеджер новостей сайта Сертис.

Добавляет новость и автоматически перераспределяет страницы.
Запуск: python blog_manager.py
"""

import glob
import os
import re
from datetime import datetime

PAGE_SIZE = 10
SIDEBAR_SIZE = 10

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
TITLE_RE = re.compile(
    r'<h2 class="entry-title">\s*<a\s+href="javascript:void\(0\)"[^>]*>\s*(.*?)\s*</a\s*>\s*</h2>',
    re.S,
)
TIME_RE = re.compile(r'<time datetime="\s*([^"]+)"\s*>(.*?)</time\s*>', re.S)
IMG_RE = re.compile(
    r'<img\s+src="([^"]+)"\s+alt=""\s+class="img-fluid"\s*/>', re.S
)
PAGIN_RE = re.compile(
    r'<div class="blog-pagination">.*?<!-- End blog entries list -->', re.S
)
RECENT_RE = re.compile(
    r'<div class="sidebar-item recent-posts">.*?<!-- End sidebar recent posts-->', re.S
)
PAGE_FILE_RE = re.compile(r"^blog\d*\.html$")


def collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def format_date_ru(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day} {MONTHS_RU[dt.month]} {dt.year}"


def multiline_input(prompt):
    print(prompt)
    print("(Введите текст, завершите пустой строкой)")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def get_next_blog_number():
    numbers = []
    for f in glob.glob("blog*.html"):
        if not PAGE_FILE_RE.match(f):
            continue
        with open(f, "r", encoding="utf-8", newline="") as fh:
            numbers.extend(int(n) for n in re.findall(r'id="blog-(\d+)"', fh.read()))
    return max(numbers) + 1 if numbers else 1


def build_article_html(num, title, date_attr, date_ru, content_html):
    return (
        f'              <article class="entry" id="blog-{num}">\n'
        f'                <div class="entry-img">\n'
        f'                  <img\n'
        f'                    src="assets/img/blog/blog-{num}.webp"\n'
        f'                    alt=""\n'
        f'                    class="img-fluid"\n'
        f'                  />\n'
        f'                </div>\n'
        f'                <h2 class="entry-title">\n'
        f'                  <a href="javascript:void(0)"\n'
        f'                    >{title}</a\n'
        f'                  >\n'
        f'                </h2>\n'
        f'                <div class="entry-meta">\n'
        f'                  <ul>\n'
        f'                    <li class="d-flex align-items-center">\n'
        f'                      <i class="bi bi-person"></i>\n'
        f'                      <a href="javascript:void(0)">Сертис</a>\n'
        f'                    </li>\n'
        f'                    <li class="d-flex align-items-center">\n'
        f'                      <i class="bi bi-clock"></i>\n'
        f'                      <a href="javascript:void(0)"\n'
        f'                        ><time datetime="{date_attr}">{date_ru}</time></a\n'
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


def add_news():
    print("=" * 60)
    print("  Добавление новости")
    print("=" * 60)

    next_num = get_next_blog_number()
    print(f"\nСледующий номер новости: blog-{next_num}")

    title = input("\nЗаголовок новости: ").strip()
    date_str = input("Дата (YYYY-MM-DD): ").strip()
    try:
        date_ru = format_date_ru(date_str)
    except ValueError:
        print("ОШИБКА: неверный формат даты")
        return False
    print(f"Дата: {date_ru}")

    content_text = multiline_input("\nТекст новости:")
    paragraphs = [p.strip() for p in content_text.split("\n") if p.strip()]
    content_html = "<br /><br />\n                  ".join(paragraphs)

    article_html = build_article_html(next_num, title, date_str, date_ru, content_html)

    with open("blog.html", "r", encoding="utf-8", newline="") as f:
        blog_content = f.read()

    marker = '<article class="entry"'
    idx = blog_content.find(marker)
    if idx == -1:
        print("ОШИБКА: не найдено место для вставки статьи")
        return False

    blog_content = blog_content[:idx] + article_html + "\n" + blog_content[idx:]

    with open("blog.html", "w", encoding="utf-8", newline="") as f:
        f.write(blog_content)

    print(f"\n  Статья blog-{next_num} добавлена в blog.html")
    print(f"  Не забудьте добавить изображение: assets/img/blog/blog-{next_num}.webp")
    return True


def extract_articles(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        html = fh.read()
    articles = []
    for m in ARTICLE_RE.finditer(html):
        aid = m.group(1)
        block = m.group(0)
        title_m = TITLE_RE.search(block)
        time_m = TIME_RE.search(block)
        img_m = IMG_RE.search(block)
        date = time_m.group(1).strip() if time_m else ""
        date_text = collapse(time_m.group(2)) if time_m else ""
        articles.append({
            "id": aid,
            "date": date,
            "date_text": date_text,
            "title": collapse(title_m.group(1)) if title_m else "",
            "img": img_m.group(1) if img_m else "",
            "block": block,
        })
    return articles


def build_sidebar_item(art, page_file):
    inner = [
        '<div class="post-item clearfix">',
        f'  <img src="{art["img"]}" alt="" />',
        "  <h4>",
        f'    <a href="{page_file}#blog-{art["id"]}">{art["title"]}</a>',
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
        page_file = "blog.html" if i == 0 else f"blog{i}.html"
        cls = ' class="active"' if i == current else ""
        links.append(f'                  <li{cls}><a href="{page_file}">{i + 1}</a></li>')
    return (
        '              <div class="blog-pagination">\n'
        '                <ul class="justify-content-center">\n'
        + "\n".join(links) + "\n"
        '                </ul>\n'
        '              </div>\n'
        '            </div>\n'
        '            <!-- End blog entries list -->'
    )


def get_page(art, pages):
    for i, page in enumerate(pages):
        if any(a["id"] == art["id"] for a in page):
            return i
    return 0


def rebuild():
    print("\n" + "=" * 60)
    print("  Перераспределение страниц")
    print("=" * 60)

    page_files = sorted(
        (f for f in glob.glob("blog*.html") if PAGE_FILE_RE.match(f)),
        key=lambda f: int(re.sub(r"\D", "", f) or 0),
    )
    if not page_files:
        print("Не найдено blog*.html файлов")
        return

    all_articles = []
    seen = set()
    for pf in page_files:
        for art in extract_articles(pf):
            if art["id"] in seen:
                continue
            seen.add(art["id"])
            all_articles.append(art)

    if not all_articles:
        print("Не найдено статей")
        return

    all_articles.sort(key=lambda a: a["date"], reverse=True)

    if len(all_articles) <= PAGE_SIZE:
        pages = [all_articles]
    else:
        pages = []
        for i in range(0, len(all_articles), PAGE_SIZE):
            pages.append(all_articles[i : i + PAGE_SIZE])
    page_count = len(pages)

    with open("blog.html", "r", encoding="utf-8", newline="") as fh:
        template = fh.read()

    pos = template.find(ENTRIES_START)
    if pos == -1:
        print("Шаблон повреждён")
        return
    head = template[: pos + len(ENTRIES_START)]

    pagin_m = PAGIN_RE.search(template, pos)
    recent_m = RECENT_RE.search(template)
    if not pagin_m or not recent_m:
        print("Шаблон повреждён")
        return
    middle = template[pagin_m.end() : recent_m.start()]
    tail = template[recent_m.end() :]

    page_to_file = {0: "blog.html"}
    for i in range(1, page_count):
        page_to_file[i] = f"blog{i}.html"

    sidebar_articles = all_articles[:SIDEBAR_SIZE]

    for idx, articles in enumerate(pages):
        page_file = page_to_file[idx]
        body = [head, "\n"]
        for art in articles:
            body.append(reindent_block(art["block"]))
            body.append("\n")
        body.append(build_pagination(page_count, idx))
        body.append(middle)
        items = "\n".join(
            build_sidebar_item(art, page_to_file[get_page(art, pages)])
            for art in sidebar_articles
        )
        body.append(
            RECENT_START + "\n" + items + "\n"
            + '                </div>\n'
            + '                ' + RECENT_END
        )
        body.append(tail)
        with open(page_file, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(body))
        print(f"  {page_file}: {len(articles)} новостей")

    for f in page_files:
        if f not in page_to_file.values():
            os.remove(f)
            print(f"  Удалена: {f}")

    print(f"\n  Итого: {page_count} страниц, {len(all_articles)} новостей")
    print(f"  Сайдбар: {SIDEBAR_SIZE} последних публикаций")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 60)
    print("  Менеджер новостей сайта Сертис")
    print("=" * 60)
    print("\n  1) Добавить новость и перераспределить")
    print("  2) Только перераспределить страницы")
    choice = input("\nВыбор [1]: ").strip() or "1"

    if choice == "1":
        if add_news():
            rebuild()
    elif choice == "2":
        rebuild()
    else:
        print("Неверный выбор")


if __name__ == "__main__":
    main()
