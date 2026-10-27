# -*- coding: utf-8 -*-
"""Замена Cloudflare Email Obfuscation на обычные mailto:.
1) href="/cdn-cgi/l/email-protection#HEX" -> href="mailto:DECODED";
2) <span class="__cf_email__" data-cfemail="HEX">[email protected]</span> -> DECODED;
3) удаление инъекций скрипта email-decode.min.js.
"""
import glob
import io
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))

HREF_RE = re.compile(r'href="/cdn-cgi/l/email-protection#([0-9a-f]+)"')
SPAN_RE = re.compile(
    r'<span\s+class="__cf_email__"\s+data-cfemail="([0-9a-f]+)"\s*>'
    r'\[email&#160;protected\]</span\s*>')
SPAN_RE2 = re.compile(
    r'<span[^>]*class="__cf_email__"[^>]*data-cfemail="([0-9a-f]+)"[^>]*>'
    r'.*?</span>', re.S)
SCRIPT_RE = re.compile(
    r'[ \t]*<script\s+data-cfasync="false"\s+'
    r'src="/cdn-cgi/scripts/[^"]*email-decode\.min\.js"\s*></script>\r?\n?')


def decode(hexs):
    b = bytes.fromhex(hexs)
    key = b[0]
    return ''.join(chr(x ^ key) for x in b[1:])


changed = 0
for path in sorted(glob.glob(os.path.join(ROOT, '*.html')) +
                   glob.glob(os.path.join(ROOT, '*.shtml'))):
    name = os.path.basename(path)
    with io.open(path, encoding='utf-8', newline='') as f:
        data = f.read()
    orig = data
    n_href = len(HREF_RE.findall(data))
    n_span = len(SPAN_RE.findall(data)) + len(SPAN_RE2.findall(data))
    n_script = len(SCRIPT_RE.findall(data))

    data = HREF_RE.sub(lambda m: 'mailto:' + decode(m.group(1)), data)
    data = SPAN_RE.sub(lambda m: decode(m.group(1)), data)
    data = SPAN_RE2.sub(lambda m: decode(m.group(1)), data)
    data = SCRIPT_RE.sub('', data)

    if data != orig:
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(data)
        changed += 1
        print('%-16s href=%d span=%d script=%d' % (name, n_href, n_span, n_script))

print('changed:', changed)

# контроль: cdn-cgi не должен остаться нигде
left = []
for path in sorted(glob.glob(os.path.join(ROOT, '*.html')) +
                   glob.glob(os.path.join(ROOT, '*.shtml'))):
    with io.open(path, encoding='utf-8') as f:
        if 'cdn-cgi' in f.read():
            left.append(os.path.basename(path))
print('осталось cdn-cgi:', left if left else 'НЕТ')
