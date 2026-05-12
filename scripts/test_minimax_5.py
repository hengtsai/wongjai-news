#!/usr/bin/env python3
"""
MiniMax abstract generation for articles with short/missing abstracts.
- Fetches article content from URL (og:description or article body)
- Uses MiniMax-M2.7 (reasoning model) for summarization via JSON in reasoning_content
- Uses MiniMax-M2.7 for translation via JSON
- Updates news.json in-place
"""
import json, re, sys, os, urllib.request, time
from pathlib import Path
from dotenv import load_dotenv

# Paths
REPO = Path("/Users/wongjai/.openclaw/workspace/wongjai-news")
NEWS_FILE = REPO / "static/data/news.json"
ENV_FILE = Path.home() / ".hermes" / ".env"

# API keys
load_dotenv(ENV_FILE)
MINIMAX_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_URL = "https://api.minimax.io/v1/text/chatcompletion_v2"

def mm_call(messages, max_tokens=300):
    """Make a MiniMax API call. Returns (ok, text_or_error)."""
    data = json.dumps({
        "model": "MiniMax-M2.7",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(MINIMAX_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINIMAX_KEY}",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        msg = result["choices"][0]["message"]
        return True, msg.get("reasoning_content", "") or msg.get("content", "")
    except Exception as e:
        return False, str(e)

def extract_json(text):
    """Extract JSON object from MiniMax reasoning_content."""
    # Try full JSON object first
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except:
            pass
    # Try finding any JSON-like structure
    m = re.search(r'"[^"]+"\s*:\s*"[^"]*"', text)
    if m:
        return {"text": m.group()}
    return None

def load_news():
    with open(NEWS_FILE) as f:
        return json.load(f)

def save_news(articles):
    with open(NEWS_FILE, "w") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def fetch_content(url, timeout=15):
    """Fetch article content from URL."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        html = resp.read().decode("utf-8", errors="ignore")

        # Try og:description
        for pattern in [
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        ]:
            m = re.search(pattern, html)
            if m:
                return m.group(1).strip()

        # Try article body
        m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
        if m:
            text = re.sub(r'<[^>]+>', '', m.group(1))
            return re.sub(r'\s+', ' ', text).strip()[:500]

        # Try paragraphs
        ps = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        if ps:
            text = ' '.join([re.sub(r'<[^>]+>', '', p) for p in ps[:5]])
            return re.sub(r'\s+', ' ', text).strip()[:500]

        return ""
    except:
        return ""

def summarize_one(title, content, word_target=80):
    """Summarize a single article. Returns summary text or None."""
    source = content[:500] if content else "(no content available)"
    prompt = f'''[SYSTEM] You must respond with ONLY valid JSON. No explanation.
{{"summary": "your {word_target}-word English summary of this article"}}

Title: {title}
Content: {source}'''

    ok, text = mm_call([{"role": "user", "content": prompt}], max_tokens=400)
    if not ok:
        print(f"   ⚠️ MiniMax error: {text}")
        return None

    j = extract_json(text)
    if j and "summary" in j:
        return j["summary"]
    # Fallback: try to extract any quoted long string
    m = re.search(r'"summary"\s*:\s*"(.{50,500}?)"', text)
    if m:
        return m.group(1)
    return None

def translate_one(text, lang_code, lang_name):
    """Translate text to target language. Returns translated text or None."""
    prompt = f'''[SYSTEM] You must respond with ONLY valid JSON. No explanation.
{{"translation": "your translation in {lang_name}"}}

Text: {text[:300]}'''

    ok, response = mm_call([{"role": "user", "content": prompt}], max_tokens=400)
    if not ok:
        return None

    j = extract_json(response)
    if j and "translation" in j:
        return j["translation"]
    m = re.search(r'"translation"\s*:\s*"(.{10,500}?)"', response)
    if m:
        return m.group(1)
    return None

def main():
    print("=" * 60)
    print("MiniMax Abstract + Translation (5 articles)")
    print("=" * 60)

    articles = load_news()

    # Find 5 articles with shortest abstracts
    short_idx = sorted(range(len(articles)),
                       key=lambda i: len(articles[i].get("s_en", "").split()))[:5]

    print(f"\n📋 Selected {len(short_idx)} articles:\n")
    for idx in short_idx:
        a = articles[idx]
        print(f"  [{len(a.get('s_en','').split()):2d} words] {a['title_en'][:70]}")

    # Step 1: Fetch content from URLs
    print("\n🌐 Fetching content from URLs...")
    contents = {}
    for idx in short_idx:
        a = articles[idx]
        content = fetch_content(a["url"])
        if not content:
            content = a.get("content", "") or a.get("s_en", "")
        contents[idx] = content
        status = "✓" if len(content) > 50 else "⚠️"
        print(f"   [{status}] {a['title_en'][:55]} ({len(content)} chars)")

    # Step 2: Summarize with MiniMax
    print("\n🤖 MiniMax summarization...")
    summaries_en = {}
    for idx in short_idx:
        a = articles[idx]
        print(f"   Processing: {a['title_en'][:55]}...")
        summary = summarize_one(a["title_en"], contents[idx])
        if summary:
            summaries_en[idx] = summary
            print(f"      ✓ {len(summary.split())} words: {summary[:60]}...")
        else:
            print(f"      ⚠️ Failed")
        time.sleep(0.5)

    # Step 3: Translate with MiniMax
    lang_map = [
        ("s_zh", "Traditional Chinese (Taiwan, use 臺灣 not China terms)"),
        ("s_zcn", "Simplified Chinese (Mainland China)"),
        ("s_ja", "Japanese"),
        ("s_ko", "Korean"),
    ]

    print("\n🌏 MiniMax translation...")
    for lang_code, lang_name in lang_map:
        ok_count = 0
        for idx in short_idx:
            if idx not in summaries_en:
                continue
            trans = translate_one(summaries_en[idx], lang_code, lang_name)
            if trans:
                articles[idx][lang_code] = trans
                ok_count += 1
            time.sleep(0.3)
        print(f"   {lang_code}: {ok_count}/{len(summaries_en)} OK")

    # Step 4: Update English summaries
    for idx, summary in summaries_en.items():
        articles[idx]["s_en"] = summary

    save_news(articles)

    # Step 5: Results
    print("\n" + "=" * 60)
    print("✅ Final Results:")
    print("=" * 60)
    for idx in short_idx:
        a = articles[idx]
        w = len(a.get('s_en', '').split())
        print(f"\n  [{w:2d} words] {a['title_en'][:65]}")
        print(f"     EN: {a.get('s_en', '')[:90]}")
        zh = a.get('s_zh', '')
        print(f"     ZH: {zh[:70]}..." if len(zh) > 70 else f"     ZH: {zh}")

if __name__ == "__main__":
    main()
