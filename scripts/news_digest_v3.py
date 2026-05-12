#!/usr/bin/env python3
"""
Wongjai News Digest v3 — RSS fetching + full article + ~100 word summaries.
Outputs data/news.json for SPA.
"""

import json, re, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import urllib.request
import xml.etree.ElementTree as ET
from dateutil import parser as date_parser

NOW = datetime.now(timezone(timedelta(hours=8)))
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── RSS Sources (cat, url) ──────────────────────────────────
RSS_SOURCES = [
    # 科技類
    ("tech", "https://technews.tw/feed/"),
    ("tech", "https://feeds.feedburner.com/TheHackersNews"),
    ("tech", "https://techcrunch.com/feed/"),
    ("tech", "https://feeds.arstechnica.com/arstechnica/index"),
    # 經濟類
    ("econ", "https://feeds.bloomberg.com/markets/news.rss"),
    ("econ", "https://www.marketwatch.com/rss/topstories"),
]

# ── HTTP ────────────────────────────────────────────────────

def fetch_url(url, timeout=12):
    h = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=h)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ✗ {url}: {e}")
        return ""

# ── RSS Parse ──────────────────────────────────────────────

def parse_rss(url, cat):
    items = []
    xml = fetch_url(url)
    if not xml:
        return items
    try:
        root = ET.fromstring(xml)
        for item in root.findall(".//item")[:30]:
            title = (item.find("title").text or "").strip()
            link = (item.find("link").text or "").strip()
            desc_raw = (item.find("description").text or "")
            desc = re.sub(r"<[^>]+>", "", desc_raw).strip()
            desc = re.sub(r"\s+", " ", desc)[:500]
            pub_raw = (item.find("pubDate").text or "").strip()
            pub = None
            if pub_raw:
                try:
                    pub = date_parser.parse(pub_raw)
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                except:
                    pass
            items.append({"cat": cat, "title": title, "url": link, "desc": desc, "pub_date": pub})
    except Exception as e:
        print(f"  ✗ RSS parse: {e}")
    return items

# ── Full Article Extract ───────────────────────────────────

def extract_full_text(html, max_chars=2000):
    """Extract main article text from HTML page."""
    if not html:
        return ""
    # Remove script/style
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html)
    html = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", html)
    html = re.sub(r"<!--[\s\S]*?-->", "", html)
    # Try article tag first
    art = re.search(r"<article[^>]*>([\s\S]*?)</article>", html)
    target = art.group(1) if art else html
    # Extract paragraphs
    paragraphs = re.findall(r"<p[^>]*>([\s\S]*?)</p>", target)
    parts = []
    for p in paragraphs:
        text = re.sub(r"<[^>]+>", "", p).strip()
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        if len(text) > 30:  # skip empty / nav paragraphs
            parts.append(text)
            if sum(len(x) for x in parts) > max_chars:
                break
    result = " ".join(parts)
    return result[:max_chars]

# ── Summary Generation (from full article text) ─────────────

def generate_summary(full_text, rss_desc):
    """Generate ~100 word English summary from full article text.
    Uses extractive summarization if full text available, falls back to RSS desc."""
    if not full_text and not rss_desc:
        return ""
    text = full_text or rss_desc
    # Simple extractive: take first N sentences that give ~100 words
    sentences = re.split(r"(?<=[.!?])\s+", text)
    words = 0
    summary_parts = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15:  # skip headers / nav
            continue
        word_count = len(s.split())
        if words + word_count > 120 and summary_parts:
            break
        summary_parts.append(s)
        words += word_count
    summary = " ".join(summary_parts)
    # Truncate if too long
    if len(summary) > 150:
        # find last sentence break
        last_dot = summary[:120].rfind(".")
        if last_dot > 50:
            summary = summary[:last_dot + 1]
        else:
            summary = summary[:120].rsplit(" ", 1)[0] + "..."
    return summary

# ── Main ────────────────────────────────────────────────────

def main():
    print("📡 Fetching RSS sources...")
    all_news = []
    for cat, url in RSS_SOURCES:
        print(f"  📰 [{cat}] {url}")
        items = parse_rss(url, cat)
        print(f"    → {len(items)} articles from RSS")
        for item in items:
            # Only keep articles from last 24h
            if item["pub_date"] and (NOW - item["pub_date"]).total_seconds() > 86400:
                continue
            all_news.append(item)
        time.sleep(0.5)

    # Dedup by URL
    seen = set()
    unique = []
    for n in all_news:
        if n["url"] not in seen:
            seen.add(n["url"])
            unique.append(n)
    all_news = unique
    print(f"\n📊 Unique articles: {len(all_news)}")

    # Fetch full article content + generate summaries
    print("\n📖 Fetching full articles + generating summaries...")
    final = []
    for i, n in enumerate(all_news):
        print(f"  [{i+1}/{len(all_news)}] {n['title'][:60]}...", end=" ")

        # Fetch full article
        page_html = fetch_url(n["url"], timeout=15)
        full = extract_full_text(page_html, max_chars=2500)

        # Generate summary
        summary = generate_summary(full, n["desc"])

        pub = n.get("pub_date")
        rank = int(pub.timestamp()) if pub else 0
        time_iso = pub.isoformat() if pub else NOW.isoformat()

        # For now: same summary for all languages; full text for zh
        final.append({
            "cat": n["cat"],
            "title_en": n["title"],
            "title_zh": n["title"],
            "title_zcn": n["title"],
            "title_ja": n["title"],
            "s_en": summary,
            "s_zh": full[:500] or summary,
            "s_zcn": full[:500] or summary,
            "s_ja": full[:500] or summary,
            "so": "科技新報" if "technews.tw" in n["url"] else n["url"].split("/")[2].replace("www.", "") if "/" in n["url"] else "",
            "url": n["url"],
            "time": time_iso,
            "rank": rank,
        })
        print(f"✓ ({len(summary)} chars)")
        time.sleep(0.3)

    # Cap at 50 per category
    groups = {"tech": [], "econ": []}
    for n in final:
        groups[n["cat"]].append(n)
    for cat in groups:
        groups[cat].sort(key=lambda x: x["rank"], reverse=True)
        before = len(groups[cat])
        groups[cat] = groups[cat][:50]
        print(f"\n  {cat}: {before} → {len(groups[cat])}")

    result = groups["tech"] + groups["econ"]
    print(f"\n✅ Writing {len(result)} articles to data/news.json")

    with open(DATA_DIR / "news.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Copy to static/data/ too
    static_data = BASE / "static" / "data"
    static_data.mkdir(exist_ok=True)
    import shutil
    shutil.copy2(DATA_DIR / "news.json", static_data / "news.json")

    print("✅ Done!")


if __name__ == "__main__":
    main()
