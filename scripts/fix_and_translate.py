#!/usr/bin/env python3
"""修復被翻譯腳本搞壞的 YAML front matter，並完成剩餘翻譯"""
import re, sys, time
from pathlib import Path
from deep_translator import GoogleTranslator

sys.stdout.reconfigure(line_buffering=True)

CONTENT_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news/content/news")

# ── Step 1: 修復所有被搞壞的 YAML 行 ──
# pattern: key: "translated_value"garbage
# fix to:  key: "translated_value"
print("\n[1/3] 修復損壞的 YAML front matter...")

fixed_count = 0
for md_file in sorted(CONTENT_DIR.glob("*.md")):
    content = md_file.read_text(encoding="utf-8")
    m = re.match(r'^---\n(.*?)\n---(.*)', content, re.DOTALL)
    if not m:
        continue
    
    fm = m.group(1)
    body = m.group(2)
    
    needs_fix = False
    
    for key in ["title_zh_tw", "title_zh_cn", "title_ja", 
                 "summary_zh_tw", "summary_zh_cn", "summary_ja"]:
        # 匹配 key: "value1"value2 的損壞形式
        pattern = rf'^({re.escape(key)}:\s*")([^"])(").+'
        if re.search(pattern, fm, re.MULTILINE):
            fm = re.sub(pattern, r'\1\2\3', fm, flags=re.MULTILINE)
            needs_fix = True
    
    if needs_fix:
        md_file.write_text(f"---\n{fm}\n---{body}", encoding="utf-8")
        fixed_count += 1

print(f"  修復了 {fixed_count} 個檔案")

# ── Step 2: 找出所有需要翻譯的文章 ──
print("\n[2/3] 找出需要翻譯的文章...")

t_zh_tw = GoogleTranslator(source='auto', target='zh-TW')
t_zh_cn = GoogleTranslator(source='auto', target='zh-CN')
t_ja = GoogleTranslator(source='auto', target='ja')

articles = []
for md_file in sorted(CONTENT_DIR.glob("*.md")):
    content = md_file.read_text(encoding="utf-8")
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        continue
    
    fm = m.group(1)
    fields = {}
    for line in fm.split('\n'):
        if ':' in line:
            key, _, val = line.partition(':')
            val = val.strip().strip('"').strip("'")
            fields[key.strip()] = val
    
    te = fields.get("title_en", "")
    se = fields.get("summary_en", "")
    tt = fields.get("title_zh_tw", "")
    
    if tt == "[待翻譯]" and te and se:
        articles.append((md_file, te, se))

print(f"  找到 {len(articles)} 篇需要翻譯")

# ── Step 3: 批次翻譯 ──
print("\n[3/3] 翻譯中...")

def try_translate(t, text, retries=3):
    for r in range(retries):
        try:
            result = t.translate(text)
            return result
        except Exception as e:
            if r < retries - 1:
                time.sleep(1)
            else:
                return None

ok = 0
err = 0
for idx, (md_file, te, se) in enumerate(articles, 1):
    try:
        content = md_file.read_text(encoding="utf-8")
        fm_m = re.match(r'^---\n(.*?)\n---(.*)', content, re.DOTALL)
        fm = fm_m.group(1)
        body = fm_m.group(2)
        
        # 翻譯 6 個欄位
        tt = try_translate(t_zh_tw, te)
        tc = try_translate(t_zh_cn, te)
        tj = try_translate(t_ja, te)
        st = try_translate(t_zh_tw, se)
        sc = try_translate(t_zh_cn, se)
        sj = try_translate(t_ja, se)
        
        # YAML 安全替換：使用逐行寫入方式
        lines = fm.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('title_zh_tw:'):
                if tt:
                    val = tt.replace('"', "'").replace('\n', ' ')
                    new_lines.append(f'title_zh_tw: "{val}"')
                else:
                    new_lines.append(line)
            elif line.startswith('title_zh_cn:'):
                if tc:
                    val = tc.replace('"', "'").replace('\n', ' ')
                    new_lines.append(f'title_zh_cn: "{val}"')
                else:
                    new_lines.append(line)
            elif line.startswith('title_ja:'):
                if tj:
                    val = tj.replace('"', "'").replace('\n', ' ')
                    new_lines.append(f'title_ja: "{val}"')
                else:
                    new_lines.append(line)
            elif line.startswith('summary_zh_tw:'):
                if st:
                    val = st.replace('"', "'").replace('\n', ' ')
                    new_lines.append(f'summary_zh_tw: "{val}"')
                else:
                    new_lines.append(line)
            elif line.startswith('summary_zh_cn:'):
                if sc:
                    val = sc.replace('"', "'").replace('\n', ' ')
                    new_lines.append(f'summary_zh_cn: "{val}"')
                else:
                    new_lines.append(line)
            elif line.startswith('summary_ja:'):
                if sj:
                    val = sj.replace('"', "'").replace('\n', ' ')
                    new_lines.append(f'summary_ja: "{val}"')
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        md_file.write_text("---\n" + "\n".join(new_lines) + "\n---" + body, encoding="utf-8")
        ok += 1
        
        if idx % 20 == 0 or idx == len(articles):
            print(f"  [{idx}/{len(articles)}] 已完成")
        
        time.sleep(0.8)  # rate limit
    except Exception as e:
        err += 1
        print(f"  ❌ {md_file.name}: {str(e)[:60]}")

print(f"\n✅ 翻譯完成！{ok} OK, {err} failed")
