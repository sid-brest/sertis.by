#!/usr/bin/env python3
"""Перераспределяет новости раздела «Новости» по страницам: blog.html (11 самых
свежих), blog1.html, blog2.html, ... (по 10, от свежих к старым).

Запуск: python rebuild_blog.py
"""

import glob
import os
import re

PAGE1_SIZE = 11
PAGE_SIZE = 10

ENTRIES_START = '<div class="col-lg-8 entries">'
ENTRIES_LIST_END = "<!-- End blog entries list -->"
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
        articles.append(
            {
                "id": aid,
                "date": date,
                "date_text": date_text,
                "title": collapse(title_m.group(1)) if title_m else "",
                "img": img_m.group(1) if img_m else "",
                "block": block,
            }
        )
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
        "              <div class=\"blog-pagination\">\n"
        "                <ul class=\"justify-content-center\">\n"
        + "\n".join(links)
        + "\n"
        "                </ul>\n"
        "              </div>\n"
        "            </div>\n"
        "            <!-- End blog entries list -->"
    )


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)

    page_files = sorted(
        (f for f in glob.glob("blog*.html") if PAGE_FILE_RE.match(f)),
        key=lambda f: int(re.sub(r"\D", "", f) or 0),
    )
    if not page_files:
        print("Не найдено ни одной страницы blog*.html")
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
        print("Не найдено ни одной новости")
        return

    all_articles.sort(key=lambda a: a["date"], reverse=True)

    if len(all_articles) <= PAGE1_SIZE:
        pages = [all_articles]
    else:
        pages = [all_articles[:PAGE1_SIZE]]
        rest = all_articles[PAGE1_SIZE:]
        for i in range(0, len(rest), PAGE_SIZE):
            pages.append(rest[i : i + PAGE_SIZE])
    page_count = len(pages)

    with open("blog.html", "r", encoding="utf-8", newline="") as fh:
        template = fh.read()

    pos = template.find(ENTRIES_START)
    if pos == -1:
        print("Шаблон повреждён: не найден блок entries")
        return
    head = template[: pos + len(ENTRIES_START)]

    pagin_m = PAGIN_RE.search(template, pos)
    recent_m = RECENT_RE.search(template)
    if not pagin_m or not recent_m:
        print("Шаблон повреждён: не найдены блоки пагинации/сайдбара")
        return
    middle = template[pagin_m.end() : recent_m.start()]
    tail = template[recent_m.end() :]

    page_to_file = {0: "blog.html"}
    for i in range(1, page_count):
        page_to_file[i] = f"blog{i}.html"

    for idx, articles in enumerate(pages):
        page_file = page_to_file[idx]
        body = [head, "\n"]
        for art in articles:
            body.append(reindent_block(art["block"]))
            body.append("\n")
        body.append(build_pagination(page_count, idx))
        body.append(middle)
        items = "\n".join(build_sidebar_item(art, page_to_file[get_page(art, pages)])
                          for art in all_articles)
        body.append(
            RECENT_START
            + "\n"
            + items
            + "\n"
            + "                </div>\n"
            + "                "
            + RECENT_END
        )
        body.append(tail)
        with open(page_file, "w", encoding="utf-8", newline="") as fh:
            fh.write("".join(body))
        print(f"{page_file}: {len(articles)} новостей")

    for f in page_files:
        if f not in page_to_file.values():
            os.remove(f)
            print(f"Удалена лишняя страница: {f}")


def get_page(art, pages):
    for i, page in enumerate(pages):
        if any(a["id"] == art["id"] for a in page):
            return i
    return 0


if __name__ == "__main__":
    main()