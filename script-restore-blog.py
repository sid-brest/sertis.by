# -*- coding: utf-8 -*-
"""Восстановление blog*.html из HEAD и повторное применение ТОЛЬКО нужных правок:
1) удаление пункта меню «Сертификация работ в строительстве» (confirmation-4);
2) переименование «Оценка системы…котроля» -> «Освидетельствование…контроля»;
3) пункт меню «Административные процедуры» после «Оценка пригодности»;
4) исправление кавычек в blog3 («Кинотеатр «Александрия»»);
5) общий meta description (без canonical, title не меняем).
Файлы предварительно восстанавливаются из HEAD (git checkout).
"""
import io
import os
import re
import subprocess

ROOT = r'C:\Users\isidb\Documents\GitHub\sertis.by'
BLOGS = ['blog.html'] + ['blog%d.html' % i for i in range(1, 8)]
BLOG_DESC = ('Новости РУП «Сертис» РУП «Белстройцентр»: семинары, спортивные '
             'и патриотические мероприятия, изменения в работе органа по '
             'сертификации.')

# 1) восстановление из HEAD
subprocess.run(['git', '-C', ROOT, 'checkout', 'HEAD', '--'] + BLOGS, check=True)
print('restored from HEAD:', ', '.join(BLOGS))

menu_re = re.compile(r'\s*<li>\s*<a href="confirmation\.html#confirmation-4".*?</li>', re.S)
rename_re = re.compile(
    r'>Оценка системы<br />производственного<br />котроля</a')
RENAMED = '>Освидетельствование системы<br />производственного<br />контроля</a>'
admin_pat = re.compile(r'([ \t]*)<li><a href="suitability\.html">Оценка пригодности</a></li>')
admin_new = '<li><a href="admin.html">Административные процедуры</a></li>'

for name in BLOGS:
    path = os.path.join(ROOT, name)
    with io.open(path, encoding='utf-8', newline='') as f:
        data = f.read()
    eol = '\r\n' if '\r\n' in data else '\n'
    orig = data

    data, n1 = menu_re.subn('', data)
    data, n2 = rename_re.subn(RENAMED, data)
    n3 = 0
    m = admin_pat.search(data)
    if m and 'href="admin.html"' not in data:
        indent = m.group(1)
        data = data[:m.end()] + eol + indent + admin_new + data[m.end():]
        n3 = 1

    # 4) кавычки blog3
    n4 = 0
    if name == 'blog3.html':
        for a, b in (
            ('>Гала-концерт «Кинотеатр «Александрия»</a',
             '>Гала-концерт «Кинотеатр «Александрия»»</a'),
            ('гала-концерт «Кинотеатр «Александрия». Концерт ежегодно',
             'гала-концерт «Кинотеатр «Александрия»». Концерт ежегодно'),
        ):
            if a in data:
                data = data.replace(a, b, 1)
                n4 += 1

    # 5) общий description
    n5 = 0
    pat = re.compile(r'<meta[^>]*name="description"[^>]*?/?>', re.S)
    if not 50 <= len(BLOG_DESC) <= 160:
        raise SystemExit('BLOG_DESC длина %d вне 50..160' % len(BLOG_DESC))
    block = '<meta{e}      content="{d}"{e}      name="description"{e}    />'.format(
        e=eol, d=BLOG_DESC)
    if pat.search(data):
        data = pat.sub(lambda m: block, data, count=1)
        n5 = 1

    if data != orig:
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(data)
    print('%-12s menu-%d rename-%d admin-%d quotes-%d desc-%d' %
          (name, n1, n2, n3, n4, n5))

print('done')
