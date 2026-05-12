#!/usr/bin/env python3
"""
快速比較 Gemini 2.5 Flash 和 Gemma 4 31B 的翻譯效果
只測試一篇新聞，快速得到結果
"""
import json, urllib.request, time

API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
MODELS = {
    "gemini-2.5-flash": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={}",
    "gemma-4-31b": "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={}"
}

# 一篇科技新聞
article = {
    "title": "NVIDIA Announces Blackwell AI Platform with 5x Performance Boost Over Hopper Architecture",
    "content": "NVIDIA has unveiled its next-generation Blackwell AI platform, claiming a 5x performance improvement over previous Hopper architecture for large language model training. The new platform features advanced tensor cores, improved memory bandwidth, and enhanced power efficiency. Blackwell is expected to accelerate AI research and deployment across various industries.",
    "category": "tech"
}

def quick_test(model_name, article):
    print(f"\n🔍 測試 {model_name}...")
    url = MODELS[model_name].format(API_KEY)
    
    # 簡化的提示詞
    prompt = f'''Translate to Traditional Chinese (繁體中文):

Title: {article['title']}
Content: {article['content']}

Please provide:
1. 中文標題
2. 中文摘要 (約60字)
'''
    
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 300,
            "topP": 0.95
        }
    }).encode('utf-8')
    
    try:
        start = time.time()
        req = urllib.request.Request(url, data=payload, 
                                    headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        elapsed = time.time() - start
        
        # 提取回應文字
        text = ""
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    text = parts[0]["text"].strip()
        
        return {
            "model": model_name,
            "time": elapsed,
            "response": text,
            "success": bool(text)
        }
    except Exception as e:
        return {
            "model": model_name,
            "time": 0,
            "response": f"Error: {e}",
            "success": False
        }

def main():
    print("🚀 快速翻譯模型比較")
    print("=" * 60)
    print(f"📰 測試文章: {article['title']}")
    print(f"📝 內容: {article['content'][:150]}...")
    
    results = []
    
    # 測試 Gemini 2.5 Flash
    result1 = quick_test("gemini-2.5-flash", article)
    results.append(result1)
    
    time.sleep(2)  # 避免 rate limit
    
    # 測試 Gemma 4 31B
    result2 = quick_test("gemma-4-31b", article)
    results.append(result2)
    
    # 顯示結果
    print(f"\n{'='*60}")
    print("📊 比較結果")
    print("=" * 60)
    
    for result in results:
        print(f"\n{result['model']}:")
        print(f"  時間: {result['time']:.1f}s")
        print(f"  成功: {'✅' if result['success'] else '❌'}")
        print(f"  回應:\n  {result['response'][:500]}{'...' if len(result['response']) > 500 else ''}")
    
    # 簡單分析
    print(f"\n{'='*60}")
    print("💡 初步觀察:")
    
    gemini_result = results[0]
    gemma_result = results[1]
    
    if gemini_result['success'] and gemma_result['success']:
        gemini_len = len(gemini_result['response'])
        gemma_len = len(gemma_result['response'])
        
        print(f"1. 回應時間: Gemini {gemini_result['time']:.1f}s vs Gemma {gemma_result['time']:.1f}s")
        print(f"2. 回應長度: Gemini {gemini_len} 字元 vs Gemma {gemma_len} 字元")
        print(f"3. 回應風格:")
        print(f"   - Gemini: {'較簡潔' if gemini_len < gemma_len else '較詳細'}")
        print(f"   - Gemma: {'較詳細' if gemma_len > gemini_len else '較簡潔'}")
        
        # 檢查是否有格式問題
        if "1." in gemini_result['response'] or "2." in gemini_result['response']:
            print(f"4. Gemini 格式: ✅ 可能遵循編號格式")
        if "解釋" in gemma_result['response'] or "分析" in gemma_result['response']:
            print(f"5. Gemma 格式: ⚠️ 可能包含解釋性文字")
    else:
        print("❌ 測試失敗，請檢查 API key 或網路連線")

if __name__ == "__main__":
    main()