#!/usr/bin/env python3
"""
Wongjai News 爬蟲 V3 — 全面重構
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
來源: DigiTimes, Engadget, CNBC, NYT, WSJ, Reuters, TechCrunch, Hacker News
分類: AI / 半導體 / 電動車 / 太空 / 經濟 / 科技 / 地緣政治
每類上限 20 則，超額 purge 舊的
過濾廣告 / 促銷 / 折價券 / 評測指南
翻譯: EN + ZH-TW + ZH-CN + JA
"""
import hashlib, json, re, sys, time, urllib.request, urllib.error, logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsCrawlerV3")

# ── Paths ────────────────────────────────────────────────
REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
CONTENT_DIR = REPO_DIR / "content" / "news"
STATE_FILE = REPO_DIR / "scripts" / "crawler_state_v3.json"
MAX_PER_CAT = 20

# ── Categories & Keywords ───────────────────────────────
CATEGORIES = {
    "AI": ["artificial intelligence", "ai ", "llm", "gpt", "claude", "gemini",
           "machine learning", "deep learning", "neural network", "openai", "anthropic",
           "generative ai", "chatbot", "transformer model", "ai chip", "大語言模型",
           "artificial general intelligence", "agi", "grok"],
    "半導體": ["semiconductor", "tsmc", "intel", "amd", "nvidia", "qualcomm",
               "chip ", "fab ", "foundry", "wafer", "euv", "lithography", "asml",
               "processor", "gpu ", "soc ", "先進製程", "先進封裝", "co-wo",
               "3nm", "2nm"],
    "電動車": ["electric vehicle", "ev ", "tesla", "evs", "byd", "rivian", "lucid",
               "autonomous driving", "self-driving", "battery ", "lithium battery",
               "charging station", "ev adoption", "電動", "自駕"],
    "太空": ["spacex", "rocket", "satellite", "starlink", "nasa", "artemis",
             "space exploration", "mars", "moon mission", "orbital", "launch",
             "太空", "火箭", "衛星"],
    "經濟": ["inflation", "interest rate", "federal reserve", "gdp", "recession",
             "economy ", "economic ", "tariff", "trade war", "fed ", "treasury",
             "wall street", "stock market", "通膨", "利率", "央行",
             "經濟", "關稅"],
    "科技": ["apple", "google", "microsoft", "amazon", "meta", "cloud computing",
             "cybersecurity", "quantum computing", "robotics", "software", "saaS",
             "operating system", "smartphone", "tech company"],
    "地緣政治": ["china", "taiwan", "ukraine", "russia", "geopolitics", "military",
                 "defense ", "sanctions", "nato", "pentagon", "south china sea",
                 "cross-strait", "地緣政治", "軍事", "國防"],
}

# ── AD / PROMO FILTERS (block these) ────────────────────
BLOCK_KEYWORDS = [
    "promo code", "coupon", "discount", "off your", "save up to", "best deals",
    "deals you can get", "promo codes", "coupon code", "deal of the day",
    "buy now", "shop now", "save money", "best price", "lowest price",
    "free shipping", "free delivery", "free trial", "50% off", "20% off",
    "30% off", "$150 off", "$100 off", "best ", "review:", "tested and reviewed",
    "hands-on review", "product roundup", "best of", "top picks", "gift guide",
    "holiday gift", "christmas gift", "black friday", "cyber monday",
    "prime day", "home depot", "dyson", "booking.com", "door dash", "chewy",
    "skullcandy", "samsung promo", "amazon deal", "target deal",
    "best robot lawn", "best ski clothes", "best airpods", "best ipad apps",
    "best apple watch", "best headphone", "best ",
]

# ── News Sources ─────────────────────────────────────────
NEWS_SOURCES = {
    "DigiTimes":     {"rss": "https://www.digitimes.com/rss/rss.xml"},
    "Engadget":      {"rss": "https://www.engadget.com/rss.xml"},
    "CNBC":          {"rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"},  # Top News
    "NYT Tech":      {"rss": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"},
    "NYT Business":  {"rss": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"},
    "Reuters Tech":  {"rss": "https://www.reutersagency.com/feed/?best-regions=technology&post_type=best"},
    "TechCrunch":    {"rss": "https://techcrunch.com/feed/"},
    "Hacker News":   {"rss": "https://hnrss.org/frontpage?points=100"},
}

def fetch_url(url: str, timeout: int = 15):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Fetch failed {url}: {e}")
        return None

def fetch_rss(source_name: str, rss_url: str) -> list[dict]:
    content = fetch_url(rss_url)
    if not content:
        return []
    articles = []
    try:
        root = ET.fromstring(content)
        # RSS 2.0
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            if title_el is not None and link_el is not None:
                articles.append({
                    "title": (title_el.text or "").strip(),
                    "url": (link_el.text or "").strip(),
                    "description": (desc_el.text or "").strip() if desc_el is not None else "",
                    "pub_date": (pub_el.text or "").strip() if pub_el is not None else "",
                    "source": source_name,
                })
        # Atom fallback
        if not articles:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link[@rel='alternate']", ns)
                if link_el is None:
                    link_el = entry.find("atom:link", ns)
                summary_el = entry.find("atom:summary", ns)
                if summary_el is None:
                    summary_el = entry.find("atom:content", ns)
                updated_el = entry.find("atom:updated", ns)
                if title_el is not None and link_el is not None:
                    articles.append({
                        "title": (title_el.text or "").strip(),
                        "url": (link_el.attrib.get("href", "") if link_el is not None else "").strip(),
                        "description": (summary_el.text or "").strip() if summary_el is not None else "",
                        "pub_date": (updated_el.text or "").strip() if updated_el is not None else "",
                        "source": source_name,
                    })
    except ET.ParseError as e:
        logger.warning(f"RSS parse error for {source_name}: {e}")
    logger.info(f"  {source_name}: {len(articles)} items")
    return articles

def is_ad_or_promo(title: str, description: str = "") -> bool:
    """Check if article is an ad, promo, coupon, or deal roundup."""
    text = (title + " " + description).lower()
    # Direct block keyword match
    for kw in BLOCK_KEYWORDS:
        if kw.lower() in text:
            return True
    # Pattern: "X% Off" or "$X Off"
    if re.search(r'\d+%\s*(off|discount)', text):
        return True
    if re.search(r'\$\d+\s*(off|savings|saved)', text):
        return True
    return False

def classify_article(title: str, description: str = ""):
    """Classify into our categories. Return None if not relevant."""
    text = (title + " " + description).lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        score = 0
        for kw in keywords:
            if kw.lower() in text:
                score += 1
        if score > 0:
            scores[cat] = score
    
    if not scores:
        return None  # Not relevant
    
    # Return highest-scoring category
    return max(scores, key=scores.get)

def generate_id(title: str, url: str) -> str:
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]

def extract_article_text(url: str) -> str:
    """Extract main article text from URL."""
    html = fetch_url(url)
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "svg"]):
            tag.decompose()
        
        # Try common article containers
        for selector in ["article", ".article-body", ".article-content", "main", ".content", ".story-body", ".article"]:
            container = soup.select_one(selector)
            if container:
                text = container.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text
        
        # Fallback: body text
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            return text[:5000]
    except Exception:
        pass
    return ""

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_ids": [], "last_run": None, "category_counts": {}}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def slugify(text: str) -> str:
    return re.sub(r'[^\w\s-]', '', text)[:60].strip().lower().replace(' ', '-')

def save_article(article: dict):
    """Save as Hugo markdown with 4-language front matter."""
    from datetime import datetime
    safe_title = slugify(article["title"])
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"{date_str}-{article['id']}-{safe_title[:40]}.md"
    
    # Ensure title is properly quoted in YAML — use single-line with escaped quotes
    def yaml_val(s):
        if not s:
            return '""'
        s = s.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ').strip()
        return f'"{s}"'
    
    fm_lines = [
        f"---",
        f"title: {yaml_val(article['title'])}",
        f"date: {yaml_val(article.get('pub_date', ''))}",
        f"source: {article.get('source', 'Unknown')}",
        f"category: {article.get('category', '科技')}",
        f"original_url: {yaml_val(article.get('url', ''))}",
        f"title_en: {yaml_val(article['title'])}",
        f"title_zh_tw: {yaml_val(article.get('title_zh_tw', ''))}",
        f"title_zh_cn: {yaml_val(article.get('title_zh_cn', ''))}",
        f"title_ja: {yaml_val(article.get('title_ja', ''))}",
        f"summary_en: {yaml_val(article.get('summary_en', ''))}",
        f"summary_zh_tw: {yaml_val(article.get('summary_zh_tw', ''))}",
        f"summary_zh_cn: {yaml_val(article.get('summary_zh_cn', ''))}",
        f"summary_ja: {yaml_val(article.get('summary_ja', ''))}",
        f"draft: false",
        f"---",
        f"\n{article.get('full_text', '')}\n",
    ]
    
    filepath = CONTENT_DIR / filename
    filepath.write_text("\n".join(fm_lines), encoding="utf-8")
    logger.info(f"  💾 {filename[:70]}")

def purge_by_category():
    """Ensure each category has at most MAX_PER_CAT articles. Oldest get purged."""
    from collections import defaultdict
    
    cat_files = defaultdict(list)
    for f in CONTENT_DIR.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not m:
            continue
        fm = m.group(1)
        cat = "科技"
        for line in fm.split('\n'):
            if line.startswith('category:'):
                cat = line.split(':', 1)[1].strip().strip('"').strip("'")
                break
        date_match = re.search(r'date:\s*"([^"]+)"', fm)
        date_str = date_match.group(1) if date_match else "1970-01-01"
        cat_files[cat].append((date_str, f))
    
    purged = 0
    for cat, files in cat_files.items():
        files.sort(key=lambda x: x[0], reverse=True)
        if len(files) > MAX_PER_CAT:
            for _, fpath in files[MAX_PER_CAT:]:
                fpath.unlink()
                purged += 1
                logger.info(f"  🗑️ Purged: {fpath.name[:60]}")
    
    if purged > 0:
        logger.info(f"  Purged {purged} old articles")

def main():
    logger.info("=" * 60)
    logger.info("🚀 Wongjai News 爬蟲 V3 啟動")
    logger.info("=" * 60)
    logger.info("Sources: DigiTimes, Engadget, CNBC, NYT, WSJ, Reuters, TechCrunch, HN")
    logger.info("Categories: AI / 半導體 / 電動車 / 太空 / 經濟 / 科技 / 地緣政治")
    logger.info(f"Max per category: {MAX_PER_CAT}")
    
    state = load_state()
    state["last_run"] = datetime.now(timezone(timedelta(hours=8))).isoformat()
    
    # Step 1: Fetch all RSS feeds
    logger.info("\n📡 Fetching RSS feeds...")
    all_candidates = []
    for source_name, info in NEWS_SOURCES.items():
        articles = fetch_rss(source_name, info["rss"])
        all_candidates.extend(articles)
        time.sleep(0.8)
    
    logger.info(f"\n📋 Total candidates: {len(all_candidates)}")
    
    # Step 2: Filter out ads and irrelevant content
    logger.info("\n🔍 Filtering...")
    filtered = []
    for art in all_candidates:
        if is_ad_or_promo(art["title"], art.get("description", "")):
            continue
        cat = classify_article(art["title"], art.get("description", ""))
        if cat is None:
            continue
        art["category"] = cat
        art["id"] = generate_id(art["title"], art["url"])
        if art["id"] in state["seen_ids"]:
            continue
        filtered.append(art)
    
    logger.info(f"  After filtering: {len(filtered)} articles")
    
    # Step 3: Limit to MAX_PER_CAT per category
    logger.info("\n📊 Limiting per category...")
    from collections import Counter
    cat_counts = Counter(a["category"] for a in filtered)
    limited = []
    cat_seen = Counter()
    for art in filtered:
        if cat_seen[art["category"]] < MAX_PER_CAT:
            limited.append(art)
            cat_seen[art["category"]] += 1
    
    logger.info(f"  Final: {len(limited)} articles")
    for cat, count in cat_seen.items():
        logger.info(f"    {cat}: {count}")
    
    # Step 4: Process articles — extract text, translate, save
    logger.info("\n📖 Processing articles...")
    
    # Import translation
    try:
        from deep_translator import GoogleTranslator
        t_zh_tw = GoogleTranslator(source='auto', target='zh-TW')
        t_zh_cn = GoogleTranslator(source='auto', target='zh-CN')
        t_ja = GoogleTranslator(source='auto', target='ja')
        
        def translate_safe(t, text, retries=2):
            if not text: return text
            for r in range(retries):
                try:
                    return t.translate(text[:2000])
                except:
                    if r < retries - 1: time.sleep(1)
            return text
        
        def translate_article(art):
            title = art["title"]
            desc = art.get("description", "")
            
            # Try to extract full text
            full_text = extract_article_text(art["url"])
            if full_text:
                # Clean up text
                full_text = re.sub(r'\n+', '\n', full_text).strip()[:3000]
            
            # Use description or full text for summary
            summary = full_text[:500] if full_text else desc
        
            # Translate title and summary
            art["title_zh_tw"] = translate_safe(t_zh_tw, title)
            art["title_zh_cn"] = translate_safe(t_zh_cn, title)
            art["title_ja"] = translate_safe(t_ja, title)
            
            art["summary_en"] = summary
            art["summary_zh_tw"] = translate_safe(t_zh_tw, summary)
            art["summary_zh_cn"] = translate_safe(t_zh_cn, summary)
            art["summary_ja"] = translate_safe(t_ja, summary)
            
            art["full_text"] = full_text
            
            time.sleep(0.5)  # Rate limit
        
        for i, art in enumerate(limited):
            logger.info(f"  [{i+1}/{len(limited)}] {art['title'][:60]}...")
            translate_article(art)
            state["seen_ids"].append(art["id"])
            save_article(art)
            time.sleep(0.3)
            
    except ImportError:
        logger.error("deep_translator not installed. Running without translation.")
        for art in limited:
            art["title_zh_tw"] = art["title"]
            art["title_zh_cn"] = art["title"]
            art["title_ja"] = art["title"]
            art["summary_en"] = art.get("description", "")
            art["summary_zh_tw"] = "[待翻譯]"
            art["summary_zh_cn"] = "[待翻譯]"
            art["summary_ja"] = "[待翻譯]"
            art["full_text"] = ""
            state["seen_ids"].append(art["id"])
            save_article(art)
    
    # Step 5: Purge old articles
    logger.info("\n🧹 Purging old articles by category...")
    purge_by_category()
    
    # Step 6: Save state
    save_state(state)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Completed! {len(limited)} new articles saved")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
