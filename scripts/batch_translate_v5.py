#!/usr/bin/env python3
"""
Batch translate news.json using MiniMax M2.7 — one API call for all articles
"""
import json, sys, os, time
from pathlib import Path

NEWS_FILE = Path("/Users/wongjai/.openclaw/workspace/wongjai-news/static/data/news.json")
API_URL = "https://api.minimaxi.chat/v1/chat/completions"

def load_api_key():
    with open('/Users/wongjai/.hermes/.env') as f:
        for line in f:
            if line.startswith('MINIMAX_API_KEY='):
                return line.split('=', 1)[1].strip()
    raise ValueError("MINIMAX_API_KEY not found")

def call_minimax(api_key, messages, max_tokens=8000):
    import urllib.request
    data = json.dumps({
        "model": "MiniMax-M2.7",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3
    }).encode()
    req = urllib.request.Request(API_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })
    resp = urllib.request.urlopen(req, timeout=300)
    result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]

def main():
    api_key = load_api_key()
    articles = json.loads(NEWS_FILE.read_text())
    print(f"📰 Loaded {len(articles)} articles")

    # Split into batches of 15
    BATCH_SIZE = 10
    all_translations = []
    total_applied = 0

    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(articles))
        batch_indices = list(range(batch_start, batch_end))
        batch = []
        for i in batch_indices:
            a = articles[i]
            batch.append({
                "id": i,
                "title_en": a.get("title_en", ""),
                "s_en": a.get("s_en", "")[:120],
            })

        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n🤖 Batch {batch_num}/{total_batches} ({len(batch)} articles)...")

        prompt = f"""Translate these {len(batch)} news articles. Output ONLY a JSON array.

For EACH article provide these fields:
- id: same as input
- title_zh: 繁體中文標題（台灣用語：晶片、軟體、資料、網路、人工智慧）
- title_zcn: 简体中文标题（中国用语：芯片、软件、数据、网络、人工智能）
- title_ja: 日本語タイトル
- title_ko: 한국어 제목
- s_zh: 繁體中文摘要 30-60字（台灣用語）
- s_zcn: 简体中文摘要 30-60字（中国用语）
- s_ja: 日本語要約 30-60字
- s_ko: 한국어 요약 30-60자

Keep company/product names in English. No markdown, just JSON.

{json.dumps(batch, ensure_ascii=False)}"""

        t0 = time.time()
        response = call_minimax(api_key, [
            {"role": "user", "content": prompt}
        ], max_tokens=4000)
        elapsed = time.time() - t0
        print(f"   {len(response)} chars in {elapsed:.1f}s")

        # Parse — skip <think> blocks and markdown
        response_clean = response.strip()
        # Remove <think>...</think> blocks (MiniMax reasoning)
        if "<think>" in response_clean:
            parts = response_clean.split("</think>")
            response_clean = parts[-1].strip() if len(parts) > 1 else response_clean
        if response_clean.startswith("```"):
            response_clean = response_clean.split("\n", 1)[1]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            response_clean = response_clean.strip()

        try:
            translations = json.loads(response_clean)
            all_translations.extend(translations)
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON error: {e}")
            print(f"   First 100: {response_clean[:100]}")
            continue

        # Apply
        for t in translations:
            idx = t.get("id", -1)
            if 0 <= idx < len(articles):
                a = articles[idx]
                for field in ["title_zh", "title_zcn", "title_ja", "title_ko",
                              "s_zh", "s_zcn", "s_ja", "s_ko"]:
                    val = t.get(field, "")
                    if val and not val.startswith("**"):
                        a[field] = val
                total_applied += 1

        print(f"   Applied: {total_applied}/{len(articles)}")
        time.sleep(1)  # Rate limit

    print(f"\n✅ Total applied: {total_applied}/{len(articles)}")

    # Save
    NEWS_FILE.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    print(f"   Saved to {NEWS_FILE}")

    # Verify
    zh_count = sum(1 for a in articles if a.get("title_zh") and not a["title_zh"].startswith("**"))
    ja_count = sum(1 for a in articles if a.get("title_ja") and not a["title_ja"].startswith("**"))
    print(f"   title_zh: {zh_count}/{len(articles)} | title_ja: {ja_count}/{len(articles)}")

if __name__ == "__main__":
    main()
