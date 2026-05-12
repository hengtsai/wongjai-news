#!/usr/bin/env python3
"""
快速翻譯前2篇文章並部署
"""
import json, re, time, urllib.request, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
OLLAMA = "http://localhost:11434/api/chat"

def translate_one(title, content, lang_name):
    system = "You are a professional news translator. Output ONLY valid JSON. No markdown."
    user = f"Translate to {lang_name}.\nTitle: {title}\nContent: {content or '(none)'}\nReturn: {{\"title\":\"translated title\", \"summary\":\"brief summary max 80 chars in {lang_name}\"}}"
    
    payload = json.dumps({
        "model": "gemma4:26b",
        "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "options": {"temperature": 0.3, "num_predict": 512}
    }).encode()
    
    try:
        req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        raw = result.get("message", {}).get("content", "")
        m = re.search(r'\{[\s\S]*\}', raw)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"翻譯失敗: {e}")
    return None

def main():
    print("📝 翻譯前 2 篇文章...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    languages = [("繁体中文", "zh"), ("简体中文", "zcn"), ("日本語", "ja"), ("한국어", "ko")]
    
    for idx in range(2):
        item = data[idx]
        title_en = item.get("title_en", "").strip()
        print(f"\n文章 {idx}: {title_en}")
        
        for lang_name, lang_code in languages:
            title_key = f"title_{lang_code}"
            summary_key = f"s_{lang_code}"
            
            if item.get(summary_key, "").strip() and item.get(summary_key, "").strip() != title_en:
                print(f"  {lang_name}: 已翻譯")
                continue
                
            print(f"  {lang_name}: 翻譯中...")
            content = (item.get("desc", item.get("content", "")) or "")[:300]
            result = translate_one(title_en, content, lang_name)
            if result:
                if result.get("title"):
                    item[title_key] = result["title"]
                if result.get("summary"):
                    item[summary_key] = result["summary"]
                print(f"    ✓ {result.get('title', '')[:60]}...")
            time.sleep(1)
        
        data[idx] = item
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 翻譯完成，寫入 {DATA_FILE}")
    
    # 部署
    print("🚀 部署到 Netlify...")
    try:
        subprocess.run(["hugo", "--gc", "--minify"], cwd=BASE, capture_output=True)
        deploy = subprocess.run(["netlify", "deploy", "--prod", "--site", "wongjai-news"], 
                               cwd=BASE, capture_output=True, text=True)
        print("部署結果:", deploy.stdout[:500])
        if "https://" in deploy.stdout:
            import re
            url_match = re.search(r'https://[^\s]+\.netlify\.app', deploy.stdout)
            if url_match:
                print(f"\n🌐 可查看: {url_match.group()}")
    except Exception as e:
        print(f"部署失敗: {e}")

if __name__ == "__main__":
    main()