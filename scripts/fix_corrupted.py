#!/usr/bin/env python3
"""修復翻譯腳本造成的 YAML 損壞：title_zh_tw: "翻譯內容"原文殘留"""
import re
from pathlib import Path

CONTENT_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news/content/news")

fixed = 0
for md_file in sorted(CONTENT_DIR.glob("*.md")):
    content = md_file.read_text(encoding="utf-8")
    m = re.match(r'^---\n(.*?)\n---(.*)', content, re.DOTALL)
    if not m:
        continue
    
    fm = m.group(1)
    body = m.group(2)
    original_fm = fm
    
    for key in ["title_zh_tw", "title_zh_cn", "title_ja", 
                "summary_zh_tw", "summary_zh_cn", "summary_ja"]:
        # 找 key: "..."...
        # 問題：translate_all.py 的正則只替換第一個 "..." 但沒吃掉整行
        # 所以變成 key: "翻譯內容"原文殘留
        pattern = rf'^({re.escape(key)}:\s*)"([^"]+)"\s*(.+)$'
        new_fm = re.sub(pattern, rf'\1"\2"', fm, flags=re.MULTILINE)
        if new_fm != fm:
            fm = new_fm
    
    if fm != original_fm:
        md_file.write_text(f"---\n{fm}\n---{body}", encoding="utf-8")
        fixed += 1

print(f"✅ 修復了 {fixed} 個檔案")
