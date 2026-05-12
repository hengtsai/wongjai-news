#!/usr/bin/env python3
"""
使用5篇純英文新聞測試兩種Google AI Studio模型
選定的文章索引: 0, 2, 5, 6, 29
"""
import json, re, time, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"

MODELS = {
    "gemini-2.5-flash": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={}",
    "gemma-4-31b": "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={}"
}

# 選定的文章索引
SELECTED_INDICES = [0, 2, 5, 6, 29]

def load_articles():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = []
    for idx in SELECTED_INDICES:
        if idx < len(data):
            item = data[idx]
            articles.append({
                "index": idx,
                "original_title": item.get("title_en", "").strip(),
                "original_content": (item.get("desc", item.get("content", "")) or "")[:300],
                "category": item.get("cat", "general"),
                "source": item.get("so", ""),
                "url": item.get("url", "")
            })
    return articles

def call_model(model_name: str, prompt: str, max_tokens: int = 512) -> dict:
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

    start_time = time.time()
    try:
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            elapsed = time.time() - start_time
            
            text = ""
            if "candidates" in resp and len(resp["candidates"]) > 0:
                candidate = resp["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        text = parts[0]["text"].strip()
            
            return {
                "success": bool(text),
                "time": elapsed,
                "response": text,
                "raw_response": resp
            }
    except Exception as e:
        return {
            "success": False,
            "time": time.time() - start_time,
            "response": f"Error: {e}",
            "raw_response": None
        }

def extract_translation(text):
    """從回應中提取翻譯結果"""
    # 嘗試找中文標題和摘要
    title_patterns = [
        r'標題[：:]\s*(.+?)(?:\n|$)',
        r'Title[：:]\s*(.+?)(?:\n|$)',
        r'^(.+?)(?:\n|$)',
        r'\"(.+?)\"'
    ]
    
    summary_patterns = [
        r'摘要[：:]\s*(.+?)(?:\n|$)',
        r'Summary[：:]\s*(.+?)(?:\n|$)',
        r'\n(.+?)(?:\n|$)'
    ]
    
    title = ""
    summary = ""
    
    for pattern in title_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            break
    
    for pattern in summary_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            summary = match.group(1).strip()
            break
    
    # 如果沒找到摘要，取部分文字
    if not summary and text:
        # 去掉可能的中文標題
        lines = text.split('\n')
        if len(lines) > 1:
            summary = lines[1].strip()[:100]
        else:
            summary = text[:100].strip()
    
    return title, summary

def test_article(article, model_name):
    prompt = f'''請將以下英文新聞翻譯成繁體中文：

標題：{article['original_title']}
內容：{article['original_content']}

請提供中文標題和中文摘要（約80字）。'''

    print(f"  使用 {model_name} 翻譯中...")
    result = call_model(model_name, prompt)
    
    title, summary = extract_translation(result["response"])
    
    return {
        "model": model_name,
        "success": result["success"],
        "time": result["time"],
        "response_length": len(result["response"]),
        "translated_title": title,
        "translated_summary": summary,
        "full_response": result["response"][:300]  # 只存前300字
    }

def main():
    print("🔍 5篇英文新聞翻譯模型比較測試")
    print("=" * 70)
    
    articles = load_articles()
    print(f"載入 {len(articles)} 篇文章")
    
    all_results = []
    
    for i, article in enumerate(articles):
        print(f"\n{'='*70}")
        print(f"📰 文章 {i+1}/{len(articles)} (索引: {article['index']})")
        print(f"類別: {article['category']}")
        print(f"標題: {article['original_title']}")
        print(f"內容: {article['original_content'][:150]}...")
        
        article_results = []
        
        # 測試 Gemini 2.5 Flash
        result1 = test_article(article, "gemini-2.5-flash")
        article_results.append(result1)
        print(f"  ✅ Gemini 2.5 Flash 完成 ({result1['time']:.1f}s)")
        
        time.sleep(1.5)  # 避免 rate limit
        
        # 測試 Gemma 4 31B
        result2 = test_article(article, "gemma-4-31b")
        article_results.append(result2)
        print(f"  ✅ Gemma 4 31B 完成 ({result2['time']:.1f}s)")
        
        time.sleep(1.5)
        
        all_results.append({
            "article": article,
            "translations": article_results
        })
    
    # 顯示結果
    print(f"\n{'='*70}")
    print("📊 翻譯效果比較")
    print("=" * 70)
    
    gemini_stats = {"total_time": 0, "success": 0, "avg_length": 0}
    gemma_stats = {"total_time": 0, "success": 0, "avg_length": 0}
    
    for i, result_set in enumerate(all_results):
        article = result_set["article"]
        translations = result_set["translations"]
        
        print(f"\n文章 {i+1}: {article['original_title'][:60]}...")
        
        for trans in translations:
            if trans["model"] == "gemini-2.5-flash":
                gemini_stats["total_time"] += trans["time"]
                gemini_stats["avg_length"] += trans["response_length"]
                if trans["success"]:
                    gemini_stats["success"] += 1
            else:
                gemma_stats["total_time"] += trans["time"]
                gemma_stats["avg_length"] += trans["response_length"]
                if trans["success"]:
                    gemma_stats["success"] += 1
            
            print(f"\n  {trans['model']}:")
            print(f"    時間: {trans['time']:.1f}s")
            print(f"    成功: {'✅' if trans['success'] else '❌'}")
            print(f"    標題: {trans['translated_title'][:60]}")
            print(f"    摘要: {trans['translated_summary'][:80]}...")
    
    # 統計
    print(f"\n{'='*70}")
    print("📈 統計數據")
    print("=" * 70)
    
    gemini_avg_time = gemini_stats["total_time"] / len(all_results) if len(all_results) > 0 else 0
    gemini_avg_length = gemini_stats["avg_length"] / len(all_results) if len(all_results) > 0 else 0
    gemma_avg_time = gemma_stats["total_time"] / len(all_results) if len(all_results) > 0 else 0
    gemma_avg_length = gemma_stats["avg_length"] / len(all_results) if len(all_results) > 0 else 0
    
    print(f"\nGemini 2.5 Flash:")
    print(f"  成功率: {gemini_stats['success']}/{len(all_results)}")
    print(f"  平均時間: {gemini_avg_time:.1f}s")
    print(f"  平均回應長度: {gemini_avg_length:.0f} 字元")
    
    print(f"\nGemma 4 31B:")
    print(f"  成功率: {gemma_stats['success']}/{len(all_results)}")
    print(f"  平均時間: {gemma_avg_time:.1f}s")
    print(f"  平均回應長度: {gemma_avg_length:.0f} 字元")
    
    # 建議
    print(f"\n{'='*70}")
    print("💡 建議")
    print("=" * 70)
    
    if gemini_stats["success"] > gemma_stats["success"]:
        print("✅ Gemini 2.5 Flash 更穩定，建議用於生產環境")
    elif gemma_stats["success"] > gemini_stats["success"]:
        print("✅ Gemma 4 31B 更穩定，建議用於生產環境")
    else:
        if gemini_avg_time < gemma_avg_time:
            print("⚡ Gemini 2.5 Flash 速度更快，建議用於批量翻譯")
        else:
            print("🧠 Gemma 4 31B 可能翻譯質量更好，建議用於重要內容")
    
    # 保存結果
    output_file = BASE / "scripts" / "five_articles_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 詳細結果已保存至: {output_file}")

if __name__ == "__main__":
    main()