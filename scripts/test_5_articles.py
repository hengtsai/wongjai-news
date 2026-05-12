#!/usr/bin/env python3
"""
測試 5 篇英文新聞用兩種 Google AI Studio 模型翻譯
1. Gemini 2.5 Flash
2. Gemma 4 31B
比較翻譯質量、速度、格式遵循度
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

def select_english_articles(data, count=5):
    """選出英文標題的文章"""
    articles = []
    for item in data:
        title_en = item.get("title_en", "").strip()
        # 簡單判斷是否為英文：包含英文字母且不包含中文字符
        if title_en and any(c.isalpha() for c in title_en) and not any('\u4e00' <= c <= '\u9fff' for c in title_en):
            content = item.get("desc", item.get("content", "")) or ""
            if len(content) > 50:  # 至少有些內容
                articles.append({
                    "original_title": title_en,
                    "original_content": content[:300],  # 取前300字
                    "category": item.get("cat", "general"),
                    "source": item.get("so", ""),
                    "url": item.get("url", "")
                })
                if len(articles) >= count:
                    break
    return articles

def call_model(model_name: str, prompt: str, max_tokens: int = 512) -> dict:
    """呼叫 Google AI Studio API"""
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
            
            # 提取文字
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
    """從回應中提取翻譯標題和摘要"""
    # 嘗試找中文標題（假設在回應開頭或明顯標示）
    title_patterns = [
        r'標題[：:]\s*(.+)',
        r'Title[：:]\s*(.+)',
        r'中文標題[：:]\s*(.+)',
        r'^([^。！？!?\n]{5,30})$'  # 單獨一行作為標題
    ]
    
    summary_patterns = [
        r'摘要[：:]\s*(.+)',
        r'Summary[：:]\s*(.+)',
        r'中文摘要[：:]\s*(.+)',
        r'([^。！？]{20,100}。)'
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
    
    # 如果沒找到，取前100字作為摘要
    if not summary and text:
        summary = text[:100].strip()
    
    return title, summary

def test_article_translation(article, model_name):
    """測試單篇文章翻譯"""
    prompt = f'''請將以下英文新聞翻譯成繁體中文（臺灣用語）：

標題：{article['original_title']}
內容：{article['original_content']}

請提供：
1. 中文標題
2. 中文摘要（約80字）

請直接給出翻譯結果，不需要解釋或額外說明。'''

    print(f"  使用 {model_name} 翻譯...")
    result = call_model(model_name, prompt)
    
    title, summary = extract_translation(result["response"])
    
    return {
        "model": model_name,
        "success": result["success"],
        "time": result["time"],
        "response_length": len(result["response"]),
        "translated_title": title,
        "translated_summary": summary,
        "raw_response": result["response"][:500]  # 只存前500字
    }

def main():
    print("🔍 5篇英文新聞翻譯模型比較測試")
    print("=" * 70)
    
    # 讀取數據
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 選出5篇英文文章
    articles = select_english_articles(data, 5)
    print(f"選出 {len(articles)} 篇英文新聞文章")
    
    if len(articles) == 0:
        print("❌ 沒有找到足夠的英文文章")
        return
    
    all_results = []
    
    for i, article in enumerate(articles):
        print(f"\n{'='*70}")
        print(f"📰 文章 {i+1}/{len(articles)}")
        print(f"類別: {article['category']}")
        print(f"標題: {article['original_title']}")
        print(f"內容: {article['original_content'][:150]}...")
        
        article_results = []
        
        # 測試 Gemini 2.5 Flash
        result1 = test_article_translation(article, "gemini-2.5-flash")
        article_results.append(result1)
        
        print(f"  ✅ 完成 ({result1['time']:.1f}s)")
        
        # 等待避免 rate limit
        time.sleep(2)
        
        # 測試 Gemma 4 31B
        result2 = test_article_translation(article, "gemma-4-31b")
        article_results.append(result2)
        
        print(f"  ✅ 完成 ({result2['time']:.1f}s)")
        
        # 等待下一篇文章
        time.sleep(2)
        
        all_results.append({
            "article": article,
            "translations": article_results
        })
    
    # 顯示比較結果
    print(f"\n{'='*70}")
    print("📊 翻譯效果比較報告")
    print("=" * 70)
    
    comparison_stats = {
        "gemini-2.5-flash": {"total_time": 0, "success_count": 0, "avg_response_length": 0},
        "gemma-4-31b": {"total_time": 0, "success_count": 0, "avg_response_length": 0}
    }
    
    for i, result_set in enumerate(all_results):
        article = result_set["article"]
        translations = result_set["translations"]
        
        print(f"\n文章 {i+1}: {article['original_title'][:60]}...")
        print(f"類別: {article['category']}")
        
        for trans in translations:
            model = trans["model"]
            comparison_stats[model]["total_time"] += trans["time"]
            comparison_stats[model]["avg_response_length"] += trans["response_length"]
            if trans["success"]:
                comparison_stats[model]["success_count"] += 1
            
            print(f"\n  {model}:")
            print(f"    時間: {trans['time']:.1f}s")
            print(f"    成功: {'✅' if trans['success'] else '❌'}")
            print(f"    回應長度: {trans['response_length']} 字元")
            print(f"    中文標題: {trans['translated_title'][:60]}")
            print(f"    中文摘要: {trans['translated_summary'][:80]}...")
        
        print(f"\n  {'─'*40}")
    
    # 統計總結
    print(f"\n{'='*70}")
    print("📈 統計總結")
    print("=" * 70)
    
    for model in ["gemini-2.5-flash", "gemma-4-31b"]:
        stats = comparison_stats[model]
        if stats["success_count"] > 0:
            avg_time = stats["total_time"] / stats["success_count"]
            avg_length = stats["avg_response_length"] / stats["success_count"]
        else:
            avg_time = 0
            avg_length = 0
        
        print(f"\n{model}:")
        print(f"  成功次數: {stats['success_count']}/{len(all_results)}")
        print(f"  平均時間: {avg_time:.1f}s")
        print(f"  平均回應長度: {avg_length:.0f} 字元")
    
    # 保存詳細結果
    output_file = BASE / "scripts" / "model_comparison_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 詳細結果已保存至: {output_file}")
    
    # 給出建議
    print(f"\n💡 建議:")
    gemini_stats = comparison_stats["gemini-2.5-flash"]
    gemma_stats = comparison_stats["gemma-4-31b"]
    
    if gemini_stats["success_count"] > gemma_stats["success_count"]:
        print("  Gemini 2.5 Flash 更穩定可靠，建議用於生產環境")
    elif gemma_stats["success_count"] > gemini_stats["success_count"]:
        print("  Gemma 4 31B 更穩定可靠，建議用於生產環境")
    else:
        gemini_avg_time = gemini_stats["total_time"] / gemini_stats["success_count"] if gemini_stats["success_count"] > 0 else 999
        gemma_avg_time = gemma_stats["total_time"] / gemma_stats["success_count"] if gemma_stats["success_count"] > 0 else 999
        
        if gemini_avg_time < gemma_avg_time:
            print("  Gemini 2.5 Flash 速度更快，建議用於批量翻譯")
        else:
            print("  Gemma 4 31B 翻譯質量可能更好，建議用於重要內容")

if __name__ == "__main__":
    main()