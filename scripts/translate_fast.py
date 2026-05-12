#!/usr/bin/env python3
"""
快速翻譯前 N 篇文章（測試用）
"""
import json, re, sys, time, urllib.request, os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
MODEL = "gemma4:26b"
OLLAMA = "http://localhost:11434/api/chat"
API_TIMEOUT = 1200  # 20 minutes

LANGS = [
    ("zh",    "繁體中文", "title_zh",    "s_zh"),
    ("zcn",   "简体中文", "title_zcn",   "s_zcn"),
    ("en",    "English",  "title_en",    "s_en"),
    ("ja",    "日本語",   "title_ja",    "s_ja"),
    ("ko",    "한국어",   "title_ko",    "s_ko"),
]

MAX_ARTICLES = 5  # 只翻譯前 5 篇

def ollama_call(system: str, user: str, max_tokens: int = 512) -> str:
    payload = json.dumps({
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"temperature": 0.3, "num_predict": max_tokens},
    }).encode()

    req = urllib.request.Request(OLLAMA, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as r:
            resp = json.loads(r.read())
            return resp.get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"  ✗ {e}")
        return ""

def main():
    data = json.loads(DATA_FILE.read_text())
    # 只取前 MAX_ARTICLES 篇
    data = data[:MAX_ARTICLES]
    print(f"📰 只處理前 {len(data)} 篇文章")
    
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

        system = f"You are a professional news translator. Output ONLY valid JSON. No markdown."
        user = (f"Translate to {name}.\nTitle: {title}\nContent: {text or '(none)'}\n"
                f'Return: {{"title":"translated title", "summary":"brief summary max 80 chars in {name}"}}')

        raw = ollama_call(system, user)
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
                        # 立即寫回檔案（但只寫入前 5 篇）
                        all_data = json.loads(DATA_FILE.read_text())
                        # 找到對應的原始文章索引
                        orig_idx = i  # 因為我們只處理前 5 篇，索引相同
                        all_data[orig_idx][sk] = r["summary"]
                        if r.get("title"):
                            all_data[orig_idx][tk] = r["title"]
                        DATA_FILE.write_text(json.dumps(all_data, ensure_ascii=False, indent=2))
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

        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"✓ Done: {done} translated, {failed} failed")
    print(f"  Total time: {(time.time()-start)/60:.1f} min")
    print(f"  Data → {DATA_FILE}")


if __name__ == "__main__":
    main()