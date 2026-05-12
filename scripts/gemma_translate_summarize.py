#!/usr/bin/env python3
"""
Gemma-powered news translator & summarizer for Wongjai News.
Uses local Ollama instance → gemma3:27b (26B MoE).

Usage:
  python3 scripts/gemma_translate_summarize.py   # process all, update news.json
"""

import json, re, sys, time, subprocess
from pathlib import Path

OLAMA_TIMEOUT = 120  # seconds per article
BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"

# ── Gemma 3 27B MoE via Ollama ──

def gemma(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Call local Ollama gemma3:27b. Returns raw text."""
    payload = {
        "model": "gemma3:27b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": max_tokens,
        }
    }
    if system:
        payload["system"] = system

    try:
        result = subprocess.run(
            ["ollama", "run", "gemma3:27b", prompt],
            input=system + "\n\n" if system else "",
            capture_output=True, text=True, timeout=OLAMA_TIMEOUT
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("  ⚠ Timeout")
        return ""
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return ""


def translate_and_summarize(title_en: str, text_en: str, lang: str = "zh_tw") -> dict:
    """Translate EN title+text → given language, produce a 100-char summary."""
    lang_map = {
        "zh_tw": ("繁體中文", "zh-TW"),
        "zh_cn": ("简体中文", "zh-CN"),
        "en":    ("English", "en"),
        "ja":    ("日本語", "ja"),
        "ko":    ("한국어", "ko"),
    }
    lang_name, locale = lang_map.get(lang, lang_map["zh_tw"])

    system_prompt = f"""You are a professional news translator. You translate news articles accurately and produce concise summaries.
Output ONLY JSON, nothing else. No markdown, no explanation."""

    user_prompt = f"""Translate the following English news article into {lang_name} and produce a summary.

Title: {title_en}
Content: {text_en[:2000] if text_en else "(no content)"}

Return ONLY a valid JSON object with this exact structure:
{{
  "title": "translated title in {lang_name}",
  "summary": "a concise summary in {lang_name}, 80-120 characters"
}}"""

    raw = gemma(user_prompt, system=system_prompt, max_tokens=512)
    # Extract JSON from response
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"title": title_en, "summary": ""}


def process_news():
    """Load news.json, translate summaries where missing, save back."""
    if not DATA_FILE.exists():
        print(f"⚠ {DATA_FILE} not found")
        return

    data = json.loads(DATA_FILE.read_text())
    print(f"📰 Loaded {len(data)} articles")

    count = 0
    skip = 0
    for i, item in enumerate(data):
        if i >= 30:  # Limit to 30 for safety
            print(f"  🛑 Stopping at 30 articles (save time)")
            break

        # Check if summary already exists
        has_zh = bool(item.get("s_zh") or item.get("s_zh_tw"))
        has_en = bool(item.get("s_en"))
        has_ja = bool(item.get("s_ja"))
        has_ko = bool(item.get("s_ko"))

        if has_zh and has_en and has_ja and has_ko:
            skip += 1
            continue

        title_en = item.get("title_en", item.get("title", ""))
        text_en = item.get("desc", item.get("content", item.get("text", "")))

        langs = []
        if not has_zh: langs.append("zh_tw")
        if not has_en: langs.append("en")
        if not has_ja: langs.append("ja")
        if not has_ko: langs.append("ko")

        for lang in langs:
            print(f"  [{i}] Translating to {lang}: {title_en[:60]}...")
            result = translate_and_summarize(title_en, text_en, lang)
            key_map = {
                "zh_tw": ("s_zh_tw", "title_zh_tw"),
                "zh_cn": ("s_zh_cn", "title_zh_cn"),
                "en":    ("s_en",    "title_en"),
                "ja":    ("s_ja",    "title_ja"),
                "ko":    ("s_ko",    "title_ko"),
            }
            sum_key, title_key = key_map.get(lang, (None, None))
            if sum_key:
                item[sum_key] = result.get("summary", "")
            if title_key and result.get("title"):
                item[title_key] = result["title"]
            count += 1

            # Brief pause between requests
            time.sleep(2)

    if count > 0 or skip > 0:
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"\n✅ Translated: {count}, Skipped: {skip}, Total: {len(data)}")
        print(f"   Saved → {DATA_FILE}")
    else:
        print("✅ Nothing to translate — all summaries present.")


if __name__ == "__main__":
    # Verify Ollama is running
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if "gemma3" not in r.stdout.lower():
            print("⚠ gemma3:27b not found. Run: ollama pull gemma3:27b")
            sys.exit(1)
    except Exception:
        print("⚠ Ollama is not running. Run: brew services start ollama")
        sys.exit(1)

    process_news()
