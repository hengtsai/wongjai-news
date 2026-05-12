#!/usr/bin/env python3
"""
測試 Google AI Studio Gemma 4 31B API
"""
import json, urllib.request

API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b:generateContent?key={API_KEY}"

def test_api():
    payload = json.dumps({
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Translate 'Hello world' to Traditional Chinese."}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 100
        }
    }).encode('utf-8')
    
    req = urllib.request.Request(API_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            print("✅ API 回應成功")
            print(json.dumps(resp, indent=2, ensure_ascii=False))
            
            # 提取文字
            if "candidates" in resp and len(resp["candidates"]) > 0:
                candidate = resp["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        text = parts[0]["text"]
                        print(f"\n📝 翻譯結果: {text}")
                        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"❌ HTTP 錯誤 {e.code}: {error_body}")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    return False

if __name__ == "__main__":
    print("🧪 測試 Google AI Studio API...")
    if test_api():
        print("\n✅ API 測試成功！Gemma 4 31B 可用於翻譯。")
    else:
        print("\n❌ API 測試失敗，請檢查 API key 或網路連線。")