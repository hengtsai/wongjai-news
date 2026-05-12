#!/usr/bin/env python3
"""
測試 Google AI Studio Gemma 4 31B 單一翻譯
"""
import json, re, time, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={API_KEY}"

def google_ai_call(system: str, user: str, max_tokens: int = 512) -> str:
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
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }).encode('utf-8')

    req = urllib.request.Request(API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            if "candidates" in resp and len(resp["candidates"]) > 0:
                candidate = resp["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"].strip()
            return json.dumps(resp)[:500]
    except Exception as e:
        print(f"  ✗ {e}")
        return ""

def main():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 只處理第一篇文章的韓文
    item = data[0]
    title = item.get("title_en", "").strip()
    text = (item.get("desc", item.get("content", "")) or "")[:500]
    name = "한국어"
    
    print(f"文章 0: {title}")
    print(f"內容預覽: {text[:100]}...")
    
    system = "You are a professional news translator. You must output ONLY a valid JSON object with no additional text, no explanations, no markdown. Do not include any other text outside the JSON object."
    user = (f"Translate to {name}.\nTitle: {title}\nContent: {text or '(none)'}\n"
            f'Return: {{"title":"translated title", "summary":"brief summary max 80 chars in {name}"}}\n'
            f'Output ONLY the JSON object, nothing else.')
    
    print("\n發送請求到 Google AI Studio...")
    start = time.time()
    raw = google_ai_call(system, user)
    elapsed = time.time() - start
    
    print(f"回應時間: {elapsed:.1f}s")
    print(f"原始回應:\n{raw[:500]}...")
    
    if raw:
        m = re.search(r'\{[\s\S]*\}', raw, re.DOTALL)
        if m:
            try:
                r = json.loads(m.group())
                print(f"\n✅ JSON 解析成功:")
                print(f"   標題: {r.get('title', 'N/A')}")
                print(f"   摘要: {r.get('summary', 'N/A')}")
                
                # 更新數據
                item["title_ko"] = r.get("title", "")
                item["s_ko"] = r.get("summary", "")
                
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"\n✅ 已更新 news.json")
                
            except json.JSONDecodeError:
                print(f"\n❌ JSON 解析失敗")
        else:
            print(f"\n❌ 未找到 JSON 物件")
    else:
        print(f"\n❌ 無回應")

if __name__ == "__main__":
    main()