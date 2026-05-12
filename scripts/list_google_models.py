#!/usr/bin/env python3
"""
列出 Google AI Studio 可用模型
"""
import json, urllib.request

API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
LIST_URL = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"

def list_models():
    req = urllib.request.Request(LIST_URL, 
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            print("✅ 可用模型列表：")
            if "models" in resp:
                for model in resp["models"]:
                    name = model.get("name", "")
                    display_name = model.get("displayName", "")
                    supported_methods = model.get("supportedGenerationMethods", [])
                    print(f"  - {name}")
                    print(f"    顯示名稱: {display_name}")
                    print(f"    支援方法: {', '.join(supported_methods)}")
                    print()
            else:
                print(json.dumps(resp, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    print("📋 查詢 Google AI Studio 可用模型...")
    list_models()