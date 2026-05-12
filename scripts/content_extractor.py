#!/usr/bin/env python3
"""
新聞全文抓取模組
用 readability-lxml + BeautifulSoup 從 URL 提取乾淨文章內容
"""
import requests
from readability import Document
from bs4 import BeautifulSoup
import re, time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8",
}

TIMEOUT = 15
MAX_CONTENT = 5000  # 最多保留字數


def extract_content(url: str, max_chars: int = MAX_CONTENT) -> dict:
    """
    從 URL 抓取文章全文。
    回傳: {"title": str, "content": str, "success": bool, "error": str}
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()

        # readability 提取主要內容
        doc = Document(resp.text)
        title = doc.title()

        # BeautifulSoup 清理 HTML → 純文字
        content_html = doc.summary()
        soup = BeautifulSoup(content_html, "lxml")

        # 移除不需要的元素
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # 清理多餘空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        # 截斷
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(' ', 1)[0] + "..."

        return {
            "title": title,
            "content": text,
            "success": True,
            "error": "",
        }

    except requests.exceptions.Timeout:
        return {"title": "", "content": "", "success": False, "error": "timeout"}
    except requests.exceptions.HTTPError as e:
        return {"title": "", "content": "", "success": False, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"title": "", "content": "", "success": False, "error": str(e)[:100]}


def extract_batch(urls: list, delay: float = 0.5) -> list:
    """
    批次抓取多個 URL。
    回傳: [{"url": str, "title": str, "content": str, "success": bool}, ...]
    """
    results = []
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay)  # 避免被 ban
        result = extract_content(url)
        result["url"] = url
        results.append(result)
        status = "✅" if result["success"] else "❌"
        print(f"  {status} [{i+1}/{len(urls)}] {result.get('title', url)[:60]}")
    return results


if __name__ == "__main__":
    import json, sys

    if len(sys.argv) > 1:
        # 單一 URL 測試
        url = sys.argv[1]
        result = extract_content(url)
        print(f"Title: {result['title']}")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Content ({len(result['content'])} chars):")
            print(result['content'][:2000])
        else:
            print(f"Error: {result['error']}")
    else:
        # 從 RSS 取文章測試
        import feedparser
        feeds = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://technews.tw/feed/",
        ]
        urls = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                urls.append(feed.entries[0].link)

        print(f"Testing {len(urls)} URLs from RSS...\n")
        results = extract_batch(urls)
        success = sum(1 for r in results if r['success'])
        print(f"\nResult: {success}/{len(results)} succeeded")
