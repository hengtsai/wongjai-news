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
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsCrawler")

# ── 路徑設定 ────────────────────────────────────────────
REPO_DIR = Path("/tmp/wongjai-news")  # 改為正式環境
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
    """抓取 URL 內容"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"URL 抓取失敗: {url} — {e}")
        return ""


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
    """從文章頁面提取內文"""
    html = fetch_url(url, timeout=12)
    if not html:
        return ""

    # 移除 script/style
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 嘗試找主要內容區
    patterns = [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
        r'<main[^>]*>(.*?)</main>',
    ]

    content = ""
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            content = m.group(1)
            break

    if not content:
        content = html

    # 提取段落文字
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
    text = " ".join(re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs)
    text = re.sub(r'\s+', ' ', text).strip()

    return text[:3000]  # 限制長度


def generate_summary(title: str, article_text: str, lang: str = "en") -> str:
    """
    生成 100 字摘要。
    使用規則型摘要：取文章前 3-5 句，壓縮到 ~100 字。
    """
    if not article_text:
        return title[:100]

    # 分句
    sentences = re.split(r'[.!?。！？\n]+', article_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return title[:100]

    # 取前 3-5 句，直到 ~100 字（中文）或 ~50 詞（英文）
    summary_parts = []
    total_len = 0
    limit = 100 if lang in ("zh", "ja") else 50  # 詞數 vs 字數

    for sent in sentences[:5]:
        if lang in ("zh", "ja"):
            if total_len + len(sent) > limit:
                break
            total_len += len(sent)
        else:
            words = sent.split()
            if total_len + len(words) > limit:
                break
            total_len += len(words)
        summary_parts.append(sent)

    summary = " ".join(summary_parts) if summary_parts else sentences[0]

    # 清理
    summary = re.sub(r'\s+', ' ', summary).strip()
    if len(summary) > 150:
        summary = summary[:147] + "..."

    return summary


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
            desc = re.sub(r'<[^>]+>', '', desc_raw).strip()[:300]
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

            # 根據語言選擇標題和摘要
            title = news.get(f"title_{lang}", news.get("title_en", news["title"]))
            summary = news.get(f"summary_{lang}", news.get("summary_en", news.get("summary", "")))

            # 檔名
            date_str = now.strftime("%Y%m%d")
            filename = f"{date_str}-{nid}.md"

            # Tags
            tags = [cat_label]
            if news.get("source"):
                tags.append(news["source"])

            # Front matter
            fm = f"""---
title: {json.dumps(title, ensure_ascii=False)}
date: "{now.strftime('%Y-%m-%dT%H:%M:%S')}"
category: {json.dumps(cat_label, ensure_ascii=False)}
source: {json.dumps(news.get("source", ""), ensure_ascii=False)}
original_url: {json.dumps(news.get("url", ""), ensure_ascii=False)}
summary: {json.dumps(summary, ensure_ascii=False)}
tags: {json.dumps(tags, ensure_ascii=False)}
draft: false
---
"""

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

    for rss_url, lang, source_name in RSS_SOURCES:
        logger.info(f"  📡 抓取: {source_name} ({lang})")
        items = fetch_rss(rss_url, max_items=8)

        for item in items:
            nid = generate_id(item["title"], item["url"])

            # 跳過已見過的（但允許 6 小時後重新出現）
            if nid in seen_ids:
                continue

            seen_ids.add(nid)
            new_count += 1

            # 讀取文章內文
            article_text = extract_article_text(item["url"])

            # 生成摘要
            summary = generate_summary(item["title"], article_text, lang)

            # 分類
            category = classify_news(item["title"], item["desc"] + " " + article_text[:500])

            news = {
                "id": nid,
                "title": item["title"],
                "url": item["url"],
                "desc": item["desc"],
                "summary": summary,
                "category": category,
                "source": source_name,
                "lang": lang,
                "pub_date": item.get("pub_date", ""),
            }

            # 設定各語言版本
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

            all_news.append(news)

    # 按時間排序（新的在前）
    all_news.sort(key=lambda x: x.get("pub_date", ""), reverse=True)

    # 限制數量
    all_news = all_news[:MAX_NEWS]

    # 輸出 Hugo
    write_hugo_news(all_news)

    # 儲存狀態（只保留最近 500 個 ID）
    state["seen_ids"] = list(seen_ids)[-500:]
    state["last_run"] = datetime.now().isoformat()
    state["total_news"] = len(all_news)
    state["new_this_run"] = new_count
    save_state(state)

    logger.info(f"✅ 完成：{len(all_news)} 則新聞（新增 {new_count}），已寫入 Hugo")

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
