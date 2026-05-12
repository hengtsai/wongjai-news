#!/usr/bin/env python3
"""
純 MiniMax M2.7 翻譯 (Ollama gemma4:26b 太慢/空回覆)
"""
import json, re, time, urllib.request, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data/news.json"

MM_URL = "https://api.minimax.io/anthropic/v1/messages"
MM_KEY = "sk-cp-fuw21CPJopzLNDf1lk60zVat348gwsAaTEPxrjAg19h2ldOsJAABwqI_6Jixyi5HO46gY2_uwG_RLwpsFSzV5Zk38a3e4aFeFdz1MEu1n-ZIiSFFfAmS0i4"

LANGS = [
    {"name":"繁體中文","tk":"title_zh","sk":"s_zh","sys":"你是一位台灣的新聞編輯。請用台灣用語。只輸出翻譯結果。"},
    {"name":"简体中文","tk":"title_zcn","sk":"s_zcn","sys":"你是一位中国大陆的新闻编辑。请用大陆用语。只输出翻译结果，使用简体字。"},
    {"name":"日本語","tk":"title_ja","sk":"s_ja","sys":"You are a Japanese news editor. Output ONLY the translation."},
    {"name":"한국어","tk":"title_ko","sk":"s_ko","sys":"You are a Korean news editor. Output ONLY the translation."},
]

def mm(prompt, retries=2):
    """Call MiniMax API with retry"""
    data = json.dumps({
        "model":"MiniMax-M2.7","max_tokens":512,"temperature":0.2,
        "messages":[{"role":"user","content":prompt}]
    }).encode('utf-8')
    for attempt in range(retries+1):
        try:
            rq = urllib.request.Request(MM_URL, data=data,
                headers={"Content-Type":"application/json","x-api-key":MM_KEY,"anthropic-version":"2023-06-01"},
                method="POST")
            with urllib.request.urlopen(rq, timeout=45) as rsp:
                resp = json.loads(rsp.read())
                for c in resp.get("content",[]):
                    if c.get("type")=="text" and c.get("text"):
                        return c["text"].strip()
        except Exception as e:
            if attempt < retries:
                time.sleep(3*(2**attempt))
            else:
                return ""
    return ""

def extract(text):
    if not text: return None, None
    title = summary = ""
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith("標題") or line.startswith("Title") or line.startswith("title"):
            title = re.sub(r'^(標題|Title|title)[：:]\s*', '', line).strip()[:80]
        elif line.startswith("摘要") or line.startswith("Summary") or line.startswith("summary"):
            summary = re.sub(r'^(摘要|Summary|summary)[：:]\s*', '', line).strip()[:100]
    if not title:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines: title = lines[0][:80].strip()
    if not summary:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) > 1: summary = ' '.join(lines[1:])[:100].strip()
    return (title or None), (summary or None)

def needs(item, lang):
    te = item.get("title_en","").strip()
    if not te: return False
    ct = item.get(lang["tk"],"").strip()
    cs = item.get(lang["sk"],"").strip()
    return not (ct and ct != te and cs and cs != te and len(cs)>=20)

def main():
    print("="*60)
    print("🌍 全量翻譯 - MiniMax M2.7")
    print("="*60)
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tasks = []
    for i, item in enumerate(data):
        for lang in LANGS:
            if needs(item, lang):
                tasks.append({"i":i, "lang":lang, "t":item.get("title_en","")[:50]})
    
    total = len(tasks)
    print(f"📊 需翻譯: {total} 項\n")
    if not total:
        print("✅ 已完成! 部署...")
        deploy(); return
    
    done=fail=0
    t0=time.time()
    
    for idx, t in enumerate(tasks):
        item = data[t["i"]]
        te = item.get("title_en","").strip()
        content = (item.get("desc", item.get("content","")) or "")[:200]
        prompt = f"""{t['lang']['sys']}

{t['lang']['name']} 標題:
{t['lang']['name']} 摘要 (100字內):

"""
        print(f"[{idx+1}/{total}] #{t['i']}→{t['lang']['name']}: {t['t']}", end=" ", flush=True)
        
        t1 = time.time()
        resp = mm(prompt)
        elapsed = time.time()-t1
        title, summary = extract(resp)
        
        if title or summary:
            if title: item[t["lang"]["tk"]] = title
            if summary: item[t["lang"]["sk"]] = summary
            done+=1; print(f"✓ {elapsed:.1f}s")
        else:
            fail+=1; print(f"✗ {elapsed:.1f}s")
        
        if done%10==0:
            save(data)
            print(f"  💾 saved ({(time.time()-t0)/60:.1f}min)")
    
    save(data)
    dt = time.time()-t0
    print(f"\n✅ ✔{done} ✘{fail} {dt/60:.1f}min")
    deploy()

def save(data):
    with open(DATA_FILE,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def deploy():
    print("\n🚀 部署...")
    r = subprocess.run(["hugo","--gc","--minify"],cwd=BASE,capture_output=True,text=True)
    if r.returncode!=0:
        print(f"  ⚠️ Hugo: {r.stderr[:200]}"); return
    print("  ✅ Hugo OK")
    r = subprocess.run(["netlify","deploy","--prod","--site","5e403a7a-f3c0-46bd-aaa1-643fad19f576","--dir","public"],
        cwd=BASE,capture_output=True,text=True)
    if r.returncode==0:
        import re
        m = re.search(r'https://[\w-]+\.netlify\.app', r.stdout)
        print(f"  ✅ 部署成功{' → '+m.group() if m else ''}")
    else:
        print(f"  ⚠️ Netlify: {r.stderr[:200]}")

if __name__=="__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 中斷，已保存")
