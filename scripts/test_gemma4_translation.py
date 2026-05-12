#!/usr/bin/env python3
"""
測試 Google AI Studio Gemma 4 31B API 翻譯功能
"""
import json, urllib.request, re

API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={API_KEY}"

def test_translation():
    system = "You are a professional news translator. Output ONLY valid JSON. No markdown."
    user = 'Translate to 繁體中文.\nTitle: How LiteLLM Turned Developer Machines Into Credential Vaults\nContent: A security report reveals how LiteLLM proxy servers can leak API keys from developer machines.\nReturn: {"title":"translated title", "summary":"brief summary max 80 chars in 繁體中文"}'
    
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
            "maxOutputTokens": 512,
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
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            print("✅ API 回應成功")
            # 提取文字
            if "candidates" in resp and len(resp["candidates"]) > 0:
                candidate = resp["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        text = parts[0]["text"].strip()
                        print(f"\n📝 原始回應:\n{text}")
                        
                        # 嘗試解析 JSON
                        m = re.search(r'\{[\s\S]*\}', text)
                        if m:
                            try:
                                json_result = json.loads(m.group())
                                print(f"\n✅ JSON 解析成功:")
                                print(f"   標題: {json_result.get('title', 'N/A')}")
                                print(f"   摘要: {json_result.get('summary', 'N/A')}")
                                return True
                            except json.JSONDecodeError:
                                print(f"\n❌ JSON 解析失敗")
                        else:
                            print(f"\n❌ 未找到 JSON 物件")
            print(f"\n📊 完整回應:\n{json.dumps(resp, indent=2, ensure_ascii=False)[:1000]}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"❌ HTTP 錯誤 {e.code}: {error_body}")
    except Exception as e:
        print(f"❌ 錯誤: {e}")
    return False

if __name__ == "__main__":
    print("🧪 測試 Google AI Studio Gemma 4 31B 翻譯...")
    if test_translation():
        print("\n✅ 翻譯測試成功！可以開始完整翻譯。")
    else:
        print("\n❌ 翻譯測試失敗，請檢查設定。")