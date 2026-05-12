#!/usr/bin/env python3
"""
Complete translation for all 120+ news articles
Title: EN -> ZH-TW, ZH-CN, JA
Summary: EN -> ZH-TW, ZH-CN, JA
Uses Google Translate in small batches to avoid rate limiting.
"""
import re, time, sys
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

from deep_translator import GoogleTranslator

CONTENT_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news/content/news")

# We need to detect: is a field already properly translated or still English?
def is_english_heavy(s):
    """Heuristic: if >60% ASCII chars, it's still mostly English."""
    if not s:
        return True
    ascii_count = sum(1 for c in s if ord(c) < 128)
    return ascii_count / len(s) > 0.6

# Translation helper with retry
def translate(t, text, retries=3):
    if not text or len(text.strip()) < 2:
        return text
    for r in range(retries):
        try:
            result = t.translate(text[:4000])  # truncate to avoid limits
            return result or text
        except Exception:
            if r < retries - 1:
                time.sleep(2)
            else:
                return text

def needs_trans(english_text, translated_val):
    """True if translated_val is still English/garbage and needs re-translation."""
    if not translated_val or translated_val == "[待翻譯]":
        return True
    if is_english_heavy(translated_val.strip()):
        return True
    return False

# Prepare translators
t_zh_tw = GoogleTranslator(source='auto', target='zh-TW')
t_zh_cn = GoogleTranslator(source='auto', target='zh-CN')
t_ja = GoogleTranslator(source='auto', target='ja')

def process_file(md_file: Path):
    content = md_file.read_text(encoding="utf-8")
    m = re.match(r'^---\n(.*?)\n---(.*)', content, re.DOTALL)
    if not m:
        return False, "no frontmatter"
    
    fm_lines = m.group(1).split('\n')
    body = m.group(2)
    
    fields = {}
    line_idx = {}
    for i, line in enumerate(fm_lines):
        if ':' in line:
            key = line.split(':')[0]
            fields[key] = line
            line_idx[key] = i
    
    te = fields.get("title_en", "")
    se = fields.get("summary_en", "")
    
    # Remove surrounding quotes if present
    for k in ["title_en", "summary_en"]:
        v = fields.get(k, "")
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        if k == "title_en":
            te = v
        elif k == "summary_en":
            se = v
    
    if not te:
        return False, "no title_en"
    
    # Check which fields need translation
    need_title = False
    need_summary = False
    
    tt = fields.get("title_zh_tw", "")
    if tt.startswith('"') and tt.endswith('"'):
        tt = tt[2:-1]  # Remove key: " and "
    if needs_trans(te, tt):
        need_title = True
    
    st = fields.get("summary_zh_tw", "")
    if st.startswith('"') and st.endswith('"'):
        st = st[2:-1]
    if needs_trans(se, st):
        need_summary = True
    
    if not need_title and not need_summary:
        return False, "already translated"
    
    # Translate titles
    if need_title:
        tt_new = translate(t_zh_tw, te)
        tc_new = translate(t_zh_cn, te)
        time.sleep(0.1)
        tj_new = translate(t_ja, te)
        time.sleep(0.1)
        
        for k, v in [
            ("title_zh_tw", tt_new.replace('"', "'").replace('\n', ' ').replace('\r', ' ')),
            ("title_zh_cn", tc_new.replace('"', "'").replace('\n', ' ').replace('\r', ' ')),
            ("title_ja", tj_new.replace('"', "'").replace('\n', ' ').replace('\r', ' ')),
        ]:
            if k in line_idx:
                fm_lines[line_idx[k]] = f'{k}: "{v}"'
            else:
                fm_lines.append(f'{k}: "{v}"')
    
    # Translate summaries
    if need_summary:
        st_new = translate(t_zh_tw, se)
        time.sleep(0.1)
        sc_new = translate(t_zh_cn, se)
        time.sleep(0.1)
        sj_new = translate(t_ja, se)
        time.sleep(0.1)
        
        for k, v in [
            ("summary_zh_tw", st_new.replace('"', "'").replace('\n', ' ').replace('\r', ' ')),
            ("summary_zh_cn", sc_new.replace('"', "'").replace('\n', ' ').replace('\r', ' ')),
            ("summary_ja", sj_new.replace('"', "'").replace('\n', ' ').replace('\r', ' ')),
        ]:
            if k in line_idx:
                fm_lines[line_idx[k]] = f'{k}: "{v}"'
            else:
                fm_lines.append(f'{k}: "{v}"')
    
    new_fm = '\n'.join(fm_lines)
    md_file.write_text(f"---\n{new_fm}\n---{body}", encoding="utf-8")
    return True, te[:50]

# Process all files
articles = sorted(CONTENT_DIR.glob("*.md"))
ok, skip, fail = 0, 0, 0

for i, f in enumerate(articles, 1):
    try:
        result, msg = process_file(f)
        if result:
            ok += 1
            if ok % 20 == 0:
                print(f"  [{i}/{len(articles)}] OK={ok}")
            time.sleep(0.6)  # Rate limit
        else:
            skip += 1
    except Exception as e:
        fail += 1
        if fail <= 5:
            print(f"  ❌ {f.name}: {str(e)[:70]}")

print(f"\n✅ Done! {ok} translated, {skip} skipped (already good), {fail} failed")
