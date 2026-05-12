#!/usr/bin/env python3
"""Translate article titles and summaries in existing markdown files."""
import re, time
from pathlib import Path
from datetime import datetime, timezone
from deep_translator import GoogleTranslator

CONTENT_DIR = Path('/Users/wongjai/.openclaw/workspace/wongjai-news/content/news')

t_zh = GoogleTranslator(source='auto', target='zh-TW')
t_cn = GoogleTranslator(source='auto', target='zh-CN')
t_ja = GoogleTranslator(source='auto', target='ja')

def safe_translate(translator, text):
    try:
        return translator.translate(text[:2000])
    except Exception as e:
        print(f"  [ERR] {e}")
        time.sleep(2)
        try:
            return translator.translate(text[:2000])
        except:
            return text

# Find files missing translations
files_to_translate = []
for f in sorted(CONTENT_DIR.glob('*.md')):
    text = f.read_text(encoding='utf-8')
    if 'title_zh_tw: ""' in text:
        files_to_translate.append(f)

print(f"Files needing translation: {len(files_to_translate)}")

done = 0
for fi, f in enumerate(files_to_translate):
    text = f.read_text(encoding='utf-8')
    
    # Extract title and summary
    m_title = re.search(r'title: "([^"]+)"', text)
    m_summary = re.search(r'summary_en: "([^"]*)"', text)
    
    if not m_title:
        continue
    
    title = m_title.group(1)
    summary = m_summary.group(1) if m_summary else ""
    
    # Translate
    if fi > 0 and fi % 10 == 0:
        print(f"  ... pausing ...")
        time.sleep(3)
    
    tt = safe_translate(t_zh, title)
    tc = safe_translate(t_cn, title)
    tj = safe_translate(t_ja, title)
    st = safe_translate(t_zh, summary) if summary else ""
    sc = safe_translate(t_cn, summary) if summary else ""
    sj = safe_translate(t_ja, summary) if summary else ""
    
    # Escape quotes
    tt = tt.replace('"', "'")
    tc = tc.replace('"', "'")
    tj = tj.replace('"', "'")
    st = st.replace('"', "'")
    sc = sc.replace('"', "'")
    sj = sj.replace('"', "'")
    
    # Replace empty translations with actual translations
    text = re.sub(r'(title_zh_tw: )"', r'\1"', text)
    text = re.sub(r'title_zh_tw: ""', f'title_zh_tw: "{tt}"', text)
    text = re.sub(r'title_zh_cn: ""', f'title_zh_cn: "{tc}"', text)
    text = re.sub(r'title_ja: ""', f'title_ja: "{tj}"', text)
    text = re.sub(r'summary_zh_tw: ""', f'summary_zh_tw: "{st}"', text)
    text = re.sub(r'summary_zh_cn: ""', f'summary_zh_cn: "{sc}"', text)
    text = re.sub(r'summary_ja: ""', f'summary_ja: "{sj}"', text)
    
    f.write_text(text, encoding='utf-8')
    done += 1
    
    if done % 5 == 0:
        print(f"  Translated {done}/{len(files_to_translate)}: {title[:50]}")
    time.sleep(0.5)

print(f"\nTranslated {done} files")
