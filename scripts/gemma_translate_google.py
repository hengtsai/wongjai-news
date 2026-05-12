#!/usr/bin/env python3
"""
Google AI Studio Gemma 4 31B translator for Wongjai News
Translates via Google AI Studio API with Gemma 4 31B model.
"""

import json, re, sys, time, urllib.request, os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={API_KEY}"
API_TIMEOUT = 1200  # 20 minutes

LANGS = [
    ("zh",    "繁體中文", "title_zh",    "s_zh"),
    ("zcn",   "简体中文", "title_zcn",   "s_zcn"),
    ("en",    "English",  "title_en",    "s_en"),
    ("ja",    "日本語",   "title_ja",    "s_ja"),
    ("ko",    "한국어",   "title_ko",    "s_ko"),
]


def google_ai_call(system: str, user: str, max_tokens: int = 512) -> str:
    """
    Call Google AI Studio Gemma 4 31B API
    """
    # Combine system and user messages into a single user prompt
    # Google API doesn't have a separate system role in v1beta, so we prepend it
    full_prompt = f"{system}\n\n{user}"
    
    payload = json.dumps({
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": max_tokens,
            "topP": 0.95,
            "topK": 40
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
    }).encode('utf-8')

    req = urllib.request.Request(API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as r:
            resp = json.loads(r.read())
            # Extract text from response
            if "candidates" in resp and len(resp["candidates"]) > 0:
                candidate = resp["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"].strip()
            # Fallback: try to find any text in response
            return json.dumps(resp)[:500]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"  ✗ HTTP {e.code}: {error_body[:200]}")
        return ""
    except Exception as e:
        print(f"  ✗ {e}")
        return ""


def main():
    data = json.loads(DATA_FILE.read_text())
    print(f"📰 {len(data)} articles loaded")

    tasks = []
    for i, item in enumerate(data):
        for code, name, tk, sk in LANGS:
            existing = (item.get(sk) or "").strip()
            # Consider it done if non-empty and not identical to English title
            if existing and existing != item.get("title_en", ""):
                continue
            tasks.append((i, item, code, name, tk, sk))

    print(f"🔄 {len(tasks)} translations needed across {len(data)} articles")

    done = 0
    failed = 0
    start = time.time()

    for idx, (i, item, code, name, tk, sk) in enumerate(tasks):
        title = item.get("title_en", "").strip()
        text = (item.get("desc", item.get("content", "")) or "")[:500]

        elapsed = time.time() - start
        avg = elapsed / (done + failed + 1) if (done + failed) > 0 else 0
        eta_min = (len(tasks) - idx) * avg / 60
        print(f"[{idx+1}/{len(tasks)}] #{i} → {name:6s}: {title[:55]}...  ETA:{eta_min:.0f}m", end=" ", flush=True)

        system = "You are a professional news translator. You must output ONLY a valid JSON object with no additional text, no explanations, no markdown. Do not include any other text outside the JSON object."
        user = (f"Translate to {name}.\nTitle: {title}\nContent: {text or '(none)'}\n"
                f'Return: {{"title":"translated title", "summary":"brief summary max 80 chars in {name}"}}\n'
                f'Output ONLY the JSON object, nothing else.')

        raw = google_ai_call(system, user)
        if raw:
            m = re.search(r'\{[\s\S]*\}', raw, re.DOTALL)
            if m:
                try:
                    r = json.loads(m.group())
                    if r.get("summary"):
                        item[sk] = r["summary"]
                        if r.get("title"):
                            item[tk] = r["title"]
                        done += 1
                        print(f"✓ {r['summary'][:40]}...")
                        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                    else:
                        failed += 1
                        print(f"✗ no summary")
                except:
                    failed += 1
                    print(f"✗ JSON parse")
            else:
                failed += 1
                print(f"✗ no JSON")
        else:
            failed += 1
            print(f"✗ timeout/error")

        time.sleep(2)  # Rate limiting

    print(f"\n{'='*60}")
    print(f"✓ Done: {done} translated, {failed} failed")
    print(f"  Total time: {(time.time()-start)/60:.1f} min")
    print(f"  Data → {DATA_FILE}")


if __name__ == "__main__":
    main()