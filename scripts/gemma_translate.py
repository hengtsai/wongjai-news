#!/usr/bin/env python3
"""
Gemma 4 26B translator for Wongjai News (news.wongjai.com)
Uses Ollama HTTP API → gemma4:26b

Usage:
  python3 scripts/gemma_translate.py              # process all untranslated
  python3 scripts/gemma_translate.py --max 5      # process max 5 articles
"""

import json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
MODEL = "gemma4:26b"
OLLAMA_URL = "http://localhost:11434/api/generate"
REQUEST_TIMEOUT = 600  # seconds (10 min — gemma 26B needs time for CJK)

LANGS = [
    ("zh_tw", "繁體中文", "zh-TW", "s_zh", "title_zh"),
    ("zh_cn", "简体中文", "zh-CN", "s_zcn", "title_zcn"),
    ("en",    "English",  "en",    "s_en",  "title_en"),
    ("ja",    "日本語",   "ja",    "s_ja",  "title_ja"),
    ("ko",    "한국어",   "ko",    "s_ko",  "title_ko"),
]


def ollama_generate(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Call Ollama generate API."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": max_tokens,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except Exception as e:
        print(f"  ⚠ API Error: {e}")
        return ""


def translate_article(title_en: str, text_en: str, lang_code: str, lang_name: str) -> dict:
    """Translate a single article to target language, return {title, summary}."""
    system_prompt = (
        "You are a professional news translator. "
        "Translate accurately and write a concise summary (80-120 characters). "
        "Output ONLY a JSON object, no explanation, no markdown."
    )

    user_prompt = (
        f"Translate this news article to {lang_name}.\n"
        f"Title: {title_en}\n"
        f"Content: {text_en[:2000] if text_en else '(no content)'}\n\n"
        f"Return ONLY valid JSON:\n"
        f'{{"title": "translated title", "summary": "brief summary in {lang_name}"}}'
    )

    raw = ollama_generate(user_prompt, system=system_prompt, max_tokens=512)
    if not raw:
        return None

    # Extract JSON
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def process_news(max_articles: int = 0):
    if not DATA_FILE.exists():
        print(f"⚠ {DATA_FILE} not found")
        return

    data = json.loads(DATA_FILE.read_text())
    print(f"📰 Loaded {len(data)} articles")

    # Filter to EN articles that need translation
    need_en = False
    to_process = []
    for i, item in enumerate(data):
        needs_langs = []
        for lang_code, lang_name, locale, sum_key, title_key in LANGS:
            if lang_code == "en":
                en_sum = (item.get("s_en") or "").replace("&nbsp;", " ").strip()
                if not en_sum or en_sum == item.get("title_en", ""):
                    needs_langs.append((lang_code, lang_name, locale, sum_key, title_key))
            else:
                existing = (item.get(sum_key) or "").strip()
                # Check if it's still untranslated (looks like English or same as EN original)
                if not existing or is_untranslated(existing, item.get("title_en", "")):
                    needs_langs.append((lang_code, lang_name, locale, sum_key, title_key))

        if needs_langs:
            to_process.append((i, item, needs_langs))

    if max_articles > 0:
        to_process = to_process[:max_articles]

    total_tasks = sum(len(langs) for _, _, langs in to_process)
    print(f"🔄 Articles needing work: {len(to_process)}, Total translations: {total_tasks}")
    if max_articles > 0:
        print(f"⏱ Limited to {max_articles} articles")

    done = 0
    errors = 0
    for article_i, (idx, item, needed_langs) in enumerate(to_process):
        title_en = item.get("title_en", item.get("title", ""))
        text_en = get_full_text(item)

        print(f"\n[{article_i}/{len(to_process)}] #{idx}: {title_en[:70]}...")

        for lang_code, lang_name, locale, sum_key, title_key in needed_langs:
            print(f"  → {lang_name} ({lang_code})... ", end="", flush=True)
            result = translate_article(title_en, text_en, lang_code, lang_name)

            if result and result.get("summary"):
                item[sum_key] = result["summary"]
                if result.get("title"):
                    item[title_key] = result["title"]
                done += 1
                print(f"✅ {result['summary'][:40]}...")
            else:
                errors += 1
                print(f"❌")

            time.sleep(2)  # prevent Ollama overload

    # Auto-generate EN summary from title if missing
    for article_i, (idx, item, _) in enumerate(to_process):
        en_sum = (item.get("s_en") or "").replace("&nbsp;", " ").strip()
        if not en_sum or en_sum == item.get("title_en", ""):
            title = item.get("title_en", "")
            item["s_en"] = title
            print(f"  → en summary set from title")

    # Save
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n{'='*60}")
    print(f"✅ Done! Translated: {done}, Errors: {errors}")
    print(f"   Saved → {DATA_FILE}")
    print(f"   Next: cd wongjai-news && netlify deploy --prod --dir=public --site wongjai-news")


def is_untranslated(text: str, original_title: str) -> bool:
    """Check if text looks like untranslated English."""
    t = text.strip()
    if not t:
        return True
    # If >80% ASCII letters (English indicators)
    alpha_count = sum(1 for c in t if c.isascii() and c.isalpha())
    total_chars = sum(1 for c in t if c.isalnum())
    if total_chars > 0 and alpha_count / total_chars > 0.85:
        return True
    # If it's the same as the EN title
    if t == original_title:
        return True
    return False


def get_full_text(item: dict) -> str:
    """Get the best available text content."""
    for key in ["desc", "content", "text", "body"]:
        v = item.get(key)
        if v:
            return str(v)
    return ""


if __name__ == "__main__":
    max_articles = 0
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_articles = int(sys.argv[idx + 1])

    print(f"🤖 Model: {MODEL}")
    print(f"📡 Ollama: {OLLAMA_URL}")

    # Quick check
    try:
        r = urllib.request.urlopen(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=10)
        tags = json.loads(r.read())
        models = [m["name"] for m in tags.get("models", [])]
        if MODEL not in models:
            print(f"⚠ {MODEL} not found. Models: {models}")
            sys.exit(1)
        print(f"✅ {MODEL} loaded")
    except Exception as e:
        print(f"⚠ Cannot reach Ollama: {e}")
        print(f"   Fix: brew services start ollama")
        sys.exit(1)

    process_news(max_articles)
