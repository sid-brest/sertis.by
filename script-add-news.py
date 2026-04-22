#!/usr/bin/env python3
"""
Скрипт для добавления новостей на страницы блога сайта Сертис.
Использование: python add_news.py
"""

import os
import re
import glob
from datetime import datetime

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def format_date_ru(date_str):
    """Преобразует 'YYYY-MM-DD' в '6 апреля 2026'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day} {MONTHS_RU[dt.month]} {dt.year}"


def get_next_blog_number(blog_html_path):
    """Находит максимальный номер новости в blog.html."""
    with open(blog_html_path, "r", encoding="utf-8") as f:
        content = f.read()
    numbers = [int(n) for n in re.findall(r'id="blog-(\d+)"', content)]
    return max(numbers) + 1 if numbers else 1


def build_article_html(num, title, date_attr, date_ru, content_html):
    """Генерирует HTML блока <article>."""
    return f'''              <article class="entry" id="blog-{num}">
                <div class="entry-img">
                  <img
                    src="assets/img/blog/blog-{num}.webp"
                    alt=""
                    class="img-fluid"
                  />
                </div>
                <h2 class="entry-title">
                  <a href="javascript:void(0)"
                    >{title}</a
                  >
                </h2>
                <div class="entry-meta">
                  <ul>
                    <li class="d-flex align-items-center">
                      <i class="bi bi-person"></i>
                      <a href="javascript:void(0)">Сертис</a>
                    </li>
                    <li class="d-flex align-items-center">
                      <i class="bi bi-clock"></i>
                      <a href="javascript:void(0)"
                        ><time datetime="{date_attr}">{date_ru}</time></a
                      >
                    </li>
                  </ul>
                </div>
                <div class="entry-content">
                  {content_html}
                </div>
              </article>
              <!-- End blog entry -->'''


def build_sidebar_item_html(num, title, date_attr, date_ru, page):
    """Генерирует HTML пункта sidebar."""
    return f'''                  <div class="post-item clearfix">
                    <img src="assets/img/blog/blog-{num}.webp" alt="" />
                    <h4>
                      <a href="{page}#blog-{num}"
                        >{title}</a
                      >
                    </h4>
                    <time datetime="{date_attr}">{date_ru}</time>
                  </div>'''


def insert_article_into_blog(content, article_html):
    """Вставляет новую статью перед первой существующей статьёй."""
    marker = '<article class="entry"'
    idx = content.find(marker)
    if idx == -1:
        print("  ПРЕДУПРЕЖДЕНИЕ: место для вставки статьи не найдено!")
        return content
    return content[:idx] + article_html + "\n              " + content[idx:]


def insert_sidebar_item(content, sidebar_item_html):
    """Вставляет новый пункт sidebar перед первым существующим пунктом."""
    sidebar_start = content.find('<div class="sidebar-item recent-posts">')
    if sidebar_start == -1:
        print("  ПРЕДУПРЕЖДЕНИЕ: sidebar recent-posts не найден!")
        return content
    marker = '<div class="post-item clearfix">'
    idx = content.find(marker, sidebar_start)
    if idx == -1:
        print("  ПРЕДУПРЕЖДЕНИЕ: post-item не найден в sidebar!")
        return content
    return content[:idx] + sidebar_item_html + "\n" + content[idx:]


def get_blog_files(directory="."):
    """Возвращает отсортированный список blog*.html файлов."""
    files = glob.glob(os.path.join(directory, "blog*.html"))
    files.sort()
    return files


def multiline_input(prompt):
    """Принимает многострочный ввод до пустой строки."""
    print(prompt)
    print("(Введите текст, каждый абзац с новой строки, завершите пустой строкой)")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  Добавление новости на сайт Сертис")
    print("=" * 60)

    directory = input("\nПуть к папке с blog*.html файлами [.]: ").strip() or "."

    blog_files = get_blog_files(directory)
    if not blog_files:
        print(f"ОШИБКА: файлы blog*.html не найдены в '{directory}'")
        return

    print(f"Найдены файлы: {[os.path.basename(f) for f in blog_files]}")

    main_blog = os.path.join(directory, "blog.html")
    if not os.path.exists(main_blog):
        print("ОШИБКА: blog.html не найден!")
        return

    next_num = get_next_blog_number(main_blog)
    print(f"\nСледующий номер новости: blog-{next_num}")

    print("\n--- Введите данные новости ---")
    title = input("Заголовок новости: ").strip()

    date_str = input("Дата публикации (YYYY-MM-DD, например 2026-04-22): ").strip()
    try:
        date_ru = format_date_ru(date_str)
    except ValueError:
        print("ОШИБКА: неверный формат даты. Используйте YYYY-MM-DD")
        return
    print(f"Дата в русском формате: {date_ru}")

    content_text = multiline_input("\nТекст новости:")
    paragraphs = [p.strip() for p in content_text.split("\n") if p.strip()]
    content_html = "<br /><br />\n                  ".join(paragraphs)

    article_html = build_article_html(next_num, title, date_str, date_ru, content_html)
    sidebar_item_html = build_sidebar_item_html(
        next_num, title, date_str, date_ru, "blog.html"
    )

    print("\n--- Обновление файлов ---")

    # blog.html — вставляем статью и пункт sidebar
    with open(main_blog, "r", encoding="utf-8") as f:
        blog_content = f.read()
    blog_content = insert_article_into_blog(blog_content, article_html)
    blog_content = insert_sidebar_item(blog_content, sidebar_item_html)
    with open(main_blog, "w", encoding="utf-8") as f:
        f.write(blog_content)
    print(f"  ✓ blog.html — добавлена статья и пункт sidebar")

    # Остальные blog*.html — только пункт sidebar
    for filepath in blog_files:
        if os.path.basename(filepath) == "blog.html":
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        content = insert_sidebar_item(content, sidebar_item_html)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ {os.path.basename(filepath)} — пункт sidebar добавлен")

    print("\n" + "=" * 60)
    print(f"  Готово! Новость blog-{next_num} добавлена.")
    print(f"  Не забудьте добавить изображение:")
    print(f"  assets/img/blog/blog-{next_num}.webp")
    print("=" * 60)


if __name__ == "__main__":
    main()
