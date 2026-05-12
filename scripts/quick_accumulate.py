#!/usr/bin/env python3
"""快速累積新聞到100篇 - 直接從多RSS批次抓取"""
import hashlib
import json
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
CONTENT_DIR = REPO_DIR / "content" / "news"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

RSS_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("VentureBeat", "https://venturebeat.com/feed/"),
    ("CNBC Tech", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"),
    ("NYT Tech", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
    ("BBC Tech", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("Space.com", "https://www.space.com/feeds/all"),
    ("科技新報", "https://technews.tw/feed/"),
    ("Guardian Tech", "https://www.theguardian.com/technology/rss"),
    ("Engadget", "https://www.engadget.com/rss.xml"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Google AI", "https://news.google.com/rss/search?q=artificial+intelligence+OR+AI+chip&hl=en-US&gl=US&ceid=US:en"),
    ("Google Semi", "https://news.google.com/rss/search?q=semiconductor+OR+TSMC+OR+Nvidia&hl=en-US&gl=US&ceid=US:en"),
    ("Google EV", "https://news.google.com/rss/search?q=Tesla+OR+electric+vehicle+OR+EV&hl=en-US&gl=US&ceid=US:en"),
]

CATEGORIES = ["AI", "半導體", "電動車", "太空", "經濟", "科技", "地緣政治"]

def fetch_url(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except:
        return ""

def make_hash(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]

def get_category(title, summary):
    text = (title + " " + summary).lower()
    if any(k in text for k in ["artificial intelligence","ai ","llm","gpt","chatgpt","openai","anthropic","gemini","nvidia gpu","machine learning","deep learning"]):
        return "AI"
    if any(k in text for k in ["semiconductor","chip","tsmc","intel","amd","nvidia","qualcomm","fab","wafer","euv","asml","arm","gpu"]):
        return "半導體"
    if any(k in text for k in ["tesla","electric vehicle","ev ","battery","autonomous","self-driving","lithium","自駕","電動車"]):
        return "電動車"
    if any(k in text for k in ["spacex","rocket","satellite","starlink","nasa","space","orbital","太空","火箭"]):
        return "太空"
    if any(k in text for k in ["inflation","interest rate","federal reserve","gdp","recession","economy","tariff","trade war","fed","央行","利率","通膨"]):
        return "經濟"
    if any(k in text for k in ["china","taiwan","ukraine","russia","geopolitics","military","sanctions","nato","地緣政治","軍事"]):
        return "地緣政治"
    return "科技"

def parse_rss(xml_content, source_name):
    articles = []
    try:
        root = ET.fromstring(xml_content)
        items = root.findall(".//item") or root.findall(".//entry")
        for item in items[:8]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not link and item.findtext("guid"):
                link = item.findtext("guid")
            desc = (item.findtext("description") or item.findtext("summary") or item.findtext("content") or "").strip()
            desc = re.sub(r'<[^>]+>', '', desc)[:300]
            if title and link:
                articles.append({"title": title, "url": link, "source": source_name, "desc": desc})
    except Exception as e:
        pass
    return articles

def article_exists(url):
    existing = list(CONTENT_DIR.glob("*.md"))
    for f in existing:
        try:
            if url in f.read_text(encoding="utf-8"):
                return True
        except:
            pass
    return False

def save_article(article):
    h = make_hash(article["title"], article["url"])
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = CONTENT_DIR / f"{date_str}-{h}.md"
    
    if filename.exists():
        return False
    
    cat = get_category(article["title"], article["desc"])
    
    # Clean title
    title_en = re.sub(r'<[^>]+>', '', article["title"]).strip()
    title_en = re.sub(r'\s+', ' ', title_en)
    title_en = title_en.replace('"', '\\"')
    
    # Clean desc
    desc_en = re.sub(r'<[^>]+>', '', article["desc"])
    desc_en = re.sub(r'\s+', ' ', desc_en).strip()
    if len(desc_en) > 300:
        desc_en = desc_en[:300] + "..."
    desc_en = desc_en.replace('"', '\\"')
    desc_en_body = desc_en.replace('---', '')  # avoid breaking YAML

    # URL safe
    url_val = article["url"].replace('"', '\\"')

    content = f"""---
title: "{title_en}"
date: "{datetime.now().isoformat()}"
source: "{article['source']}"
category: "{cat}"
original_url: "{url_val}"
title_en: "{title_en}"
title_zh_tw: "[待翻譯]"
title_zh_cn: "[待翻譯]"
title_ja: "[待翻譯]"
summary_en: "{desc_en}"
summary_zh_tw: "[待翻譯]"
summary_zh_cn: "[待翻譯]"
summary_ja: "[待翻譯]"
draft: "false"
---

{desc_en_body}
"""
    filename.write_text(content, encoding="utf-8")
    return True

# ── MAIN ──────────────────────────────────────────────
current = len(list(CONTENT_DIR.glob("*.md")))
print(f"目前 {current} 篇文章，目標 100 篇")

added = 0
for source_name, rss_url in RSS_FEEDS:
    if len(list(CONTENT_DIR.glob("*.md"))) >= 100:
        break
    print(f"  抓取 {source_name}...", end=" ", flush=True)
    xml = fetch_url(rss_url)
    if not xml:
        print("失敗")
        continue
    articles = parse_rss(xml, source_name)
    print(f"{len(articles)} 篇")
    for art in articles:
        if len(list(CONTENT_DIR.glob("*.md"))) >= 100:
            break
        if article_exists(art["url"]):
            continue
        if save_article(art):
            added += 1
    time.sleep(0.5)

final = len(list(CONTENT_DIR.glob("*.md")))
print(f"\n完成！+{added} 篇，目前共 {final} 篇")
