#!/usr/bin/env python3
"""
新聞翻譯生產腳本 - 使用 Gemini 2.5 Flash
繁體：台灣用語 | 簡體：中國大陸慣用語
"""
import json, re, time, urllib.request, sys, os, subprocess
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "news.json"
API_KEY = "AIzaSyCogCNvzMiutA8H9JX91xHsgeahi5XVujU"
MODEL = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# 語言設定
LANGUAGES = [
    {
        "code": "zh",
        "name": "繁體中文",
        "title_key": "title_zh",
        "summary_key": "s_zh",
        "system_prompt": "你是一位台灣的新聞編輯。請使用台灣的用語和表達方式，避免使用中國大陸的簡體字詞彙。"
    },
    {
        "code": "zcn",
        "name": "简体中文",
        "title_key": "title_zcn",
        "summary_key": "s_zcn",
        "system_prompt": "你是一位中國大陸的新聞編輯。請使用中國大陸的慣用語和簡體字詞彙，避免使用台灣用語。"
    },
    {
        "code": "ja",
        "name": "日本語",
        "title_key": "title_ja",
        "summary_key": "s_ja",
        "system_prompt": "你是一位日本的新聞編輯。請使用自然的日語表達。"
    },
    {
        "code": "ko",
        "name": "한국어",
        "title_key": "title_ko",
        "summary_key": "s_ko",
        "system_prompt": "你是一位韓國的新聞編輯。請使用自然的韓語表達。"
    }
]

def call_gemini(system_prompt: str, user_prompt: str, max_tokens: int = 300) -> str:
    """呼叫 Gemini 2.5 Flash API，帶指數退避重試"""
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,  # 低溫度確保一致性
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
    
    max_retries = 5
    base_delay = 2  # 起始延遲秒數
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(API_URL, data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
                if "candidates" in resp and len(resp["candidates"]) > 0:
                    candidate = resp["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            text = parts[0]["text"].strip()
                            if text:
                                return text
                # 如果沒有有效回應，也視為失敗，繼續重試
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 指數退避
                    print(f"      重試 {attempt+1}/{max_retries} 在 {delay} 秒後...")
                    time.sleep(delay)
                continue
                
        except urllib.error.HTTPError as e:
            status_code = e.code
            if status_code == 429:  # 速率限制
                retry_after = 30  # 預設30秒
                print(f"  ⚠️  速率限制 (429)，等待 {retry_after} 秒...")
                time.sleep(retry_after)
                continue
            elif status_code == 503:  # 服務不可用
                retry_after = 10
                print(f"  ⚠️  服務暫時不可用 (503)，等待 {retry_after} 秒...")
                time.sleep(retry_after)
                continue
            else:
                print(f"  ✗ HTTP 錯誤 {status_code}: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                continue
        except Exception as e:
            print(f"  ✗ API 錯誤 (嘗試 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
            continue
    
    print(f"  ✗ 所有重試失敗")
    return ""

def extract_translation(text: str, language_name: str):
    """從 API 回應中提取翻譯標題和摘要"""
    # 清理常見的前綴
    prefixes = [
        "好的，這是",
        "以下是",
        "這是",
        "Here is",
        "好的，以下是",
        f"以下是{language_name}翻譯"
    ]
    
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            if text.startswith("："):
                text = text[1:].strip()
            elif text.startswith(":"):
                text = text[1:].strip()
    
    # 嘗試提取標題（通常在第一行）
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    title = ""
    summary = ""
    
    if lines:
        # 第一行可能是標題
        first_line = lines[0]
        # 如果第一行包含"標題"或"Title"
        if "標題" in first_line or "Title" in first_line:
            # 提取冒號後的內容
            match = re.search(r'[：:]\s*(.+)', first_line)
            if match:
                title = match.group(1).strip()
        else:
            # 第一行可能就是標題
            title = first_line
        
        # 尋找摘要
        for i, line in enumerate(lines):
            if "摘要" in line or "Summary" in line or "summary" in line.lower():
                match = re.search(r'[：:]\s*(.+)', line)
                if match:
                    summary = match.group(1).strip()
                    break
        
        # 如果沒有找到摘要標記，取第二行或合併後續行
        if not summary and len(lines) > 1:
            # 從第二行開始，直到遇到空行或達到100字元
            summary_lines = []
            for line in lines[1:]:
                if line and len(''.join(summary_lines)) < 100:
                    summary_lines.append(line)
                else:
                    break
            summary = ' '.join(summary_lines)[:100].strip()
    
    # 如果還是沒找到摘要，用整個文字（排除可能標題）
    if not summary and text:
        # 移除可能標題的部分
        if title and text.startswith(title):
            remaining = text[len(title):].strip()
            summary = remaining[:100].strip()
        else:
            summary = text[:100].strip()
    
    return title, summary

def needs_translation(item, lang_config):
    """檢查是否需要翻譯"""
    title_en = item.get("title_en", "").strip()
    if not title_en:
        return False
    
    title_key = lang_config["title_key"]
    summary_key = lang_config["summary_key"]
    
    current_title = item.get(title_key, "").strip()
    current_summary = item.get(summary_key, "").strip()
    
    # 如果標題未翻譯或與英文相同，需要翻譯
    title_needed = not current_title or current_title == title_en
    
    # 如果摘要未翻譯、太短或與英文相同，需要翻譯
    summary_needed = (not current_summary or 
                     current_summary == title_en or 
                     len(current_summary) < 20)
    
    return title_needed or summary_needed

def translate_article(item, lang_config):
    """翻譯單篇文章的標題和摘要"""
    title_en = item.get("title_en", "").strip()
    content = item.get("desc", item.get("content", "")) or ""
    content_preview = content[:200]  # 取前200字
    
    language_name = lang_config["name"]
    system_prompt = lang_config["system_prompt"]
    
    user_prompt = f"""請將以下英文新聞翻譯成{language_name}：

標題：{title_en}
內容：{content_preview}

請提供：
1. {language_name}標題
2. {language_name}摘要（約80字）

請直接給出翻譯結果，不要有任何前綴或解釋。"""
    
    print(f"    翻譯到{language_name}...", end=" ", flush=True)
    start_time = time.time()
    
    response = call_gemini(system_prompt, user_prompt)
    elapsed = time.time() - start_time
    
    if not response:
        print(f"✗ 失敗 ({elapsed:.1f}s)")
        return None, None
    
    title, summary = extract_translation(response, language_name)
    
    if not title:
        # 如果沒提取到標題，用原始回應的前50字
        title = response[:50].strip()
    
    print(f"✓ 完成 ({elapsed:.1f}s)")
    return title, summary

def save_progress(data, progress_file):
    """保存進度"""
    progress = {
        "last_updated": datetime.now().isoformat(),
        "total_articles": len(data),
        "data": data
    }
    
    # 先保存到臨時文件
    temp_file = progress_file.with_suffix(".tmp")
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    
    # 然後移動到正式文件
    temp_file.rename(progress_file)

def deploy_to_netlify():
    """部署到 Netlify"""
    print(f"\n🚀 部署到 news.wongjai.com...")
    
    try:
        # Hugo 建置
        print("  建置 Hugo 網站...")
        result = subprocess.run(["hugo", "--gc", "--minify"], 
                               cwd=BASE, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ Hugo 建置失敗: {result.stderr[:200]}")
            return False
        
        # Netlify 部署
        print("  部署到 Netlify...")
        result = subprocess.run(
            ["netlify", "deploy", "--prod", "--site", "5e403a7a-f3c0-46bd-aaa1-643fad19f576", "--dir", "public"],
            cwd=BASE, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # 提取 URL
            import re
            url_match = re.search(r'https://[^\s]+\.netlify\.app', result.stdout)
            prod_match = re.search(r'Production URL:\s*<([^>]+)>', result.stdout)
            
            if prod_match:
                print(f"  ✅ 部署成功: {prod_match.group(1)}")
            elif url_match:
                print(f"  ✅ 部署成功: {url_match.group()}")
            else:
                print("  ✅ 部署成功（請檢查 Netlify 控制台）")
            return True
        else:
            print(f"  ✗ Netlify 部署失敗: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"  ✗ 部署錯誤: {e}")
        return False

def main():
    print("📰 新聞翻譯生產流程啟動")
    print("=" * 70)
    print("模型: Gemini 2.5 Flash")
    print("語言: 繁體中文（台灣用語）、简体中文（中國大陸慣用語）、日本語、한국어")
    print("目標: news.wongjai.com")
    print("=" * 70)
    
    # 載入數據
    print("載入新聞數據...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"總文章數: {len(data)}")
    
    # 分析翻譯需求
    print("\n分析翻譯需求...")
    tasks = []
    
    for i, item in enumerate(data):
        title_en = item.get("title_en", "").strip()
        if not title_en:
            continue
        
        for lang_config in LANGUAGES:
            if needs_translation(item, lang_config):
                tasks.append({
                    "article_index": i,
                    "language": lang_config,
                    "original_title": title_en
                })
    
    print(f"需要翻譯的項目: {len(tasks)}")
    
    if len(tasks) == 0:
        print("✅ 所有翻譯已完成，直接部署...")
        deploy_to_netlify()
        return
    
    # 批次處理設定
    BATCH_SIZE = 120  # 今晚先處理120個任務，0表示處理全部
    if BATCH_SIZE > 0:
        print(f"批次處理: 今晚先處理前 {min(BATCH_SIZE, len(tasks))} 個任務")
        tasks = tasks[:BATCH_SIZE]
    
    # 開始翻譯
    print(f"\n開始翻譯（預計時間: {len(tasks) * 4 / 60:.1f} 分鐘）...")
    print("=" * 70)
    
    completed = 0
    failed = 0
    start_time = time.time()
    
    for task_idx, task in enumerate(tasks):
        i = task["article_index"]
        lang_config = task["language"]
        original_title = task["original_title"]
        
        print(f"[{task_idx+1}/{len(tasks)}] 文章 {i}: {original_title[:50]}...")
        
        title, summary = translate_article(data[i], lang_config)
        
        if title or summary:
            # 更新數據
            if title:
                data[i][lang_config["title_key"]] = title
            if summary:
                data[i][lang_config["summary_key"]] = summary
            
            completed += 1
            
            # 每完成10個項目保存一次進度
            if completed % 10 == 0:
                print(f"  保存進度...")
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            failed += 1
        
        # 速率限制（每秒不超過2次請求）
        time.sleep(0.5)
    
    # 最終保存
    print(f"\n保存最終數據...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    total_time = time.time() - start_time
    print(f"\n✅ 翻譯完成!")
    print(f"   成功: {completed}, 失敗: {failed}")
    print(f"   總時間: {total_time/60:.1f} 分鐘")
    print(f"   平均速度: {total_time/len(tasks):.1f} 秒/項目")
    
    # 部署
    if deploy_to_netlify():
        print(f"\n🎉 所有流程完成！")
        print(f"   翻譯: {completed} 個項目")
        print(f"   部署: news.wongjai.com")
    else:
        print(f"\n⚠️ 翻譯完成但部署失敗")
        print(f"   請手動執行: cd {BASE} && netlify deploy --prod --site 5e403a7a-f3c0-46bd-aaa1-643fad19f576 --dir public")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n⏹️ 用戶中斷")
        print(f"  進度已自動保存，下次可繼續執行")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()