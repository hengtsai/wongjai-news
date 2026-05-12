#!/usr/bin/env python3
"""
batch_translate.py — 批次翻譯工具（最小 token 消耗）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
工作流程：
1. 讀取所有需要翻譯的 markdown 檔案（summary_zh_tw == "[待翻譯]"）
2. 只提取 title_en + summary_en（約 100 字/則）
3. 打包成一個 JSON 檔，供 sub-agent 一次翻譯
4. sub-agent 回傳翻譯 JSON，本程式解析後寫回 markdown

Token 成本：N 則新聞 × ~200 token = 約 10K（50 則）
對比 spawn 5 個 sub-agent：~200K → 節省 95%

作者: Wongjai ⚡
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

CONTENT_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news/content/news")


def find_articles_needing_translation() -> List[Dict]:
    """找出所有需要翻譯的文章（只提取必要欄位）"""
    articles = []
    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        
        # 解析 front matter
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            continue
        
        frontmatter = match.group(1)
        fields = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, _, val = line.partition(': ')
                fields[key.strip()] = val.strip().strip('"').strip("'")
        
        # 只收集需要翻譯的
        if fields.get("summary_zh_tw") == "[待翻譯]":
            articles.append({
                "file": str(md_file),
                "title_en": fields.get("title_en", ""),
                "summary_en": fields.get("summary_en", ""),
            })
    
    return articles


def write_translations(translations: Dict[str, Dict]):
    """將翻譯結果寫回 markdown 檔案"""
    for filepath, trans in translations.items():
        path = Path(filepath)
        if not path.exists():
            print(f"⚠️ 檔案不存在: {filepath}")
            continue
        
        content = path.read_text(encoding="utf-8")
        
        # 替換 6 個欄位
        for key in ["title_zh_tw", "title_zh_cn", "title_ja", "summary_zh_tw", "summary_zh_cn", "summary_ja"]:
            if key in trans:
                val = trans[key].replace('"', '\\"')
                # 替換 YAML 欄位
                pattern = rf'^{key}:.*$'
                content = re.sub(pattern, f'{key}: "{val}"', content, flags=re.MULTILINE)
        
        path.write_text(content, encoding="utf-8")
        print(f"✅ {path.name}")


if __name__ == "__main__":
    if "--find" in sys.argv:
        # 找出需要翻譯的文章
        articles = find_articles_needing_translation()
        print(json.dumps(articles, ensure_ascii=False, indent=2))
        print(f"\n共 {len(articles)} 則需要翻譯")
    
    elif "--apply" in sys.argv:
        # 從 stdin 讀取翻譯結果並寫入
        translations = json.load(sys.stdin)
        write_translations(translations)
        print(f"\n✅ 已寫入 {len(translations)} 則翻譯")
    
    else:
        print("用法:")
        print("  python3 batch_translate.py --find          # 找出需要翻譯的文章")
        print("  cat translations.json | python3 batch_translate.py --apply  # 寫入翻譯")
