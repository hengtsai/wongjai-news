#!/usr/bin/env python3
"""
news_crawler.py — Wongjai News 爬蟲
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
功能：
1. 從多來源抓取新聞（RSS + 網頁爬取）
2. 逐篇讀取文章內文
3. AI 生成 100 字摘要（使用本地 LLM 或摘要規則）
4. 自動分類
5. 生成 4 語言版本的 Hugo markdown
6. 限制每則新聞最多 100 則，超過 purge
7. 每 10 分鐘執行一次

作者: Wongjai ⚡ Agent Team
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import List, Dict, Optional, Tuple
import logging
from bs4 import BeautifulSoup
import unicodedata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsCrawler")

# ── 路徑設定 ────────────────────────────────────────────
REPO_DIR = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
CONTENT_DIR = REPO_DIR / "content"
STATE_FILE = REPO_DIR / "scripts" / "crawler_state.json"
MAX_NEWS = 100

# ── 分類規則 ─────────────────────────────────────────────
CATEGORIES = {
    "AI": [
        "artificial intelligence", "ai", "llm", "gpt", "claude", "gemini",
        "machine learning", "deep learning", "neural", "openai", "anthropic",
        "generative ai", "chatbot", "transformer", "人工智慧", "機器學習",
        "大型語言模型", "深度學習",
    ],
    "半導體": [
        "semiconductor", "chip", "tsmc", "nvidia", "amd", "intel", "qualcomm",
        "台積電", "聯發科", "晶圓", "晶片", "製程", "封裝", "光刻",
        "asml", "三星半導體", "foundry", "wafer",
    ],
    "自駕/電動車": [
        "electric vehicle", "ev", "tesla", "autonomous", "self-driving",
        "電動車", "自駕", "自動駕駛", "充電", "電池", "lithium",
        "byd", "nio", "rivian", "waymo", "lidar",
    ],
    "經濟": [
        "economy", "gdp", "inflation", "interest rate", "federal reserve",
        "fed", "recession", "tariff", "trade war", "stock market", "wall street",
        "經濟", "通膨", "利率", "央行", "股市", "關稅", "貿易戰",
        "金融", "bank", "貨幣", "匯率", "cpi", "ppi",
    ],
    "科技": [
        "apple", "google", "microsoft", "amazon", "meta", "samsung",
        "cloud", "saas", "cybersecurity", "quantum", "blockchain",
        "科技", "雲端", "資安", "量子", "5g", "6g", "iot",
    ],
    "地緣政治": [
        "geopolitical", "war", "military", "china", "taiwan", "iran",
        "israel", "russia", "ukraine", "nato", "missile", "nuclear",
        "地緣政治", "軍事", "戰爭", "飛彈", "核武", "台海",
        "南海", "中東", "制裁",
    ],
    "日本": [
        "japan", "tokyo", "nikkei", "boj", "sony", "toyota", "nintendo",
        "日本", "東京", "日經", "日銀", "任天堂", "豐田", "索尼",
        "softbank", "jpy", "yen",
    ],
}

# ── 新聞來源（RSS）─────────────────────────────────────
RSS_SOURCES = [
    # 國際財經
    ("https://news.google.com/rss/search?q=AI+semiconductor+tech+stock&hl=en-US&gl=US&ceid=US:en", "en", "Google News"),
    ("https://news.google.com/rss/search?q=federal+reserve+economy+GDP&hl=en-US&gl=US&ceid=US:en", "en", "Google News"),
    ("https://news.google.com/rss/search?q=Tesla+EV+autonomous+driving&hl=en-US&gl=US&ceid=US:en", "en", "Google News"),
    ("https://news.google.com/rss/search?q=TSMC+NVIDIA+semiconductor+chip&hl=en-US&gl=US&ceid=US:en", "en", "Google News"),
    ("https://news.google.com/rss/search?q=geopolitics+Iran+Taiwan+China+military&hl=en-US&gl=US&ceid=US:en", "en", "Google News"),
    # 中文新聞
    ("https://news.google.com/rss/search?q=%E5%8F%B0%E7%A9%8D%E9%9B%BB+%E5%8D%8A%E5%B0%8E%E9%AB%94&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "zh", "Google News"),
    ("https://news.google.com/rss/search?q=%E8%82%A1%E5%B8%82+%E7%B6%93%E6%BF%9F+%E6%8A%95%E8%B3%87&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "zh", "Google News"),
    ("https://news.google.com/rss/search?q=%E9%9B%BB%E5%8B%95%E8%BB%8A+%E7%89%B9%E6%96%AF%E6%8B%89+%E8%87%AA%E9%A7%95&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "zh", "Google News"),
    ("https://news.google.com/rss/search?q=AI+%E4%BA%BA%E5%B7%A5%E6%99%BA%E6%85%A7+%E5%A4%A7%E6%A8%A1%E5%9E%8B&hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "zh", "Google News"),
    # 科技新報
    ("https://technews.tw/feed/", "zh", "科技新報"),
    # 日文
    ("https://news.google.com/rss/search?q=%E3%83%88%E3%83%A8%E3%82%BF+%E3%82%BD%E3%83%8B%E3%83%BC+%E5%8D%8A%E5%B0%8E%E4%BD%93&hl=ja&gl=JP&ceid=JP:ja", "ja", "Google News"),
    ("https://news.google.com/rss/search?q=AI+%E4%BA%BA%E5%B7%A5%E7%9F%A5%E8%83%BD&hl=ja&gl=JP&ceid=JP:ja", "ja", "Google News"),
]


# ═══════════════════════════════════════════════════════════
#  工具函數
# ═══════════════════════════════════════════════════════════

def fetch_url(url: str, timeout: int = 15) -> str:
    """抓取 URL 內容（自動跟隨重定向）"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7,ja;q=0.6",
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"URL 抓取失敗: {url} — {e}")
        return ""


def resolve_google_news_url(url: str) -> str:
    """解析 Google News 重定向 URL，取得真正的文章連結

    策略：
    1. 跟隨 HTTP 301/302 重定向
    2. 從 HTML 頁面提取 canonical/meta refresh URL
    3. 嘗試解碼 Google News protobuf 格式
    """
    if "news.google.com" not in url:
        return url

    # 方法 1：跟隨 HTTP 重定向（可能有 301/302）
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        resp = urllib.request.urlopen(req, timeout=10)
        final_url = resp.geturl()
        if final_url != url and "news.google.com" not in final_url:
            logger.debug(f"  🔗 HTTP 重定向: {final_url[:80]}")
            return final_url

        # 方法 2：從 HTML 提取重定向目標
        html = resp.read().decode("utf-8", errors="replace")[:8000]

        # 嘗試找 meta refresh
        m = re.search(r'<meta[^>]*http-equiv="refresh"[^>]*content="[^"]*url=([^"]+)"', html, re.IGNORECASE)
        if m:
            resolved = m.group(1).replace("&amp;", "&")
            if "news.google.com" not in resolved:
                logger.debug(f"  🔗 meta refresh: {resolved[:80]}")
                return resolved

        # 嘗試找 canonical URL
        m = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"', html, re.IGNORECASE)
        if m:
            resolved = m.group(1)
            if "news.google.com" not in resolved:
                logger.debug(f"  🔗 canonical: {resolved[:80]}")
                return resolved

        # 方法 3：找 JavaScript 重定向
        # Google News 新版用 JS: window.location = "..."
        m = re.search(r'window\.location\s*=\s*["\']([^"\']+)["\']', html)
        if m:
            resolved = m.group(1)
            if "news.google.com" not in resolved:
                logger.debug(f"  🔗 JS redirect: {resolved[:80]}")
                return resolved

        # 方法 4：找 data- 屬性中的 URL
        m = re.search(r'data-(?:url|href|article)="(https?://(?!news\.google\.com)[^"]+)"', html)
        if m:
            resolved = m.group(1)
            logger.debug(f"  🔗 data attr: {resolved[:80]}")
            return resolved

    except Exception as e:
        logger.debug(f"  Google News 重定向失敗: {e}")

    return url


def generate_id(title: str, url: str) -> str:
    """生成新聞唯一 ID"""
    raw = f"{title}|{url}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def classify_news(title: str, desc: str) -> str:
    """根據標題和摘要分類"""
    text = f"{title} {desc}".lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return "科技"  # 預設分類


def extract_article_text(url: str) -> str:
    """從文章頁面提取內文 — 使用 BeautifulSoup 精準提取

    優先級：
    1. <article> 標籤
    2. <main> 標籤
    3. class 包含 content/article/post-body/story 的 div
    4. 全頁段落 fallback
    排除：nav, header, footer, aside, sidebar, ad, comment, related
    """
    html = fetch_url(url, timeout=15)
    if not html:
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning(f"BeautifulSoup 解析失敗: {url} — {e}")
        # Fallback: 簡單 regex
        return _extract_text_regex(html)

    # 移除不需要的元素
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside",
                               "iframe", "noscript", "svg"]):
        tag.decompose()

    # 移除廣告/側邊欄/評論/相關推薦
    ad_keywords = ["ad-", "-ad", "ads-", "sidebar", "comment", "related",
                    "recommend", "share", "social", "widget", "popup",
                    "newsletter", "subscribe", "cookie", "breadcrumb",
                    "author-bio", "tag-list", "prev-next", "pagination"]
    for el in soup.find_all(True):
        if not el.attrs:
            continue
        classes = el.get("class") or []
        if not classes:
            continue
        classes_str = " ".join(str(c) for c in classes)
        if any(kw in classes_str.lower() for kw in ad_keywords):
            el.decompose()

    # 按優先級找主要內容
    content_el = None

    # 1. <article>
    content_el = soup.find("article")
    if content_el:
        logger.debug(f"  → 使用 <article> 標籤")

    # 2. <main>
    if not content_el:
        content_el = soup.find("main")
        if content_el:
            logger.debug(f"  → 使用 <main> 標籤")

    # 3. class 包含特定關鍵字的 div
    if not content_el:
        content_keywords = ["entry-content", "post-content", "article-body",
                           "article__content", "article__body", "post-body",
                           "story-body", "news-content", "main-content",
                           "article-content", "content-body"]
        for kw in content_keywords:
            try:
                div = soup.find("div", class_=lambda c: c and any(kw in str(cls).lower() for cls in (c if isinstance(c, list) else [c]))
                              if c else False)
                if div:
                    content_el = div
                    logger.debug(f"  → 使用 div.{kw}")
                    break
            except (TypeError, AttributeError):
                continue
        # 更寬鬆的搜索：只要 class 名包含 "content" 或 "article"
        if not content_el:
            for div in soup.find_all("div"):
                classes = div.get("class")
                if not classes:
                    continue
                classes_str = " ".join(str(c) for c in classes)
                if any(kw in classes_str.lower() for kw in ["content", "article", "story"]):
                    # 確認段落數量足夠
                    p_count = len(div.find_all("p", recursive=True))
                    if p_count >= 3:
                        content_el = div
                        logger.debug(f"  → 使用 div (class={classes_str}, {p_count} paragraphs)")
                        break

    # 提取段落
    if content_el:
        paragraphs = content_el.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    # 清理段落文字
    texts = []
    for p in paragraphs:
        # 移除段落內的 script/style 殘留
        for bad in p.find_all(["script", "style"]):
            bad.decompose()
        text = p.get_text(separator=" ", strip=True)
        if len(text) > 15:  # 過濾太短的段落（通常是導航或廣告）
            texts.append(text)

    result = " ".join(texts)
    result = re.sub(r'\s+', ' ', result).strip()

    if len(result) < 50:
        # 文字太少，嘗試全頁提取
        return _extract_text_regex(html)

    return result[:3000]


def _extract_text_regex(html: str) -> str:
    """後備方案：用正則表達式提取文字"""
    # 移除 script/style
    cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # 提取段落
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', cleaned, re.DOTALL | re.IGNORECASE)
    text = " ".join(re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs if len(p.strip()) > 15)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:3000]


def _extract_keywords(text: str, lang: str = "en") -> set:
    """從文字中提取關鍵詞（停用詞過濾）"""
    stopwords_en = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                   "being", "have", "has", "had", "do", "does", "did", "will",
                   "would", "could", "should", "may", "might", "can", "shall",
                   "to", "of", "in", "for", "on", "with", "at", "by", "from",
                   "as", "into", "through", "during", "before", "after", "above",
                   "below", "between", "out", "off", "over", "under", "again",
                   "further", "then", "once", "here", "there", "when", "where",
                   "why", "how", "all", "each", "every", "both", "few", "more",
                   "most", "other", "some", "such", "no", "nor", "not", "only",
                   "own", "same", "so", "than", "too", "very", "just", "also",
                   "about", "up", "it", "its", "this", "that", "these", "those",
                   "and", "but", "or", "if", "while", "they", "them", "their",
                   "he", "him", "his", "she", "her", "we", "us", "our", "you",
                   "your", "who", "which", "what", "said", "says", "new", "one",
                   "two", "first", "last", "like", "get", "got", "make", "made"}

    stopwords_zh = {"的", "了", "是", "在", "和", "有", "被", "這", "那", "你",
                    "我", "他", "她", "它", "們", "個", "為", "以", "與", "及",
                    "從", "但", "或", "而", "且", "也", "都", "就", "要", "會",
                    "能", "可以", "將", "到", "來", "去", "上", "下", "中", "內",
                    "外", "前", "後", "等", "其", "所", "之", "由", "已", "於",
                    "更", "很", "最", "不", "沒", "無", "多", "少", "大", "小"}

    stopwords_ja = {"の", "は", "を", "に", "が", "で", "と", "も", "た", "て",
                    "し", "れ", "さ", "ある", "いる", "する", "なる", "この",
                    "その", "あの", "どの", "これ", "それ", "あれ", "どれ",
                    "から", "まで", "より", "など", "また", "しかし", "ため"}

    text = text.lower()
    if lang == "en":
        words = set(re.findall(r'[a-z]{3,}', text))
        return words - stopwords_en
    elif lang == "ja":
        # 日文：取 2+ 字元的片語
        chars = set(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,}', text))
        return chars - stopwords_ja
    else:
        # 中文：取 2+ 字元的片語
        words = set(re.findall(r'[\u4e00-\u9fff]{2,}', text))
        return words - stopwords_zh


def generate_summary(title: str, article_text: str, lang: str = "en") -> str:
    """
    生成 ~100 字摘要（關鍵詞匹配法）。

    方法：
    1. 從標題提取關鍵詞
    2. 將文章分句
    3. 計算每句與標題的關鍵詞重疊度
    4. 取重疊度最高的 2-3 句，組合成摘要
    5. 確保摘要通順、不超過 ~100 字（中文）或 ~60 詞（英文）
    """
    if not article_text:
        return title[:100]

    title_kw = _extract_keywords(title, lang)

    # 分句
    if lang == "en":
        sentences = re.split(r'(?<=[.!?])\s+', article_text)
    elif lang == "ja":
        sentences = re.split(r'[。！？\n]+', article_text)
    else:
        sentences = re.split(r'[。！？\n]+', article_text)

    # 過濾太短的句子
    min_len = 15 if lang in ("zh", "ja") else 30
    sentences = [s.strip() for s in sentences if len(s.strip()) >= min_len]

    if not sentences:
        return _truncate_summary(article_text[:200], lang)

    # 計算每句的分數（關鍵詞重疊 + 位置權重）
    scored: List[Tuple[float, int, str]] = []
    for i, sent in enumerate(sentences[:20]):  # 只看前 20 句
        sent_kw = _extract_keywords(sent, lang)
        overlap = len(title_kw & sent_kw)

        # 位置權重：越前面的句子分數越高
        position_bonus = max(0, 5 - i) * 0.3

        # 長度懲罰：太長的句子扣分
        length_penalty = 0.1 if len(sent) > 200 else 0

        score = overlap + position_bonus - length_penalty
        scored.append((score, i, sent))

    # 按分數排序，取最高分的 2-3 句
    scored.sort(key=lambda x: (-x[0], x[1]))

    # 選取句子（保留原始順序）
    selected_indices = []
    for _, idx, _ in scored[:4]:  # 最多考慮 4 句
        selected_indices.append(idx)
    selected_indices.sort()  # 按原始順序排列

    # 組合摘要
    summary_parts = []
    total_len = 0
    char_limit = 120 if lang in ("zh", "ja") else 70  # 字數/詞數限制

    for idx in selected_indices[:3]:  # 最多取 3 句
        sent = sentences[idx]
        if lang in ("zh", "ja"):
            if total_len + len(sent) > char_limit:
                break
            total_len += len(sent)
        else:
            word_count = len(sent.split())
            if total_len + word_count > char_limit:
                break
            total_len += word_count
        summary_parts.append(sent)

    if not summary_parts:
        # 沒選到合適句子，取前兩句
        summary_parts = sentences[:2]

    summary = " ".join(summary_parts) if lang == "en" else "".join(summary_parts)

    return _truncate_summary(summary, lang)


def _truncate_summary(text: str, lang: str) -> str:
    """截斷摘要到合理長度，清理 HTML 實體"""
    # 清理 HTML 實體
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r'\s+', ' ', text).strip()

    if lang in ("zh", "ja"):
        if len(text) > 130:
            text = text[:127] + "..."
    else:
        words = text.split()
        if len(words) > 70:
            text = " ".join(words[:67]) + "..."
    return text.strip()


# ═══════════════════════════════════════════════════════════
#  翻譯（簡易 key-based）
# ═══════════════════════════════════════════════════════════

CATEGORY_I18N = {
    "zh-tw": {"AI": "AI", "半導體": "半導體", "自駕/電動車": "自駕/電動車", "經濟": "經濟", "科技": "科技", "地緣政治": "地緣政治", "日本": "日本"},
    "zh-cn": {"AI": "AI", "半導體": "半导体", "自駕/電動車": "自驾/电动车", "經濟": "经济", "科技": "科技", "地緣政治": "地缘政治", "日本": "日本"},
    "ja":    {"AI": "AI", "半導體": "半導体", "自駕/電動車": "自動運転/電気自動車", "經濟": "経済", "科技": "テクノロジー", "地緣政治": "地政学", "日本": "日本"},
    "en":    {"AI": "AI", "半導體": "Semiconductor", "自駕/電動車": "EV/Autonomous", "經濟": "Economy", "科技": "Tech", "地緣政治": "Geopolitics", "日本": "Japan"},
}


# ═══════════════════════════════════════════════════════════
#  RSS 抓取
# ═══════════════════════════════════════════════════════════

def fetch_rss(url: str, max_items: int = 10) -> List[Dict]:
    """從 RSS 抓取新聞列表"""
    items = []
    try:
        xml_text = fetch_url(url, timeout=12)
        if not xml_text:
            return items

        root = ET.fromstring(xml_text)
        for item in root.findall(".//item")[:max_items]:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")

            if title_el is None or title_el.text is None:
                continue

            title = title_el.text.strip()
            link = link_el.text.strip() if link_el is not None and link_el.text else ""
            desc_raw = desc_el.text if desc_el is not None and desc_el.text else ""
            desc = re.sub(r'<[^>]+>', '', desc_raw)
            # 清理 HTML 實體
            desc = desc.replace("&nbsp;", " ").replace("&amp;", "&")
            desc = desc.replace("&lt;", "<").replace("&gt;", ">")
            desc = desc.replace("&quot;", '"').replace("&#39;", "'")
            desc = re.sub(r'\s+', ' ', desc).strip()[:300]
            pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

            items.append({
                "title": title,
                "url": link,
                "desc": desc,
                "pub_date": pub_date,
            })

    except Exception as e:
        logger.warning(f"RSS 解析失敗: {url} — {e}")

    return items


# ═══════════════════════════════════════════════════════════
#  狀態管理
# ═══════════════════════════════════════════════════════════

def load_state() -> Dict:
    """載入爬蟲狀態"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen_ids": [], "last_run": None}


def save_state(state: Dict):
    """儲存爬蟲狀態"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
#  Hugo 輸出
# ═══════════════════════════════════════════════════════════

def write_hugo_news(news_list: List[Dict]):
    """為每個語言版本生成 Hugo markdown"""
    now = datetime.now()

    for lang in ["zh-tw", "zh-cn", "ja", "en"]:
        news_dir = CONTENT_DIR / lang / "news"
        news_dir.mkdir(parents=True, exist_ok=True)

        # 清除舊檔案
        for f in news_dir.glob("*.md"):
            f.unlink()

        cat_labels = CATEGORY_I18N.get(lang, CATEGORY_I18N["zh-tw"])

        # 只保留最多 MAX_NEWS 則
        for i, news in enumerate(news_list[:MAX_NEWS]):
            nid = news["id"]
            cat = news["category"]
            cat_label = cat_labels.get(cat, cat)

            # 根據語言選擇主標題和摘要
            title = news.get(f"title_{lang}", news.get("title_en", news["title"]))
            summary = news.get(f"summary_{lang}", news.get("summary_en", news.get("summary", "")))

            # 檔名
            date_str = now.strftime("%Y%m%d")
            filename = f"{date_str}-{nid}.md"

            # Tags
            tags = [cat_label]
            if news.get("source"):
                tags.append(news["source"])

            # Front matter — 包含所有語言版本
            fm_lines = ["---"]
            fm_lines.append(f'title: {json.dumps(title, ensure_ascii=False)}')
            fm_lines.append(f'date: "{now.strftime("%Y-%m-%dT%H:%M:%S")}"')

            # 所有語言的標題
            fm_lines.append(f'title_original: {json.dumps(news["title"], ensure_ascii=False)}')
            fm_lines.append(f'title_en: {json.dumps(news.get("title_en", news["title"]), ensure_ascii=False)}')
            fm_lines.append(f'title_zh_tw: {json.dumps(news.get("title_zh-tw", news["title"]), ensure_ascii=False)}')
            fm_lines.append(f'title_zh_cn: {json.dumps(news.get("title_zh-cn", news["title"]), ensure_ascii=False)}')
            fm_lines.append(f'title_ja: {json.dumps(news.get("title_ja", news["title"]), ensure_ascii=False)}')

            # 所有語言的摘要
            orig_summary = news.get("summary", "")
            fm_lines.append(f'summary: {json.dumps(summary, ensure_ascii=False)}')
            fm_lines.append(f'summary_original: {json.dumps(orig_summary, ensure_ascii=False)}')
            fm_lines.append(f'summary_en: {json.dumps(news.get("summary_en", orig_summary), ensure_ascii=False)}')
            fm_lines.append(f'summary_zh_tw: {json.dumps(news.get("summary_zh-tw", orig_summary), ensure_ascii=False)}')
            fm_lines.append(f'summary_zh_cn: {json.dumps(news.get("summary_zh-cn", orig_summary), ensure_ascii=False)}')
            fm_lines.append(f'summary_ja: {json.dumps(news.get("summary_ja", orig_summary), ensure_ascii=False)}')

            # 其他欄位
            fm_lines.append(f'category: {json.dumps(cat_label, ensure_ascii=False)}')
            fm_lines.append(f'source: {json.dumps(news.get("source", ""), ensure_ascii=False)}')
            fm_lines.append(f'original_url: {json.dumps(news.get("url", ""), ensure_ascii=False)}')
            fm_lines.append(f'original_lang: {json.dumps(news.get("lang", ""), ensure_ascii=False)}')
            fm_lines.append(f'tags: {json.dumps(tags, ensure_ascii=False)}')
            fm_lines.append('draft: false')
            fm_lines.append('---')

            fm = "\n".join(fm_lines) + "\n"

            filepath = news_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(fm)

    logger.info(f"✅ 已寫入 {min(len(news_list), MAX_NEWS)} 則新聞 x 4 語言")


# ═══════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════

def crawl():
    """主爬蟲流程"""
    logger.info("🕷️ Wongjai News 爬蟲啟動")

    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    all_news = []
    new_count = 0
    article_count = 0
    summary_count = 0

    for rss_url, lang, source_name in RSS_SOURCES:
        logger.info(f"  📡 抓取: {source_name} ({lang})")
        items = fetch_rss(rss_url, max_items=8)

        for item in items:
            nid = generate_id(item["title"], item["url"])

            # 跳過已見過的
            if nid in seen_ids:
                continue

            seen_ids.add(nid)
            new_count += 1

            # 解析 Google News 重定向 URL
            real_url = resolve_google_news_url(item["url"])

            # 判斷是否為 Google News 連結（無法解析時用 RSS 描述）
            is_google_news = "news.google.com" in real_url

            # 讀取文章全文
            article_text = ""
            if not is_google_news:
                article_text = extract_article_text(real_url)

            # 如果全文不足，用 RSS 描述作為後備
            if not article_text or len(article_text) < 30:
                article_text = item.get("desc", "")
                if is_google_news:
                    real_url = item["url"]  # 保留原始 Google News URL

            if article_text and len(article_text) > 50 and not is_google_news:
                article_count += 1
                logger.debug(f"  📖 全文: {len(article_text)} 字 — {item['title'][:40]}")
            else:
                logger.debug(f"  📎 RSS 描述: {item['title'][:40]}")

            # 生成高品質摘要（關鍵詞匹配法）
            summary = generate_summary(item["title"], article_text, lang)
            if summary:
                summary_count += 1

            # 分類
            category = classify_news(item["title"], item["desc"] + " " + (article_text[:500] if article_text else ""))

            news = {
                "id": nid,
                "title": item["title"],
                "url": real_url,
                "desc": item["desc"],
                "summary": summary,
                "article_text": article_text[:1500] if article_text else "",  # 保留部分全文（存 JSON 用）
                "category": category,
                "source": source_name,
                "lang": lang,
                "pub_date": item.get("pub_date", ""),
            }

            # 設定各語言版本的標題和摘要
            # 原文直接作為該語言的值
            if lang == "en":
                news["title_en"] = item["title"]
                news["summary_en"] = summary
            elif lang == "zh":
                news["title_zh-tw"] = item["title"]
                news["summary_zh-tw"] = summary
                news["title_zh-cn"] = item["title"]  # 簡體需要轉換，暫用繁體
                news["summary_zh-cn"] = summary
            elif lang == "ja":
                news["title_ja"] = item["title"]
                news["summary_ja"] = summary

            # 其他語言暫時用原文（未來可由 AI cron job 翻譯）
            for target_lang in ["title_en", "title_zh-tw", "title_zh-cn", "title_ja"]:
                if target_lang not in news:
                    news[target_lang] = item["title"]
            for target_lang in ["summary_en", "summary_zh-tw", "summary_zh-cn", "summary_ja"]:
                if target_lang not in news:
                    news[target_lang] = summary

            all_news.append(news)

    # 按時間排序（新的在前）
    all_news.sort(key=lambda x: x.get("pub_date", ""), reverse=True)

    # 限制數量
    all_news = all_news[:MAX_NEWS]

    # 移除 article_text 欄位（不存到 Hugo，但保留 JSON 中）
    for news in all_news:
        news.pop("article_text", None)

    # 輸出 Hugo
    write_hugo_news(all_news)

    # 儲存狀態（只保留最近 500 個 ID）
    state["seen_ids"] = list(seen_ids)[-500:]
    state["last_run"] = datetime.now().isoformat()
    state["total_news"] = len(all_news)
    state["new_this_run"] = new_count
    save_state(state)

    logger.info(f"✅ 完成：{len(all_news)} 則新聞（新增 {new_count}）")
    logger.info(f"   📖 全文提取成功: {article_count}/{new_count}")
    logger.info(f"   📝 摘要生成成功: {summary_count}/{new_count}")

    return all_news


def deploy():
    """Hugo build + Netlify deploy"""
    logger.info("🚀 開始部署...")

    try:
        # Hugo build
        result = subprocess.run(
            ["hugo", "--gc", "--minify"],
            cwd=str(REPO_DIR),
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            logger.error(f"Hugo build 失敗: {result.stderr}")
            return False

        # Netlify deploy
        result = subprocess.run(
            ["netlify", "deploy", "--prod", "--dir=public", "--site", "wongjai-news", "--no-build"],
            cwd=str(REPO_DIR),
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            logger.error(f"Netlify deploy 失敗: {result.stderr}")
            return False

        logger.info("✅ 部署成功！")
        return True

    except Exception as e:
        logger.error(f"❌ 部署錯誤: {e}")
        return False


def main():
    """主程式入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Wongjai News 爬蟲")
    parser.add_argument("--crawl-only", action="store_true", help="只爬取不部署")
    parser.add_argument("--deploy-only", action="store_true", help="只部署不爬取")
    args = parser.parse_args()

    if args.deploy_only:
        deploy()
    elif args.crawl_only:
        crawl()
    else:
        crawl()
        deploy()


if __name__ == "__main__":
    main()
