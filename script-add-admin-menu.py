# -*- coding: utf-8 -*-
"""Добавляет пункт меню «Административные процедуры» (admin.html)
в раздел «Услуги» сразу после «Оценка пригодности» — во всех *.html.
Чтение/запись с сохранением окончаний строк (CRLF/LF)."""
import glob
import io
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'([ \t]*)<li><a href="suitability\.html">Оценка пригодности</a></li>')
NEW = '<li><a href="admin.html">Административные процедуры</a></li>'

added = 0
for path in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
    with io.open(path, encoding='utf-8', newline='') as f:
        data = f.read()
    if 'href="admin.html"' in data:
        print('skip (already):', os.path.basename(path))
        continue
    m = PAT.search(data)
    if not m:
        print('NOT FOUND:', os.path.basename(path))
        continue
    indent = m.group(1)
    eol = '\r\n' if '\r\n' in data else '\n'
    ins = m.group(0) + eol + indent + NEW
    data = data[:m.start()] + ins + data[m.end():]
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(data)
    added += 1

print('menu items added: %d' % added)
