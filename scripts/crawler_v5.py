#!/usr/bin/env python3
"""
Wongjai News V5 — RSS 爬蟲 → 全文抓取 → 分類 → news.json
"""
import json, hashlib, re, time, sys, os, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
import feedparser

# Content extraction
sys.path.insert(0, str(Path(__file__).parent))
from content_extractor import extract_content

REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
DATA_FILE = REPO_DIR / "static" / "data" / "news.json"
STATE_FILE = REPO_DIR / "scripts" / "crawler_state_v5.json"
MAX_AGE_HOURS = 48  # 只收 48 小時內的文章
MAX_TOTAL = 100

# 付費牆/反爬站：跳過 HTTP 抓取，直接用 RSS 摘要
PAYWALLED = {"wsj.com", "nytimes.com", "investing.com"}

# ===== RSS Sources =====
FEEDS = [
    # 半導體
    {"url": "https://www.anandtech.com/rss/", "cat": "chip", "so": "anandtech.com"},
    {"url": "https://www.tomshardware.com/feeds/all", "cat": "chip", "so": "tomshardware.com"},
    # AI
    {"url": "https://openai.com/blog/rss.xml", "cat": "ai", "so": "openai.com"},
    {"url": "https://www.jiqizhixin.com/rss", "cat": "ai", "so": "jiqizhixin.com"},
    # 財經
    {"url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "cat": "finance", "so": "wsj.com"},
    {"url": "https://www.investing.com/rss/news.rss", "cat": "finance", "so": "investing.com"},
    {"url": "https://finance.yahoo.com/news/rssindex", "cat": "finance", "so": "yahoo.finance"},
    {"url": "https://www.nytimes.com/services/xml/rss/nyt/HomePage.xml", "cat": "finance", "so": "nytimes.com"},
    # 台灣
    {"url": "https://technews.tw/feed/", "cat": "taiwan", "so": "technews.tw"},
    {"url": "https://www.inside.com.tw/feed", "cat": "taiwan", "so": "inside.com.tw"},
    # 太空
    {"url": "https://www.space.com/feeds/all", "cat": "space", "so": "space.com"},
    # 地緣政治
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "cat": "geo", "so": "bbc.com"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "cat": "geo", "so": "aljazeera.com"},
]

# Category display names
CAT_NAMES = {
    "tech":    {"zh_tw": "科技", "zh_cn": "科技", "en": "Tech", "ja": "テクノロジー", "ko": "기술"},
    "chip":    {"zh_tw": "半導體", "zh_cn": "半导体", "en": "Chips", "ja": "半導体", "ko": "반도체"},
    "ai":      {"zh_tw": "AI", "zh_cn": "AI", "en": "AI", "ja": "AI", "ko": "AI"},
    "finance": {"zh_tw": "財經", "zh_cn": "财经", "en": "Finance", "ja": "経済", "ko": "경제"},
    "taiwan":  {"zh_tw": "台灣", "zh_cn": "台湾", "en": "Taiwan", "ja": "台湾", "ko": "대만"},
    "ev":      {"zh_tw": "電動車", "zh_cn": "电动车", "en": "EV", "ja": "電気自動車", "ko": "전기차"},
    "space":   {"zh_tw": "太空", "zh_cn": "太空", "en": "Space", "ja": "宇宙", "ko": "우주"},
    "geo":     {"zh_tw": "地緣政治", "zh_cn": "地缘政治", "en": "Geopolitics", "ja": "地政学", "ko": "지정학"},
}

# ===== Utilities =====
def gen_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_ids": [], "last_run": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def load_existing():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except:
            pass
    return []

def clean_html(text):
    """Remove HTML tags and clean whitespace"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300]

def extract_brief(url):
    """Try to get article brief from the page"""
    try:
        r = subprocess.run(
            ['curl', '-sL', '--max-time', '8', '-A',
             'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
             url],
            capture_output=True, text=True, timeout=12
        )
        if r.returncode == 0 and r.stdout:
            # Try og:description first
            m = re.search(r'<meta\s+(?:property|name)="og:description"\s+content="([^"]{20,500})"', r.stdout)
            if m:
                return clean_html(m.group(1))
            # Try meta description
            m = re.search(r'<meta\s+name="description"\s+content="([^"]{20,500})"', r.stdout)
            if m:
                return clean_html(m.group(1))
            # Try first <p>
            m = re.search(r'<p[^>]*>([^<]{40,500})</p>', r.stdout)
            if m:
                return clean_html(m.group(1))
    except:
        pass
    return ""

# ===== Main Crawler =====
def crawl_feeds():
    """Crawl all RSS feeds and return new articles"""
    state = load_state()
    seen = set(state.get("seen_ids", []))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    new_articles = []

    for feed_info in FEEDS:
        url = feed_info["url"]
        cat = feed_info["cat"]
        source = feed_info["so"]
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:  # Max 15 per feed
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not title or not link:
                    continue

                aid = gen_id(title, link)
                if aid in seen:
                    continue

                # Parse date
                pub_time = None
                for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
                    tp = entry.get(date_field)
                    if tp:
                        try:
                            pub_time = datetime(*tp[:6], tzinfo=timezone.utc)
                        except:
                            pass
                        break

                if pub_time and pub_time < cutoff:
                    continue

                # Get description from RSS
                desc = ""
                if entry.get("summary"):
                    desc = clean_html(entry.summary)
                elif entry.get("description"):
                    desc = clean_html(entry.description)

                # Extract full article content (skip paywalled sites)
                content = ""
                content_source = "rss"
                if source not in PAYWALLED:
                    ext = extract_content(link, max_chars=3000)
                    if ext["success"]:
                        content = ext["content"]
                        content_source = "full"
                        if len(desc) < 30:
                            desc = content[:200]
                    elif len(desc) < 30:
                        desc = extract_brief(link) or desc
                # For paywalled sites, RSS summary is the best we can do
                if not content:
                    content = desc

                # Format time
                time_str = pub_time.isoformat() if pub_time else now.isoformat()
                rank = pub_time.timestamp() if pub_time else now.timestamp()

                article = {
                    "id": aid,
                    "cat": cat,
                    "title_en": title,
                    "title_zh": "",  # Will be translated
                    "title_zcn": "",
                    "title_ja": "",
                    "title_ko": "",
                    "s_en": desc[:200] if desc else "",
                    "s_zh": "",
                    "s_zcn": "",
                    "s_ja": "",
                    "s_ko": "",
                    "so": source,
                    "url": link,
                    "time": time_str,
                    "rank": rank,
                    "content": content,  # Full article text
                    "content_source": content_source,  # "full" or "rss"
                }
                new_articles.append(article)
                seen.add(aid)

        except Exception as e:
            print(f"  ⚠️ {source}: {e}", file=sys.stderr)

    # Update state
    # Keep only last 5000 seen IDs
    all_seen = list(seen)[-5000:]
    state["seen_ids"] = all_seen
    state["last_run"] = now.isoformat()
    save_state(state)

    return new_articles

def merge_articles(new, existing):
    """Merge new articles with existing, dedup, sort by time, limit"""
    seen_urls = set()
    merged = []

    for a in new + existing:
        url = a.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(a)

    # Sort by rank (timestamp) descending
    merged.sort(key=lambda x: x.get("rank", 0), reverse=True)

    # Limit
    return merged[:MAX_TOTAL]

def main():
    print("🕷️ Wongjai News V5 — RSS Crawler")
    print(f"   Sources: {len(FEEDS)} feeds")
    print()

    # Crawl
    print("📡 Crawling RSS feeds...")
    new_articles = crawl_feeds()
    print(f"   Found {len(new_articles)} new articles")

    # Merge with existing
    existing = load_existing()
    merged = merge_articles(new_articles, existing)
    print(f"   Total after merge: {len(merged)} articles")

    # Stats by category
    cats = defaultdict(int)
    for a in merged:
        cats[a.get("cat", "?")] += 1
    print("   Categories:", dict(cats))

    # Save
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"\n✅ Saved to {DATA_FILE}")
    print(f"   {len(merged)} articles")

    return merged

if __name__ == "__main__":
    main()
