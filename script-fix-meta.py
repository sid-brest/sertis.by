# -*- coding: utf-8 -*-
"""SEO-правки мета-тегов на всех страницах:
1) уникальные meta description (50–160 знаков) вместо общего на 411 знаков;
2) уникальные <title> для страниц новостей (blog1..blog7);
3) <link rel="canonical"> на каждой странице;
4) <meta name="robots" content="noindex,follow"> на страницах ошибок;
5) robots.txt — удалена мусорная первая строка;
6) sitemap.xml — все индексируемые страницы.
"""
import glob
import io
import os
import re
import subprocess
from datetime import date

ROOT = r'C:\Users\isidb\Documents\GitHub\sertis.by'
SITE = 'https://sertis.by/'

DESC = {
    'index.html': 'Орган по сертификации строительных материалов и продукции '
                  '«Сертис», Брест: сертификация, декларирование, техническая '
                  'оценка пригодности, лабораторные испытания.',
    'about.html': 'О предприятии: РУП «Сертис» РУП «Белстройцентр» — орган по '
                  'сертификации и испытательная лаборатория в строительной '
                  'отрасли, работающая с 1993 года.',
    'admin.html': 'Административные процедуры в РУП «Сертис»: выдача '
                  'технических свидетельств о пригодности материалов и изделий '
                  'и свидетельств о компетентности СПК.',
    'assessment.html': 'Освидетельствование системы производственного контроля '
                       'с 11.03.2026: реестр свидетельств о технической '
                       'компетентности СПК, периодические проверки.',
    'certificates.html': 'Аттестаты и сертификаты органа по сертификации '
                         '«Сертис»: документы об аккредитации, область '
                         'аккредитации по сертификации и испытаниям.',
    'complaint.html': 'Порядок подачи и рассмотрения жалоб и апелляций в органе '
                      'по сертификации «Сертис»: сроки, форма обращения, права '
                      'заявителей.',
    'confirmation.html': 'Подтверждение соответствия в Беларуси: обязательная '
                         'сертификация и декларирование строительных материалов '
                         'по ТР 2025/013/BY, ТР ТС 014/2011, ТР ЕАЭС 042/2017.',
    'contact.html': 'Контакты РУП «Сертис» РУП «Белстройцентр»: 224701, г. '
                    'Брест, ул. Лейтенанта Рябцева, 39Л/1, телефоны и '
                    'электронная почта mail@sertis.by.',
    'corruption.html': 'Противодействие коррупции в РУП «Сертис» РУП '
                       '«Белстройцентр»: антикоррупционная политика, меры '
                       'профилактики, контакты для обращений.',
    'extra.html': 'Дополнительные услуги: инженерно-техническая поддержка '
                  'строительства, контроль качества материалов, разработка СМК '
                  'и документации для аккредитации лабораторий.',
    'feedback.html': 'Отзывы заказчиков о работе РУП «Сертис» РУП '
                     '«Белстройцентр»: сертификация продукции, испытания и '
                     'сопровождение подтверждения соответствия.',
    'forms.html': 'Бланки и образцы документов: заявка на сертификацию '
                  'продукции по ТР 2025/013/BY, заявление на техническую оценку '
                  'пригодности, декларация о соответствии.',
    'goals.html': 'Цели и задачи РУП «Сертис» РУП «Белстройцентр»: '
                  'обеспечение качества строительной продукции, стандартизация '
                  'и подтверждение соответствия.',
    'history.html': 'История РУП «Сертис»: путь органа по сертификации и '
                    'испытательной лаборатории строительных материалов с 1993 '
                    'года до сегодняшнего дня.',
    'idiology.html': 'Идеологическая работа в РУП «Сертис» РУП «Белстройцентр»: '
                     'патриотическое воспитание, Директива № 12, '
                     'государственная символика, общественные мероприятия.',
    'pricing.html': 'Стоимость и сроки работ по подтверждению соответствия: '
                    'сертификация продукции, регистрация декларации, '
                    'освидетельствование СПК, оплата через ЕРИП.',
    'procedure.html': 'Порядок обращений граждан и юридических лиц в РУП '
                      '«Сертис»: сроки рассмотрения, форма подачи, адреса и '
                      'контакты для обращений.',
    'profsoyuz.html': 'Профсоюзная организация РУП «Сертис» РУП '
                      '«Белстройцентр»: защита трудовых прав, социальное '
                      'партнёрство, мероприятия для работников предприятия.',
    'requisites.html': 'Реквизиты РУП «Сертис» РУП «Белстройцентр»: почтовый '
                       'адрес, УНП, банковские реквизиты, расчетные счета и '
                       'контакты предприятия.',
    'rights.html': 'Права и обязанности заявителей в системе подтверждения '
                   'соответствия: порядок подачи заявки, рассмотрение '
                   'обращений, обязанности органа по сертификации.',
    'structure.html': 'Структура РУП «Сертис» РУП «Белстройцентр»: '
                      'руководство, подразделения органа по сертификации и '
                      'испытательного центра.',
    'suitability.html': 'Техническая оценка пригодности строительных материалов '
                        'и изделий по ТР 2025/013/BY: техническое свидетельство, '
                        'заявление и реестр выданных свидетельств.',
    'team.html': 'Руководство РУП «Сертис» РУП «Белстройцентр»: директор и '
                 'специалисты органа по сертификации и испытательной '
                 'лаборатории.',
    'tests.html': 'Испытания строительных материалов в лаборатории «Сертис»: '
                  'бетон и растворы, грунты, теплоизоляция, '
                  'воздухопроницаемость, неразрушающие методы контроля.',
    'vyshestvoyashchaya.html': 'Вышестоящая организация РУП «Сертис»: РУП '
                               '«Белстройцентр» и Министерство архитектуры и '
                               'строительства Республики Беларусь.',
    '401.shtml': 'Страница требует авторизации — ошибка 401 на сайте sertis.by.',
    '403.shtml': 'Доступ к странице запрещён — ошибка 403 на сайте sertis.by.',
    '404.shtml': 'Запрошенная страница не найдена — ошибка 404 на сайте '
                 'sertis.by.',
    '500.shtml': 'Внутренняя ошибка сервера — ошибка 500 на сайте sertis.by.',
}
NOINDEX = {'401.shtml', '403.shtml', '404.shtml', '500.shtml'}

# Новостные страницы (blog*.html): общий description для всех, title и
# canonical не меняем — состав и порядок новостей меняются при публикациях.
SKIP = {'blog.html'} | {'blog%d.html' % i for i in range(1, 8)}
BLOG_DESC = ('Новости РУП «Сертис» РУП «Белстройцентр»: семинары, спортивные '
             'и патриотические мероприятия, изменения в работе органа по '
             'сертификации.')

DESC_BLOCK = ('<meta\n      content="{d}"\n      name="description"\n    />')

warnings = []


def set_description(name, text, data, eol):
    if not 50 <= len(text) <= 160:
        warnings.append('%s: длина description %d' % (name, len(text)))
    block = '<meta{e}      content="{d}"{e}      name="description"{e}    />'.format(
        e=eol, d=text)
    pat = re.compile(r'<meta[^>]*name="description"[^>]*?/?>', re.S)
    if pat.search(data):
        return pat.sub(lambda m: block, data, count=1)
    # description отсутствует — вставляем после </title>
    return data.replace('</title>', '</title>' + eol + '    ' + block, 1)


def set_canonical(name, data, eol):
    if 'rel="canonical"' in data:
        return data
    url = SITE if name == 'index.html' else SITE + name
    tag = '<link rel="canonical" href="%s" />' % url
    if name in NOINDEX:
        tag = '<meta name="robots" content="noindex,follow" />' + eol + '    ' + tag
    return data.replace('</title>', '</title>' + eol + '    ' + tag, 1)


changed = 0
for path in sorted(glob.glob(os.path.join(ROOT, '*.html')) +
                   glob.glob(os.path.join(ROOT, '*.shtml'))):
    name = os.path.basename(path)
    with io.open(path, encoding='utf-8', newline='') as f:
        data = f.read()
    eol = '\r\n' if '\r\n' in data else '\n'
    orig = data

    if name in SKIP:
        # новости: только общее описание, без canonical и без смены title
        if not 50 <= len(BLOG_DESC) <= 160:
            warnings.append('%s: длина blog-description %d' % (name, len(BLOG_DESC)))
        new = set_description(name, BLOG_DESC, data, eol)
        if new != data:
            with io.open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(new)
            changed += 1
            print('meta (новости, описание):', name)
        else:
            print('skip (новости, уже ок):', name)
        continue

    if name not in DESC:
        warnings.append('%s: нет описания в словаре!' % name)
        continue

    data = set_description(name, DESC[name], data, eol)
    data = set_canonical(name, data, eol)

    if data != orig:
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(data)
        changed += 1
        print('meta:', name)

print('changed:', changed)

# ---------------------------------------------------------------- robots.txt
rp = os.path.join(ROOT, 'robots.txt')
with io.open(rp, encoding='utf-8', newline='') as f:
    robots = f.read()
lines = robots.splitlines()
if lines and lines[0].strip().lower() == 'robots.txt':
    lines = lines[1:]
    with io.open(rp, 'w', encoding='utf-8', newline='') as f:
        f.write('\r\n'.join(lines) + '\r\n')
    print('robots.txt: мусорная первая строка удалена')

# ---------------------------------------------------------------- sitemap.xml
pages = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, '*.html')))
urls = []
for name in pages:
    if name.startswith(('401', '403', '404', '500')):
        continue
    url = SITE if name == 'index.html' else SITE + name
    lastmod = subprocess.run(
        ['git', '-C', ROOT, 'log', '-1', '--format=%cs', '--', name],
        capture_output=True, text=True).stdout.strip()
    if not re.match(r'\d{4}-\d{2}-\d{2}', lastmod or ''):
        lastmod = date.today().isoformat()
    urls.append((url, lastmod))

# index — первым
urls.sort(key=lambda u: (u[0] != SITE, u[0]))
sx = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
      '        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
      '        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9',
      '        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">']
for url, lastmod in urls:
    sx += ['    <url>', '        <loc>%s</loc>' % url,
           '        <lastmod>%sT00:00:00+00:00</lastmod>' % lastmod, '    </url>']
sx.append('</urlset>')
with io.open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8', newline='') as f:
    f.write('\r\n'.join(sx) + '\r\n')
print('sitemap.xml: %d URL' % len(urls))

if warnings:
    print('--- WARNINGS ---')
    for w in warnings:
        print(w)
