#!/usr/bin/env python3
"""
Wongjai News 爬蟲 V3 Fast — 不抓全文，使用 RSS description 作為摘要
速度快，不會 timeout
"""
import hashlib, json, re, sys, time, urllib.request, urllib.error, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsCrawlerV3Fast")

# ── Paths ──
REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
CONTENT_DIR = REPO_DIR / "content" / "news"
STATE_FILE = REPO_DIR / "scripts" / "crawler_state_v3.json"
MAX_PER_CAT = 20

# ── Categories ──
CATEGORIES = {
    "AI": ["artificial intelligence", " ai ", "llm", "gpt", "claude", "gemini",
           "machine learning", "deep learning", "openai", "anthropic",
           "generative ai", "chatbot", "transformer ", "ai chip", "agi", "grok",
           "large language model", "neural network"],
    "半導體": ["semiconductor", "tsmc", "intel", "amd", "nvidia", "qualcomm",
               "chip ", "fab ", "foundry", "wafer", "euv", "asml", "arm Holdings",
               "3nm", "2nm", "先进製程", "co-wo", "hbm"],
    "電動車": ["electric vehicle", " ev ", "evs", "tesla", "byd", "rivian", "lucid",
               "autonomous", "self-driving", "battery ", "lithium ",
               "charging station", "ev adoption", "xpeng", "nio", "solid-state"],
    "太空": ["spacex", "rocket", "satellite", "starlink", "nasa", "artemis",
             "space exploration", "mars", "moon mission", "orbital", "launch",
             "blue origin", "boeing starliner"],
    "經濟": ["inflation", "interest rate", "federal reserve", "gdp", "recession",
             "econom", "tariff", "trade war", "fed ", "treasury",
             "wall street", "stock market", "central bank"],
    "科技": ["apple", "google", "microsoft", "amazon", "meta", "cloud computing",
             "cybersecurity", "data breach", "software update", "privacy",
             "operating system", "smartphone", "tech company"],
    "地緣政治": ["ukraine", "russia", "iran", "geopolitics", "military",
                 "defense ", "sanctions", "nato", "taiwan", "south china sea",
                 "cross-strait", "pentagon", "arms deal"],
}

# AD/PROMO blacklist
BLOCK_PATTERNS = [
    r'\d+%\s+off', r'\$\d+\s+off', 'promo code', 'coupon', 'best deal',
    'save up to', 'free shipping', 'free delivery', 'tested and reviewed',
    'hands-on review', 'product roundup', 'gift guide', 'holiday gift',
    'best robot', 'best ski', 'best airpod', 'best ipad', 'best apple watch',
    'best headphone', 'promo codes', 'coupon code',
    'home depot', 'dyson promo', 'booking.com', 'doordash', 'chewy promo',
    'skullcandy', 'samsung promo', 'target deal',
]

# ── Sources ──
NEWS_SOURCES = {
    "TechCrunch":     "https://techcrunch.com/feed/",
    "Engadget":       "https://www.engadget.com/rss.xml",
    "CNBC":           "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
    "NYT Tech":       "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "NYT Business":   "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "NYT World":      "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "Hacker News":    "https://hnrss.org/frontpage?points=100",
}

def fetch_url(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except:
        return None

def fetch_rss(name, url):
    content = fetch_url(url)
    if not content:
        return []
    articles = []
    try:
        root = ET.fromstring(content)
        for item in root.findall(".//item"):
            t = item.find("title")
            l = item.find("link")
            d = item.find("description")
            p = item.find("pubDate")
            if t is not None and l is not None:
                desc = (d.text or "") if d is not None else ""
                # Strip HTML tags from description
                desc = re.sub(r'<[^>]+>', ' ', desc).strip()
                desc = re.sub(r'\s+', ' ', desc)
                articles.append({
                    "title": (t.text or "").strip(),
                    "url": (l.text or "").strip(),
                    "description": desc[:1000],
                    "pub_date": (p.text or "").strip() if p is not None else "",
                    "source": name,
                })
        if not articles:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                t = entry.find("atom:title", ns)
                l = entry.find("atom:link[@rel='alternate']", ns) or entry.find("atom:link", ns)
                s = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
                if t is not None and l is not None:
                    desc = (s.text or "") if s is not None else ""
                    desc = re.sub(r'<[^>]+>', ' ', desc).strip()
                    articles.append({
                        "title": (t.text or "").strip(),
                        "url": l.attrib.get("href", "").strip(),
                        "description": desc[:1000],
                        "pub_date": "",
                        "source": name,
                    })
    except ET.ParseError:
        pass
    logger.info(f"  {name}: {len(articles)}")
    return articles

def is_ad(title, desc=""):
    text = (title + " " + desc).lower()
    for p in BLOCK_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def classify(title, desc=""):
    text = (title + " " + desc).lower()
    scores = {}
    for cat, kws in CATEGORIES.items():
        s = sum(1 for kw in kws if kw.lower() in text)
        if s > 0:
            scores[cat] = s
    return max(scores, key=scores.get) if scores else None

def gen_id(title, url):
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_ids": [], "last_run": None}

def slugify(text):
    return re.sub(r'[^\w\s-]', '', text)[:60].strip().lower().replace(' ', '-')

def main():
    logger.info("=" * 60)
    logger.info("🚀 Wongjai News V3 Fast — 不抓全文版")
    logger.info("=" * 60)

    # 1. Fetch RSS
    logger.info("\n📡 Fetching RSS...")
    all_candidates = []
    for name, url in NEWS_SOURCES.items():
        arts = fetch_rss(name, url)
        all_candidates.extend(arts)
        time.sleep(0.5)

    # 2. Filter
    logger.info("\n🔍 Filtering...")
    seen_in_state = set(load_state().get("seen_ids", []))
    
    filtered = []
    for art in all_candidates:
        if is_ad(art["title"], art.get("description", "")):
            continue
        cat = classify(art["title"], art.get("description", ""))
        if cat is None:
            continue
        art_id = gen_id(art["title"], art["url"])
        if art_id in seen_in_state:
            continue
        art["category"] = cat
        art["id"] = art_id
        filtered.append(art)

    # 3. Limit per category
    cat_counts = Counter()
    limited = []
    for art in filtered:
        if cat_counts[art["category"]] < MAX_PER_CAT:
            limited.append(art)
            cat_counts[art["category"]] += 1

    logger.info(f"  Final: {len(limited)} articles")
    for cat, cnt in cat_counts.most_common():
        logger.info(f"    {cat}: {cnt}")

    # 4. Translate & save (fast — no text extraction)
    try:
        from deep_translator import GoogleTranslator
        t_zh = GoogleTranslator(source='auto', target='zh-TW')
        t_cn = GoogleTranslator(source='auto', target='zh-CN')
        t_ja = GoogleTranslator(source='auto', target='ja')

        def ts(t, text):
            try:
                return t.translate(text[:2000])
            except:
                return text

        logger.info("\n📝 Translating & saving...")
        for i, art in enumerate(limited):
            title = art["title"]
            summary = art.get("description", "")[:500]

            art["title_zh_tw"] = ts(t_zh, title)
            art["title_zh_cn"] = ts(t_cn, title)
            art["title_ja"] = ts(t_ja, title)
            art["summary_en"] = summary
            art["summary_zh_tw"] = ts(t_zh, summary)
            art["summary_zh_cn"] = ts(t_cn, summary)
            art["summary_ja"] = ts(t_ja, summary)

            # Write markdown
            def yv(s):
                s = re.sub(r'[\n\r]', ' ', s or '').strip()
                return f'"{s}"'

            date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            safe = slugify(title)[:40]
            fn = f"{date_str}-{art['id']}-{safe}.md"

            md = f"""---
title: {yv(title)}
date: {yv(art.get('pub_date', ''))}
source: {art['source']}
category: {art['category']}
original_url: {yv(art['url'])}
title_en: {yv(title)}
title_zh_tw: {yv(art['title_zh_tw'])}
title_zh_cn: {yv(art['title_zh_cn'])}
title_ja: {yv(art['title_ja'])}
summary_en: {yv(summary)}
summary_zh_tw: {yv(art['summary_zh_tw'])}
summary_zh_cn: {yv(art['summary_zh_cn'])}
summary_ja: {yv(art['summary_ja'])}
draft: false
---

{summary}
"""
            (CONTENT_DIR / fn).write_text(md, encoding="utf-8")

            if (i+1) % 10 == 0:
                logger.info(f"  [{i+1}/{len(limited)}] done")
            time.sleep(0.5)

        # Save state
        state = load_state()
        state["seen_ids"].extend([a["id"] for a in limited])
        # Keep seen_ids manageable
        if len(state["seen_ids"]) > 5000:
            state["seen_ids"] = state["seen_ids"][-3000:]
        state["last_run"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
        STATE_FILE.write_text(json.dumps(state, indent=2))

        logger.info(f"\n✅ {len(limited)} articles saved + translated")

    except ImportError:
        logger.error("deep_translator not available, saving without translation.")

    # 5. Purge
    logger.info("\n🧹 Purging excess per category...")
    cat_files = defaultdict(list)
    for f in CONTENT_DIR.glob("*.md"):
        c = f.read_text(encoding="utf-8")
        m = re.match(r'^---\n(.*?)\n---', c, re.DOTALL)
        if not m: continue
        cat = "科技"
        for line in m.group(1).split('\n'):
            if line.startswith('category:'):
                cat = line.split(':', 1)[1].strip()
                break
        cat_files[cat].append(f)

    purged = 0
    for cat, files in cat_files.items():
        if len(files) > MAX_PER_CAT:
            for f in files[MAX_PER_CAT:]:
                f.unlink()
                purged += 1
    logger.info(f"  Purged {purged} old files")

    logger.info("\n✅ Done!")

if __name__ == "__main__":
    main()
