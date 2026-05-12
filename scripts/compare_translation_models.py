#!/usr/bin/env python3
"""
比較 Google AI Studio 兩種模型的翻譯效果
1. Gemini 2.5 Flash
2. Gemma 4 31B
"""
import json, re, time, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"

MODELS = {
    "gemini-2.5-flash": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={}",
    "gemma-4-31b": "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={}"
}

# 三篇英文新聞（科技/財經/安全）
TEST_ARTICLES = [
    {
        "title": "How LiteLLM Turned Developer Machines Into Credential Vaults for Attackers",
        "content": "A security report reveals how LiteLLM proxy servers, used by developers to manage multiple AI models, can inadvertently expose API keys and credentials stored on developer machines. The vulnerability allows attackers to access sensitive credentials through misconfigured proxy servers.",
        "category": "security"
    },
    {
        "title": "NVIDIA Announces Blackwell AI Platform with 5x Performance Boost",
        "content": "NVIDIA has unveiled its next-generation Blackwell AI platform, claiming a 5x performance improvement over previous Hopper architecture. The new platform features advanced tensor cores and improved memory bandwidth, targeting large language model training and inference workloads.",
        "category": "tech"
    },
    {
        "title": "Fed Signals Caution on Rate Cuts as Inflation Remains Sticky",
        "content": "Federal Reserve officials have indicated they will proceed cautiously with interest rate cuts, as inflation data remains higher than expected. The central bank's latest minutes show policymakers are concerned about persistent price pressures in the services sector.",
        "category": "finance"
    }
]

def call_model(model_name: str, prompt: str, max_tokens: int = 512) -> str:
    url = MODELS[model_name].format(API_KEY)
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
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

    req = urllib.request.Request(url, data=payload,
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
            return json.dumps(resp)[:1000]
    except Exception as e:
        return f"Error: {e}"

def test_translation(article, model_name):
    title = article["title"]
    content = article["content"]
    
    prompt = f'''Translate this news article to Traditional Chinese (繁體中文).

Title: {title}
Content: {content}

Output format:
- Translated title: [中文標題]
- Translated summary: [中文摘要，約80字]
- Translation quality notes: [簡短說明翻譯難點或特色]

Keep the translation accurate and natural.'''
    
    print(f"\n📡 使用 {model_name} 翻譯...")
    start = time.time()
    response = call_model(model_name, prompt)
    elapsed = time.time() - start
    
    print(f"⏱️ 回應時間: {elapsed:.1f}s")
    print(f"📝 回應長度: {len(response)} 字元")
    print(f"📋 回應內容:\n{response[:800]}{'...' if len(response) > 800 else ''}")
    
    # 嘗試提取中文標題
    title_match = re.search(r'Translated title:\s*(.+)', response, re.IGNORECASE)
    if not title_match:
        title_match = re.search(r'標題:\s*(.+)', response)
    if not title_match:
        title_match = re.search(r'中文標題:\s*(.+)', response)
    
    chinese_title = title_match.group(1).strip() if title_match else "無法提取標題"
    
    return {
        "model": model_name,
        "response_time": elapsed,
        "response_length": len(response),
        "chinese_title": chinese_title[:100],
        "full_response": response
    }

def main():
    print("🔍 比較 Google AI Studio 兩種模型的翻譯效果")
    print("=" * 60)
    
    results = []
    
    for i, article in enumerate(TEST_ARTICLES):
        print(f"\n{'='*60}")
        print(f"📰 文章 {i+1}: {article['category'].upper()}")
        print(f"標題: {article['title']}")
        print(f"內容: {article['content'][:150]}...")
        
        article_results = []
        
        # 測試 Gemini 2.5 Flash
        result1 = test_translation(article, "gemini-2.5-flash")
        article_results.append(result1)
        time.sleep(2)  # 避免 rate limit
        
        # 測試 Gemma 4 31B
        result2 = test_translation(article, "gemma-4-31b")
        article_results.append(result2)
        time.sleep(2)
        
        results.append({
            "article": article,
            "translations": article_results
        })
    
    # 生成比較報告
    print(f"\n{'='*60}")
    print("📊 翻譯效果比較報告")
    print("=" * 60)
    
    for i, article_data in enumerate(results):
        article = article_data["article"]
        translations = article_data["translations"]
        
        print(f"\n文章 {i+1}: {article['title'][:60]}...")
        print(f"類別: {article['category']}")
        
        for trans in translations:
            print(f"\n  {trans['model']}:")
            print(f"    回應時間: {trans['response_time']:.1f}s")
            print(f"    回應長度: {trans['response_length']} 字元")
            print(f"    中文標題: {trans['chinese_title']}")
        
        print(f"\n  {'─'*40}")
    
    # 保存結果到文件
    output_file = BASE / "scripts" / "translation_comparison.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 比較結果已保存至: {output_file}")

if __name__ == "__main__":
    main()