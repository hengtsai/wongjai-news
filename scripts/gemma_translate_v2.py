#!/usr/bin/env python3
"""
Gemma 4 26B translator for Wongjai News — v2 (chat API, batched)
Each article: translate title+summary to zh_tw/zh_cn/ja/ko in ONE prompt
"""

import json, re, sys, time, subprocess, os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
MODEL = "gemma4:26b"
PROMPT_TIMEOUT = 1200  # 20 min max (generous for 4 langs in one call)


def ollama_chat(system: str, user: str) -> str:
    """Call ollama via subprocess with json."""
    messages = json.dumps([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])
    payload = json.dumps({
        "model": MODEL,
        "messages": json.loads(messages),
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024},
    })
    result = subprocess.run(
        ["curl", "-s", "-m", str(PROMPT_TIMEOUT),
         "http://localhost:11434/api/chat",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True, timeout=PROMPT_TIMEOUT + 10
    )
    try:
        resp = json.loads(result.stdout)
        return resp.get("message", {}).get("content", "").strip()
    except Exception:
        return ""


def translate_one_article(title_en: str, text_en: str) -> dict:
    """Translate to zh_tw/zh_cn/ja/ko in one call."""
    system = (
        "You are a professional multilingual news translator. "
        "Output ONLY valid JSON, no markdown, no explanation."
    )
    content_preview = (text_en[:800] if text_en else "(no content)")
    user = (
        f"Translate this news to 4 languages.\n"
        f"EN Title: {title_en}\n"
        f"EN Content: {content_preview}\n\n"
        f'Return ONLY a JSON object:\n'
        f'{{'
        f'  "title_zh": "traditional chinese title", "s_zh": "繁中 80 字摘要", '
        f'  "title_zcn": "simplified chinese title", "s_zcn": "簡中 80 字摘要", '
        f'  "title_ja": "japanese title", "s_ja": "日本語 80 字要約", '
        f'  "title_ko": "korean title", "s_ko": "한국어 80 자 요약",'
        f'  "s_en": "concise english summary, ~80 chars"'
        f'}}'
    )
    raw = ollama_chat(system, user)
    if not raw:
        return None
    # Extract JSON
    match = re.search(r'\{[\s\S]*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


def main():
    if not DATA_FILE.exists():
        print(f"⚠ {DATA_FILE} not found")
        sys.exit(1)

    data = json.loads(DATA_FILE.read_text())
    print(f"📰 Loaded {len(data)} articles")

    max_articles = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    to_process = []
    for i, item in enumerate(data):
        has_all = all(item.get(k) for k in ["s_zh", "s_zcn", "s_ja", "s_ko"])
        if not has_all:
            to_process.append((i, item))

    if max_articles > 0:
        to_process = to_process[:max_articles]

    print(f"🔄 Need translation: {len(to_process)} articles")
    done = 0
    errors = 0

    for idx, (i, item) in enumerate(to_process):
        title_en = item.get("title_en", item.get("title", ""))
        text_en = item.get("desc", item.get("content", item.get("text", "")))

        print(f"\n[{idx+1}/{len(to_process)}] #{i}: {title_en[:60]}... ", end="", flush=True)

        result = translate_one_article(title_en, text_en)

        if result:
            for key in ["title_zh", "s_zh", "title_zcn", "s_zcn", "title_ja", "s_ja", "title_ko", "s_ko", "s_en"]:
                if key in result and result[key]:
                    item[key] = result[key]
            done += 1
            print(f"✅ 繁:{item.get('s_zh','?')[:30]}...")
        else:
            errors += 1
            print(f"❌ (set EN fallback)")
            # Fallback: at least set en summary from title
            item["s_en"] = title_en

        time.sleep(3)  # warm down

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n{'='*60}")
    print(f"✅ Done! Translated: {done}, Errors: {errors}")
    print(f"   Saved → {DATA_FILE}")


if __name__ == "__main__":
    main()
