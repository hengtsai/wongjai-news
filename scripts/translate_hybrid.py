#!/usr/bin/env python3
"""
混合翻譯腳本: gemma4:26b (本地) + MiniMax M2.7 (逾時切換)
規則: 單次翻譯逾時 180秒 → 自動切換 MiniMax
"""
import json, re, time, urllib.request, subprocess, os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data/news.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:26b"

MM_API_KEY = "sk-cp-fuw21CPJopzLNDf1lk60zVat348gwsAaTEPxrjAg19h2ldOsJAABwqI_6Jixyi5HO46gY2_uwG_RLwpsFSzV5Zk38a3e4aFeFdz1MEu1n-ZIiSFFfAmS0i4"
MM_URL = "https://api.minimax.io/anthropic/v1/messages"

TIMEOUT = 120  # 每項翻譯秒數上限

LANGS = [
    {"code":"zh","name":"繁體中文","tk":"title_zh","sk":"s_zh",
     "sys":"你是一位台灣的新聞編輯。請只輸出翻譯結果，不要任何分析。"},
    {"code":"zcn","name":"简体中文","tk":"title_zcn","sk":"s_zcn",
     "sys":"你是一位中國大陸的新聞編輯。請只輸出翻譯結果，使用大陸用語。"},
    {"code":"ja","name":"日本語","tk":"title_ja","sk":"s_ja",
     "sys":"You are a Japanese news editor. Output only the translation."},
    {"code":"ko","name":"한국어","tk":"title_ko","sk":"s_ko",
     "sys":"You are a Korean news editor. Output only the translation."},
]

def ollama(prompt, seconds=TIMEOUT):
    """Call Ollama local API"""
    data = json.dumps({
        "model": OLLAMA_MODEL, "prompt": prompt,
        "stream": False, "options": {"temperature": 0.2, "top_p": 0.95, "num_predict": 512}
    }).encode('utf-8')
    t0 = time.time()
    try:
        r = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(r, timeout=seconds) as rsp:
            resp = json.loads(rsp.read())
            return resp.get("response", "").strip(), time.time()-t0
    except Exception as e:
        return "", time.time()-t0

def minimax(prompt):
    """Call MiniMax API"""
    data = json.dumps({
        "model": "MiniMax-M2.7", "max_tokens": 512, "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }).encode('utf-8')
    try:
        r = urllib.request.Request(MM_URL, data=data,
            headers={"Content-Type":"application/json","x-api-key":MM_API_KEY,"anthropic-version":"2023-06-01"},
            method="POST")
        with urllib.request.urlopen(r, timeout=60) as rsp:
            resp = json.loads(rsp.read())
            for c in resp.get("content", []):
                if c.get("type") == "text" and c.get("text"):
                    return c["text"].strip(), 0
    except Exception as e:
        print(f"  MM err: {e}")
    return "", 0

def translate(task_text, use_mm=False):
    """Return (response, time, new_use_mm)"""
    t0 = time.time()
    if use_mm:
        resp, _ = minimax(task_text)
        return resp, time.time()-t0, True
    resp, elapsed = ollama(task_text)
    if (not resp and elapsed >= TIMEOUT) or elapsed >= 180:
        print(f"\n  ⚠️ Ollama逾時({elapsed:.0f}s)切MiniMax...", end="")
        resp, _ = minimax(task_text)
        if resp:
            return resp, time.time()-t0, True
    return resp, time.time()-t0, use_mm

def extract(text):
    """Extract title & summary from response"""
    if not text: return None, None
    title = summary = ""
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith("標題:") or line.startswith("標題 ："):
            title = re.sub(r'^標題[：:]\\s*', '', line).strip()[:80]
        elif line.startswith("摘要:") or line.startswith("摘要 ："):
            summary = re.sub(r'^摘要[：:]\\s*', '', line).strip()[:100]
    if not title:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines: title = lines[0][:80].strip()
    if not summary:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) > 1: summary = ' '.join(lines[1:])[:100].strip()
    return (title if title else None), (summary if summary else None)

def needs(item, lang):
    te = item.get("title_en","").strip()
    if not te: return False
    ct = item.get(lang["tk"],"").strip()
    cs = item.get(lang["sk"],"").strip()
    t_ok = ct and ct != te
    s_ok = cs and cs != te and len(cs) >= 20
    return not (t_ok and s_ok)

def main():
    global use_mm
    print("="*70)
    print("🌍 混合翻譯: gemma4:26b → MiniMax M2.7 (逾時切)")
    print(f"規則: 單次逾時 {TIMEOUT}秒 切換為 MiniMax")
    print("="*70)
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tasks = []
    for i, item in enumerate(data):
        for lang in LANGS:
            if needs(item, lang):
                tasks.append({"i":i, "lang":lang, "t":item.get("title_en","")[:50]})
    
    total = len(tasks)
    print(f"\n📊 需翻譯: {total} 項")
    if not total:
        print("✅ 全部完成！部署...")
        deploy(); return
    
    use_mm = False  # global flag
    done = fail = 0
    t0 = time.time()
    
    for idx, t in enumerate(tasks):
        te = data[t["i"]].get("title_en","").strip()
        content = (data[t["i"]].get("desc", data[t["i"]].get("content","")) or "")[:200]
        prompt = f"""{t['lang']['sys']}

Translate to {t['lang']['name']}:
TITLE: {te}
CONTENT: {content}

Output format:
標題: [translated title]
摘要: [summary under 80 chars]"""
        
        print(f"[{idx+1}/{total}] #{t['i']}→{t['lang']['name']}: {t['t']}", end=" ", flush=True)
        resp, elapsed, use_mm = translate(prompt, use_mm)
        title, summary = extract(resp)
        
        if title or summary:
            if title: data[t["i"]][t["lang"]["tk"]] = title
            if summary: data[t["i"]][t["lang"]["sk"]] = summary
            done += 1; print(f"✓ {elapsed:.1f}s")
        else:
            fail += 1; print(f"✗ {elapsed:.1f}s")
        
        if done % 10 == 0:
            save(data)
            print(f"  💾 saved ({(time.time()-t0)/60:.1f}min)")
    
    save(data)
    dt = time.time()-t0
    mode = "MiniMax" if use_mm else "gemma4:26b"
    print(f"\n✅ 完成! ✔{done} ✘{fail} {dt/60:.1f}min ({dt/3600:.2f}h) 模式:{mode}")
    deploy()

def save(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def deploy():
    print("\n🚀 部署...")
    try:
        r = subprocess.run(["hugo","--gc","--minify"], cwd=BASE,
            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ⚠️ Hugo fail: {r.stderr[:200]}"); return
        print("  ✅ Hugo 建置完成")
        r = subprocess.run(
            ["netlify","deploy","--prod","--site","5e403a7a-f3c0-46bd-aaa1-643fad19f576","--dir","public"],
            cwd=BASE, capture_output=True, text=True)
        if r.returncode == 0:
            import re
            m = re.search(r'https://[\w-]+\.netlify\.app', r.stdout)
            print(f"  ✅ 部署成功{' → '+m.group() if m else ''}")
        else:
            print(f"  ⚠️ Netlify fail: {r.stderr[:200]}")
    except Exception as e:
        print(f"  ⚠️ {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 中斷，已保存進度")
