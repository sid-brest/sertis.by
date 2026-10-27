# -*- coding: utf-8 -*-
"""Удаление раздела «Сертификация работ в строительстве»:
1) пункт меню confirmation.html#confirmation-4 во всех страницах;
2) секция confirmation-4 в confirmation.html + её CSS-селекторы;
3) секция «Сертификация работ в строительстве» в forms.html.
"""
import re
import glob
import io
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# 1) пункт меню во всех *.html
menu_re = re.compile(r'\s*<li>\s*<a href="confirmation\.html#confirmation-4".*?</li>', re.S)
menu_removed = 0
for path in glob.glob(os.path.join(ROOT, '*.html')):
    with io.open(path, encoding='utf-8') as f:
        text = f.read()
    new, n = menu_re.subn('', text)
    if n:
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(new)
        menu_removed += n
        print('menu -%d: %s' % (n, os.path.basename(path)))

# 2) секция confirmation-4 + CSS в confirmation.html
path = os.path.join(ROOT, 'confirmation.html')
with io.open(path, encoding='utf-8') as f:
    text = f.read()

start = text.index('<section id="confirmation-4"')
# включаем предшествующий комментарий-шапку секции
pre = text.rfind('<!-- =======', 0, start)
if pre != -1:
    start = pre
end = text.index('</section>', start) + len('</section>')
# хвостовой комментарий "End Breadcrumbs"
tail = re.match(r'\s*<!-- End Breadcrumbs -->', text[end:])
if tail:
    end += tail.end()
text = text[:start] + text[end:]

# CSS-селекторы #confirmation-4 (строки-селекторы в группах)
lines = text.split('\n')
kept = [ln for ln in lines if '#confirmation-4' not in ln]
print('css lines removed: %d' % (len(lines) - len(kept)))
text = '\n'.join(kept)

with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('confirmation.html: section removed')

# 3) секция «Сертификация работ в строительстве» в forms.html
path = os.path.join(ROOT, 'forms.html')
with io.open(path, encoding='utf-8') as f:
    text = f.read()
start = text.index('<p>Сертификация работ в строительстве</p>')
# начало секции: ближайший <section ...> перед заголовком
sec_start = text.rfind('<section', 0, start)
sec_end = text.index('</section>', start) + len('</section>')
# включаем предшествующий комментарий, если есть
pre = text.rfind('<!--', 0, sec_start)
if pre != -1 and text[pre:sec_start].strip().startswith('<!--'):
    # убеждаемся, что между комментарием и секцией только пробелы/переносы
    if not text[pre:sec_start].strip(' \t\r\n<!--'):
        sec_start = pre
text = text[:sec_start] + text[sec_end:]
with io.open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('forms.html: section removed')

print('TOTAL menu items removed: %d' % menu_removed)
