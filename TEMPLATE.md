# Wongjai News Template — v5 (2026-04-07)

> Clean Financial Digest style. Used for `news.wongjai.com` and future similar sites.

## Design Tokens

```css
--bg: #0d0f12           /* 深色背景 */
--border: rgba(255,255,255,0.06)
--text: #eaedf3
--text-dim: #8f95a3
--text-faint: #5c6170
--accent: #f5a623        /* 金色強調 */
--max-width: 960px       /* 閱讀寬度 */
```

## Typography Scale

| Element | Size | Weight |
|---------|------|--------|
| Brand (WongjaiNews) | 22px | 700 |
| Article Title | 19px | 600 |
| Article Brief | 14.5px | normal |
| Source / Time | 11px | 600 / 400 |

## Features

- 🌗 Dark/Light theme toggle (auto-detect prefers-color-scheme)
- 🌐 5 languages: 繁中 / 簡中 / EN / 日本語 / 한국어
- 📧 Email contact button → mailto:news@wongjai.com
- 📂 4 category tabs: 全部 / 科技 / 晶片．半導體 / 財經．投資
- Mobile: max 560px breakpoint, title→16px, brief→13.5px

## File Locations

```
wongjai-news/
├── themes/wongjai-news/
│   ├── static/css/style.css     # ← 主樣式
│   ├── static/js/theme.js       # ← 主題切換
│   └── layouts/
│       ├── _default/baseof.html # ← header / tabs / lang buttons
│       └── index.html           # ← SPA feed (JS renders from news.json)
├── static/data/news.json        # ← 新聞資料
└── hugo.toml                    # ← baseURL = https://news.wongjai.com/
```

## Data Format (news.json)

```json
[{
  "cat": "tech",
  "title_en": "English title",
  "title_zh": "中文標題",
  "s_en": "English brief",
  "s_zh": "中文摘要",
  "so": "source.com",
  "url": "https://...",
  "time": "2026-04-07T12:00:00+08:00"
}]
```

## Deploy

```bash
cd /Users/wongjai/.openclaw/workspace/wongjai-news
hugo --minify
netlify deploy --prod --dir=public --site 5e403a7a-f3c0-46bd-aaa1-643fad19f576
```
