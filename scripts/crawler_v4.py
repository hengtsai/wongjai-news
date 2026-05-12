#!/usr/bin/env python3
"""
Wongjai News V4 — 全文抓取 + AI 批次翻譯
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
不使用 RSS，直接爬取各新聞網站首頁，收集文章連結，
再批次送給 AI sub-agent 進行抓取 + 翻譯。
"""
import json, hashlib, re, time, sys, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter, defaultdict

REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
CONTENT_DIR = REPO_DIR / "content" / "news"
STATE_FILE = REPO_DIR / "scripts" / "crawler_state_v4.json"
MAX_PER_CAT = 20
BATCH_TRANSLATE = 50  # articles per AI batch

CATEGORIES = {
    "AI": ["artificial intelligence", " artificial intelligence ", "ai ", " llm", "llm ", "gpt", "claude", "gemini",
           "machine learning", "deep learning", "openai", "anthropic",
           "generative ai", "chatbot", " ai ", "ai chip", "agi", "grok",
           "large language model", "neural network", "foundation model",
           "openai ", "anthropic ", "ai company"],
    "半導體": ["semiconductor", "tsmc", "intel", "amd", "nvidia", "qualcomm",
               "chip makers", "chip industry", "chip maker", "fab ", "foundry", "wafer", "euv", "asml", "arm holdings",
               "advanced node", "advanced packaging"],
    "電動車": ["electric vehicle", " electric vehicles ", " evs", " ev ", "ev makers", "tesla", "byd", "rivian", "lucid",
               "autonomous driving", "self-driving", "battery ", "lithium ",
               "ev adoption", "xpeng", "nio", "solid-state battery"],
    "太空": ["spacex", "rocket", "satellite", "starlink", "nasa", "artemis",
             "space exploration", "mars", "moon mission", "orbital", "launch",
             "blue origin"],
    "經濟": ["inflation", "interest rate", "federal reserve", "gdp", "recession",
             "economic growth", "economic policy", "tariff", "trade war", "fed ", "treasury",
             "wall street", "stock market", "central bank", "unemployment", "consumer price"],
    "科技": ["apple", "google", "microsoft", "amazon", "meta", "cloud computing",
             "cybersecurity", "data breach", "software", "privacy",
             "smartphone", "tech company", "tech giant"],
    "地緣政治": ["ukraine", "russia", "iran", "geopolitics", "military",
                 "defense spending", "sanctions", "nato", "taiwan", "south china sea",
                 "cross-strait", "pentagon"],
}

BLOCK_PATTERNS = [
    r'\d+%\s*off', r'\$\d+\s*off', 'promo code', 'coupon', 'best deal',
    'save up to', 'free shipping', 'free delivery', 'tested and reviewed',
    'product roundup', 'gift guide', 'best robot', 'best ski', 'best airpod',
    'Rating:', 'at Amazon', 'at Best Buy', 'at Walmart', 'buy now',
]

def gen_id(t, u):
    return hashlib.md5(f"{t}{u}".encode()).hexdigest()[:12]

def classify(title, text):
    txt = (title + " " + text).lower()
    scores = {}
    for cat, kws in CATEGORIES.items():
        s = sum(1 for kw in kws if kw.lower() in txt)
        if s > 0:
            scores[cat] = s
    return max(scores, key=scores.get) if scores else None

def is_ad(title, text=""):
    t = (title + " " + text).lower()
    for p in BLOCK_PATTERNS:
        if re.search(p, t, re.IGNORECASE):
            return True
    return False

# ── 收集各網站文章 URL 和標題 ──
def collect_all_articles():
    """使用 web_fetch 抓取各網站首頁，收集文章連結"""
    results = {}
    
    sources = {
        "TechCrunch": "https://techcrunch.com/",
        "Engadget": "https://www.engadget.com/",
        "CNBC": "https://www.cnbc.com/technology/",
        "DigiTimes": "https://www.digitimes.com/",
        "Reuters Tech": "https://www.reuters.com/technology/",
        "WSJ": "https://www.wsj.com/news/technology",
        "NYT Tech": "https://www.nytimes.com/section/technology",
    }
    
    print(f"\n📡 正在抓取 {len(sources)} 個網站首頁...")
    
    for name, url in sources.items():
        print(f"  📄 {name}: {url}")
    
    # Return the sources for the sub-agent to process
    return sources

def main():
    print("=" * 60)
    print("🚀 Wongjai News V4 — 全文抓取 + AI 批次翻譯")
    print("=" * 60)
    print("\n📋 新聞來源: TechCrunch, Engadget, CNBC, DigiTimes, Reuters, WSJ, NYT")
    print("📋 分類: AI / 半導體 / 電動車 / 太空 / 經濟 / 科技 / 地緣政治")
    print("📋 每分類上限: 20")
    print("📋 翻譯: 一次性 AI sub-agent 批次翻譯")
    
    # Step 1: Collect all source URLs
    sources = collect_all_articles()
    
    # Write source URLs to a file for the sub-agent
    sources_file = REPO_DIR / "team" / "shared" / "news_crawl_urls.json"
    sources_file.parent.mkdir(exist_ok=True)
    sources_file.write_text(json.dumps(sources, indent=2), encoding="utf-8")
    
    print(f"\n✅ 已寫入來源 URL 到 {sources_file}")
    print("\n🤖 現在需要 spawn 一個 AI sub-agent 來:")
    print("  1. 用 web_fetch 抓取每個網站首頁")
    print("  2. 找出所有新聞文章連結")
    print("  3. 逐篇抓取全文並提取摘要")
    print("  4. 分類 + 過濾廣告")
    print("  5. 一次性批次翻譯成 ZH-TW, ZH-CN, JA")
    print("  6. 生成 Hugo markdown 檔案")
    
    print("\n❗ 請 spawn 以下任務的 sub-agent:")
    
    task = f"""你是 Wongjai News V4 爬蟲執行器。

## 任務
抓取 7 個新聞網站，提取全文，分類，批次翻譯，生成 Hugo markdown。

## 來源網站
```json
{json.dumps(sources, indent=2)}
```

## 步驟

### Step 1: 抓取每個網站首頁
用 `web_fetch` 抓取每個網站的 HTML，找出所有新聞文章的標題和 URL。
從 HTML 中提取 <a> 標籤中具有有意義標題的連結。

### Step 2: 逐篇抓取全文
對每篇感興趣的文章（約每個網站 15 篇）：
1. 用 `web_fetch(url, extractMode="text", maxChars=5000)` 抓取全文
2. 從全文提取前 50 個英文單字作為摘要（summary_en）
3. 如果該文章 URL 已抓取過就跳過

### Step 3: 分類
每篇文章分類到以下之一：
- AI, 半導體, 電動車, 太空, 經濟, 科技, 地緣政治

### Step 4: 廣告過濾
移除包含以下關鍵字的內容：promo code, coupon, X% off, best deal, tested and reviewed, gift guide, Rating, at Amazon

### Step 5: 批次翻譯
將所有需要翻譯的文章一次送給我翻譯的 prompt。
格式 JSON：
```
{{
  "translations": [
    {{
      "id": 0,
      "title_zh_tw": "...",
      "title_zh_cn": "...", 
      "title_ja": "...",
      "summary_zh_tw": "...",
      "summary_zh_cn": "...",
      "summary_ja": "..."
    }}
  ]
}}
```

### Step 6: 生成 Hugo markdown
每分類最多 20 篇，超額的刪除舊的（按日期排序）。

檔案路徑: /Users/wongjai/.openclaw/workspace/wongjai-news/content/news/
檔名格式: YYYYMMDD-{id12}-{slug}.md

Front matter 格式：
```yaml
---
title: "Title"
date: "pub_date"
source: "SourceName"
category: "AI"
original_url: "url"
title_en: "Title"
title_zh_tw: "中文"
title_zh_cn: "中文"
title_ja: "日本語"
summary_en: "50-word summary"
summary_zh_tw: "中文摘要"
summary_zh_cn: "中文摘要"  
summary_ja: "日本語摘要"
draft: false
---

全文內容（前 1000 字）
```

## 注意
- 每個文章 title_en / summary_en 先用 AI 提取 50 字英文摘要
- 翻譯要求自然流暢，不要機器翻譯腔
- 公司名/產品名保留原文
- 先分類、過濾、去重，再翻譯，減少 token 浪費
- 所有操作完成後回報最終統計

開始執行！
"""
    
    print(f"\n{'='*60}")
    print("Sub-agent task 已準備完成（見上方）")
    print(f"{'='*60}")
    
    # Save task to file
    task_file = REPO_DIR / "team" / "shared" / "news_v4_task.txt"
    task_file.write_text(task, encoding="utf-8")
    print(f"Task 已儲存到 {task_file}")

if __name__ == "__main__":
    main()
