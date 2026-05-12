#!/usr/bin/env python3
"""
news_crawler_v2.py — Wongjai News 爬蟲 v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
功能：
1. 從穩定 RSS 來源抓取新聞（TechCrunch, Ars Technica, The Verge, CNBC, NYT, HN）
2. 用 BeautifulSoup 提取文章內文
3. 規則摘要（後續可批次送 AI 翻譯）
4. 自動分類（AI/半導體/電動車/太空/經濟/科技/地緣政治）
5. 生成 Hugo markdown
6. 最多 50 則新聞，超過 purge 舊的

作者: Wongjai ⚡
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging
from xml.etree import ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsCrawlerV2")

# ── 路徑設定 ────────────────────────────────────────────
REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
CONTENT_DIR = REPO_DIR / "content" / "news"
STATE_FILE = REPO_DIR / "scripts" / "crawler_state_v2.json"
MAX_NEWS = 150

# ── 分類規則 ─────────────────────────────────────────────
CATEGORIES = {
    "AI": [
        "artificial intelligence", "ai", "llm", "gpt", "claude", "gemini",
        "machine learning", "deep learning", "neural", "openai", "anthropic",
        "generative ai", "chatbot", "transformer", "nvidia gpu", "ai chip",
        "人工智慧", "機器學習",
    ],
    "半導體": [
        "semiconductor", "chip", "tsmc", "intel", "amd", "nvidia", "qualcomm",
        "fab", "foundry", "wafer", "euv", "lithography", "asml", "arm",
        "processor", "gpu", "晶圓", "半導體", "製程",
    ],
    "電動車": [
        "electric vehicle", "ev ", "tesla", "battery", "autonomous", "self-driving",
        "lithium", "charging", "electric car", "電動車", "自駕", "電池",
    ],
    "太空": [
        "spacex", "rocket", "satellite", "starlink", "nasa", "space", "orbital",
        "太空", "火箭", "衛星", "星鏈",
    ],
    "經濟": [
        "inflation", "interest rate", "federal reserve", "gdp", "recession",
        "economy", "economic", "tariff", "trade war", "fed ", "treasury",
        "通膨", "利率", "經濟", "央行",
    ],
    "科技": [
        "apple", "google", "microsoft", "amazon", "meta", "cloud", "saas",
        "cybersecurity", "quantum", "robotics", "delivery", "revenue",
        "earnings", "quarterly", "科技", "雲端",
    ],
    "地緣政治": [
        "china", "taiwan", "ukraine", "russia", "geopolitics", "military",
        "defense", "sanctions", "nato", "地緣政治", "軍事",
    ],
}

# ── 排除關鍵字（命中任一就跳過）─────────────────────────
EXCLUDE_KEYWORDS = [
    "celebrity", "gossip", "entertainment", "fashion", "beauty",
    "recipe", "cooking", "sports score", "nba", "nfl", "mlb",
    "horoscope", "astrology", "wedding", "dating",
    "名人", "八卦", "美食", "星座", "穿搭",
]

# ── 新聞來源定義（18+ 知名網站 + Google News）────────
NEWS_SOURCES = {
    # Tech 主流
    "TechCrunch": {"rss": "https://techcrunch.com/feed/"},
    "Ars Technica": {"rss": "https://feeds.arstechnica.com/arstechnica/index"},
    "The Verge": {"rss": "https://www.theverge.com/rss/index.xml"},
    "Engadget": {"rss": "https://www.engadget.com/rss.xml"},
    "Wired": {"rss": "https://www.wired.com/feed/rss"},
    "VentureBeat": {"rss": "https://venturebeat.com/feed/"},
    "The Register": {"rss": "https://www.theregister.com/headlines.atom"},
    # 財經
    "CNBC Tech": {"rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"},
    "CNBC World": {"rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"},
    "MarketWatch": {"rss": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    "Yahoo Finance": {"rss": "https://finance.yahoo.com/news/rssindex"},
    # 科技深度
    "NYT Tech": {"rss": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"},
    "BBC Tech": {"rss": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    "Guardian Tech": {"rss": "https://www.theguardian.com/technology/rss"},
    # 開發者 / AI
    "Hacker News": {"rss": "https://hnrss.org/frontpage?points=100"},
    "MIT Tech Review": {"rss": "https://www.technologyreview.com/feed/"},
    # 太空 / 科學
    "Space.com": {"rss": "https://www.space.com/feeds/all"},
    # 台灣科技
    "科技新報": {"rss": "https://technews.tw/feed/"},
    # Google News（僅用於補充來源，連結會跟隨到原始網站）
    "Google AI": {"rss": "https://news.google.com/rss/search?q=artificial+intelligence+OR+AI+chip&hl=en-US&gl=US&ceid=US:en"},
    "Google Semi": {"rss": "https://news.google.com/rss/search?q=semiconductor+OR+TSMC+OR+Nvidia+chip&hl=en-US&gl=US&ceid=US:en"},
    "Google EV": {"rss": "https://news.google.com/rss/search?q=Tesla+OR+electric+vehicle+OR+EV&hl=en-US&gl=US&ceid=US:en"},
}


def resolve_google_news_url(url: str) -> str:
    """解析 Google News 重定向連結，取得原始文章 URL"""
    if "news.google.com" not in url:
        return url
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.url  # 跟隨重定向後的最終 URL
    except Exception:
        return url  # 失敗就保留原始連結


def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    """下載網頁內容"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"下載失敗 {url}: {e}")
        return None


def fetch_rss_articles(rss_url: str, source_name: str) -> List[Dict]:
    """從 RSS feed 提取文章連結"""
    articles = []
    content = fetch_url(rss_url)
    if not content:
        return articles

    try:
        root = ET.fromstring(content)
        # RSS 2.0
        items = root.findall(".//item")
        if not items:
            # Atom
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//atom:entry", ns)

        for item in items[:15]:  # 每個來源最多抓 15 則
            title = item.findtext("title") or item.findtext("atom:title", namespaces={"atom": "http://www.w3.org/2005/Atom"}) or ""
            link = item.findtext("link") or ""
            if not link:
                link_el = item.find("atom:link", {"atom": "http://www.w3.org/2005/Atom"})
                if link_el is not None:
                    link = link_el.get("href", "")

            pub_date = item.findtext("pubDate") or item.findtext("atom:published", namespaces={"atom": "http://www.w3.org/2005/Atom"}) or ""

            # HN 的 link 格式不同，需要從 description 提取
            if source_name == "Hacker News" and "news.ycombinator.com" in link:
                desc = item.findtext("description") or ""
                # HN RSS 的 link 指向 HN 討論頁，description 中可能有原始連結
                # 但 HN 討論頁也可以作為連結
                pass

            if title and link:
                articles.append({
                    "title": title.strip(),
                    "url": link.strip(),
                    "date": pub_date.strip(),
                    "source": source_name,
                })
    except ET.ParseError as e:
        logger.warning(f"RSS 解析失敗 {source_name}: {e}")

    return articles


def extract_article_text(url: str) -> Optional[str]:
    """用 BeautifulSoup 提取文章內文"""
    html = fetch_url(url, timeout=20)
    if not html:
        return None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # 移除不需要的元素
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "form", "button", "noscript", "svg", "img"]):
            tag.decompose()

        # 嘗試多種選擇器找到文章主體
        article = None
        for selector in ["article", "[role='main']", ".article-body",
                         ".post-content", ".entry-content", ".story-body",
                         "main", ".content"]:
            article = soup.select_one(selector)
            if article:
                break

        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # 清理空行
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        return text[:3000] if len(text) > 100 else None
    except Exception as e:
        logger.warning(f"提取失敗: {e}")
        return None


def is_relevant(title: str, snippet: str) -> bool:
    """判斷新聞是否相關（排除法）"""
    text = (title + " " + snippet).lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text:
            return False
    return True  # 預設通過


def classify_article(title: str, snippet: str) -> str:
    """自動分類"""
    text = (title + " " + snippet).lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[cat] = score

    if scores:
        return max(scores, key=scores.get)
    return "科技"  # 預設


def parse_date(date_str: str) -> str:
    """解析各種日期格式，回傳 ISO 格式"""
    if not date_str:
        return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S")

    date_str = date_str.strip()

    # RFC 2822: "Wed, 02 Apr 2026 14:30:00 +0000" or "GMT"
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(date_str, fmt)
            # 轉換到台北時間
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone(timedelta(hours=8)))
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue

    # 手動處理 "+0000" 格式（%z 在某些 Python 版本可能不支援 "+0000"）
    m = re.match(r"(\w+,\s+\d+\s+\w+\s+\d+\s+\d+:\d+:\d+)\s+([+-]\d{4})", date_str)
    if m:
        try:
            base = datetime.strptime(m.group(1), "%a, %d %b %Y %H:%M:%S")
            base = base.replace(tzinfo=timezone.utc)
            base = base.astimezone(timezone(timedelta(hours=8)))
            return base.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S")


def generate_id(title: str, url: str) -> str:
    """生成唯一 ID"""
    return hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]


# ── 節省 Token 的摘要策略 ──────────────────────────────
# 英文摘要：直接從內文提取前 N 句（0 token）
# 翻譯摘要：只翻譯 ~100 字的英文摘要（省 80% token vs 送整篇文章）

def extract_summary_from_text(article_text: str, max_sentences: int = 4) -> str:
    """從內文提取前 N 句作為摘要（0 token 成本）"""
    sentences = re.split(r'(?<=[.!?])\s+', article_text.strip())
    good_sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    summary = " ".join(good_sentences[:max_sentences])
    words = summary.split()
    if len(words) > 120:
        summary = " ".join(words[:115]) + "."
    if not summary.endswith(('.', '!', '?')):
        last_period = summary.rfind('.')
        if last_period > len(summary) // 2:
            summary = summary[:last_period + 1]
        else:
            summary += '.'
    return summary


def ai_summarize(title: str, article_text: str, source: str) -> Optional[Dict]:
    """智慧摘要：從內文提取英文摘要，標記需 AI 翻譯"""
    try:
        summary_en = extract_summary_from_text(article_text)
        category = classify_article(title, summary_en)
        return {
            "summary_en": summary_en,
            "summary_zh_tw": "[待翻譯]",
            "summary_zh_cn": "[待翻譯]",
            "summary_ja": "[待翻譯]",
            "category": category,
        }
    except Exception as e:
        logger.warning(f"摘要提取失敗: {e}")
        return None


# ── Hugo 輸出 ──────────────────────────────────────────

def generate_hugo_markdown(article: Dict) -> str:
    """生成 Hugo markdown 檔案（含 front matter）"""
    article_id = article.get("id", generate_id(article["title"], article["url"]))
    date = article.get("date", datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S"))
    source = article.get("source", "Unknown")
    category = article.get("category", "科技")
    url = article.get("url", "")

    # 4 語言標題
    title_en = article.get("title", "")
    title_zh_tw = article.get("title_zh_tw", title_en)
    title_zh_cn = article.get("title_zh_cn", title_en)
    title_ja = article.get("title_ja", title_en)

    # 4 語言摘要
    summary_en = article.get("summary_en", "")
    summary_zh_tw = article.get("summary_zh_tw", summary_en)
    summary_zh_cn = article.get("summary_zh_cn", summary_en)
    summary_ja = article.get("summary_ja", summary_en)

    # 轉義 YAML 特殊字元
    def yaml_escape(s):
        if not s:
            return ""
        s = s.replace('"', '\\"').replace('\n', ' ')
        if any(c in s for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`']):
            return f'"{s}"'
        return s

    md = f"""---
title: {yaml_escape(title_en)}
date: "{date}"
source: {yaml_escape(source)}
category: {yaml_escape(category)}
original_url: {yaml_escape(url)}
title_en: {yaml_escape(title_en)}
title_zh_tw: {yaml_escape(title_zh_tw)}
title_zh_cn: {yaml_escape(title_zh_cn)}
title_ja: {yaml_escape(title_ja)}
summary_en: {yaml_escape(summary_en)}
summary_zh_tw: {yaml_escape(summary_zh_tw)}
summary_zh_cn: {yaml_escape(summary_zh_cn)}
summary_ja: {yaml_escape(summary_ja)}
draft: false
---

{summary_en}
"""
    return md


def save_article(article: Dict):
    """儲存文章到 Hugo content 目錄"""
    article_id = article.get("id", generate_id(article["title"], article["url"]))
    date_prefix = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    filename = f"{date_prefix}-{article_id}.md"

    md = generate_hugo_markdown(article)
    filepath = CONTENT_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    logger.info(f"已儲存: {filename} — {article['title'][:50]}")
    return filepath


# ── 狀態管理 ──────────────────────────────────────────

def load_state() -> Dict:
    """載入爬蟲狀態"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"seen_ids": [], "last_run": None}


def save_state(state: Dict):
    """儲存爬蟲狀態"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def purge_old_articles(max_count: int = MAX_NEWS):
    """purge 超過上限的舊文章"""
    md_files = sorted(CONTENT_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if len(md_files) > max_count:
        for f in md_files[max_count:]:
            f.unlink()
            logger.info(f"Purge: {f.name}")


# ── 主流程 ──────────────────────────────────────────────

def crawl_all_sources() -> List[Dict]:
    """爬取所有新聞來源"""
    all_articles = []
    seen_urls = set()

    for source_name, config in NEWS_SOURCES.items():
        logger.info(f"📡 爬取 {source_name}...")
        articles = []

        if config.get("rss"):
            articles = fetch_rss_articles(config["rss"], source_name)

        # 去重
        for a in articles:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                all_articles.append(a)

        logger.info(f"  {source_name}: {len(articles)} 則")
        time.sleep(1)  # 避免過快

    logger.info(f"總計: {len(all_articles)} 則候選新聞")
    return all_articles


def process_article(article: Dict, state: Dict) -> Optional[Dict]:
    """處理單則新聞：提取內文 → 篩選 → 摘要"""
    article_id = generate_id(article["title"], article["url"])

    # 跳過已處理的
    if article_id in state["seen_ids"]:
        return None

    # 先用標題做排除篩選
    if not is_relevant(article["title"], ""):
        logger.debug(f"跳過（排除關鍵字命中）: {article['title'][:50]}")
        return None

    # 解析 Google News 重定向連結
    if "news.google.com" in article["url"]:
        article["url"] = resolve_google_news_url(article["url"])

    # 提取內文
    logger.info(f"  📖 提取內文: {article['title'][:50]}...")
    article_text = extract_article_text(article["url"])
    if not article_text or len(article_text) < 100:
        logger.warning(f"  內文太短或提取失敗，跳過")
        return None

    # 二次排除篩選（用內文前 500 字）
    if not is_relevant(article["title"], article_text[:500]):
        logger.debug(f"  跳過（內文排除關鍵字命中）")
        return None

    # 分類
    category = classify_article(article["title"], article_text[:500])

    # 解析日期
    date_str = parse_date(article.get("date", ""))

    # 生成 ID
    article["id"] = article_id
    article["date"] = date_str
    article["category"] = category
    article["text"] = article_text[:2000]

    # 規則摘要（AI 翻譯由主 session 批次處理）
    summary = ai_summarize(article["title"], article_text, article["source"])
    if summary:
        article.update(summary)

    # 標記為已處理
    state["seen_ids"].append(article_id)

    return article


def run_crawl(test_mode: bool = False):
    """執行爬蟲"""
    logger.info("=" * 60)
    logger.info("🚀 Wongjai News 爬蟲 v2 啟動")
    logger.info("=" * 60)

    state = load_state()
    state["last_run"] = datetime.now(timezone(timedelta(hours=8))).isoformat()

    # 1. 爬取所有來源
    candidates = crawl_all_sources()

    # 2. 逐一處理
    processed = []
    max_process = 10 if test_mode else 50  # 測試模式 10 則，正式 50 則

    for i, article in enumerate(candidates[:max_process * 2]):  # 多看一些，篩掉不相關的
        if len(processed) >= max_process:
            break

        logger.info(f"[{i+1}/{min(len(candidates), max_process*2)}] 處理: {article['title'][:50]}...")
        result = process_article(article, state)
        if result:
            processed.append(result)
            save_article(result)

        time.sleep(0.5)  # 避免過快

    # 3. Purge 舊文章
    purge_old_articles()

    # 4. 儲存狀態
    save_state(state)

    logger.info(f"\n✅ 完成！本次新增 {len(processed)} 則新聞")

    # 5. 輸出摘要報告
    if processed:
        logger.info("\n📰 成功抓取新聞摘要：")
        logger.info("-" * 60)
        for i, a in enumerate(processed, 1):
            logger.info(f"  {i}. [{a.get('source', '?')}] {a['title'][:70]}")
            logger.info(f"     分類: {a.get('category', '?')} | 日期: {a.get('date', '?')}")
            logger.info(f"     內文長度: {len(a.get('text', ''))} 字")
        logger.info("-" * 60)

    return processed


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    if test_mode:
        logger.info("🧪 測試模式：只處理 10 則新聞")

    run_crawl(test_mode=test_mode)
