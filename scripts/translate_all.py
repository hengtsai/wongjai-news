#!/usr/bin/env python3
"""Batch translate all articles with 4 languages via Google Translate"""
import re, sys, time
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

from deep_translator import GoogleTranslator

CONTENT_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news/content/news")

t_zh_tw = GoogleTranslator(source='auto', target='zh-TW')
t_zh_cn = GoogleTranslator(source='auto', target='zh-CN')
t_ja = GoogleTranslator(source='auto', target='ja')

def safe_quote(s):
    return s.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ').strip()

def translate_text(t, text, retries=3):
    for r in range(retries):
        try:
            return t.translate(text)
        except Exception as e:
            if r < retries - 1:
                time.sleep(2)
            else:
                raise e

articles = []
for md_file in sorted(CONTENT_DIR.glob("*.md")):
    content = md_file.read_text(encoding="utf-8")
    if '[待翻譯]' not in content:
        continue
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        continue
    fields = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, _, val = line.partition(': ')
            fields[key.strip()] = val.strip().strip('"').strip("'")
    if fields.get("title_en") and fields.get("summary_en"):
        articles.append((md_file,))

total = len(articles)
print(f"[INFO] Found {total} articles to translate")

ok, err = 0, 0
for idx, (md_file,) in enumerate(articles, 1):
    try:
        raw = md_file.read_text(encoding="utf-8")
        m = re.match(r'^---\n(.*?)\n---', raw, re.DOTALL)
        frontmatter = m.group(1)
        body = raw[m.end():]
        
        te = None
        for line in frontmatter.split('\n'):
            if line.startswith('title_en:'):
                te = line.split(':', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('summary_en:'):
                se = line.split(':', 1)[1].strip().strip('"').strip("'")
        
        if not te:
            err += 1
            print(f"[{idx}/{total}] SKIP no title_en: {md_file.name}")
            continue
        
        tt = safe_quote(translate_text(t_zh_tw, te))
        time.sleep(0.15)
        tc = safe_quote(translate_text(t_zh_cn, te))
        time.sleep(0.15)
        tj = safe_quote(translate_text(t_ja, te))
        time.sleep(0.15)
        st = safe_quote(translate_text(t_zh_tw, se))
        time.sleep(0.15)
        sc = safe_quote(translate_text(t_zh_cn, se))
        time.sleep(0.15)
        sj = safe_quote(translate_text(t_ja, se))
        time.sleep(0.15)
        
        def rep(text, key, val):
            return re.sub(rf'^({key}:\s*)"[^"]*"', rf'\1"{val}"', text, flags=re.MULTILINE)
        
        for k, v in [("title_zh_tw", tt), ("title_zh_cn", tc), ("title_ja", tj),
                      ("summary_zh_tw", st), ("summary_zh_cn", sc), ("summary_ja", sj)]:
            frontmatter = rep(frontmatter, k, v)
        
        md_file.write_text(f"---\n{frontmatter}\n---{body}", encoding="utf-8")
        ok += 1
        if idx % 10 == 0 or idx == total:
            print(f"[{idx}/{total}] OK={ok} ERR={err}")
    except Exception as e:
        err += 1
        print(f"  ❌ {md_file.name}: {str(e)[:80]}")
    time.sleep(0.1)

print(f"\n✅ Done! {ok} translated, {err} failed out of {total}")
