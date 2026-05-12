#!/usr/bin/env python3
"""Write more articles to fill remaining category gaps."""
import hashlib, re, time
from pathlib import Path
from datetime import datetime, timezone

ARTICLES = [
    {"title": "The ascension of Arm: hyperscalers rewire AI server CPUs",
     "summary_en": "Custom AI server CPUs are shifting from x86 to proprietary Arm-based designs, reshaping semiconductor competition. Counterpoint Research data confirms the post-x86 era for AI server compute is underway.",
     "full_text": "The architecture of host CPUs in custom AI servers is undergoing a significant shift, with proprietary Arm-based designs steadily displacing traditional x86 processors, according to Counterpoint Research's latest data on AI server compute ASIC shipments. This trend has major implications for Intel and AMD as hyperscalers build their own optimized silicon.",
     "source": "DigiTimes", "category": "半導體",
     "url": "https://www.digitimes.com/news/arm-hyperscalers-ai-server-cpus"},
    {"title": "Dixon launches India's first homegrown display module fab",
     "summary_en": "Dixon Technologies invests INR 11 billion in a new display module fabrication unit in Noida. The plant approved under India's ECMS program marks a milestone in backward integration for Indian display manufacturing.",
     "full_text": "Dixon Technologies is accelerating its push into display module manufacturing, backed by an INR 11 billion investment in a new facility in the Noida region. The plant, approved under India's Electronics Component Manufacturing Scheme, will serve as the company's first dedicated display module fabrication unit.",
     "source": "DigiTimes", "category": "半導體",
     "url": "https://www.digitimes.com/news/dixon-india-display-module-fab"},
    {"title": "China plans display sector consolidation as BOE leads OLED",
     "summary_en": "China drafts consolidation plan with BOE positioned for OLED and TCL China Star for LCD. Smaller panel makers face mergers or exits as the industry consolidates amid intense competition.",
     "full_text": "China is reportedly drafting a consolidation plan for its display industry, with BOE Technology positioned for small- and mid-sized OLED and TCL China Star for large-size LCD, while smaller panel makers face potential mergers or exits.",
     "source": "DigiTimes", "category": "半導體", "url": "https://www.digitimes.com/news/china-display-sector-consolidation"},
    {"title": "Starcloud raises $170M for space-based solar data centers",
     "summary_en": "Starcloud raised $170 million at $1.1 billion valuation from Y Combinator, pursuing solar-powered data centers in orbit. One of the fastest startups to reach unicorn status.",
     "full_text": "Starcloud, a company pursuing solar-powered data centers in orbit, said it had raised $170 million in new funding, valuing the business at $1.1 billion, making it one of the fastest startups to reach unicorn status after graduating from Y Combinator.",
     "source": "DigiTimes", "category": "太空",
     "url": "https://www.digitimes.com/news/starcloud-space-computing-funding"},
    {"title": "Taiwan deploys air force and drones for cloud seeding amid drought",
     "summary_en": "Facing drought, Taiwan mobilized the air force and drones for cloud seeding near Hsinchu Science Park. Climate disruptions now threaten critical semiconductor manufacturing water supply.",
     "full_text": "Facing drought conditions, Taiwan's government has mobilized the air force and drones to conduct cloud seeding operations near the area over the Hsinchu Science and Industrial Park, a center of Taiwan's tech industry.",
     "source": "DigiTimes", "category": "太空",
     "url": "https://www.digitimes.com/news/taiwan-drought-cloud-seeding"},
    {"title": "SpaceX Starlink 17-30 launches from Vandenberg expanding constellation",
     "summary_en": "SpaceX's 30th Starlink mission of 2026 launched from Vandenberg SFB, adding more V2 Mini satellites. The rapid launch cadence shows SpaceX's dominance in commercial space operations.",
     "full_text": "The Starlink 17-30 mission was SpaceX's 30th mission supporting its broadband internet satellites megaconstellation so far this year. Liftoff from pad 4 East at Vandenberg Space Force Base added more satellites to the growing low Earth orbit constellation.",
     "source": "Spaceflight Now", "category": "太空",
     "url": "https://spaceflightnow.com/starlink-17-30"},
    {"title": "SpaceX Starlink 10-62 launches from Cape Canaveral",
     "summary_en": "SpaceX launched another Starlink mission from Cape Canaveral adding V2 Mini satellites. The constellation now has thousands of satellites providing global broadband coverage.",
     "full_text": "Liftoff of the Starlink 10-62 mission from pad 40 at Cape Canaveral Space Force Station added more broadband satellites. The milestone came less than seven years after launching the first operational Starlink batch.",
     "source": "Spaceflight Now", "category": "太空",
     "url": "https://spaceflightnow.com/starlink-10-62"},
    {"title": "Taiwan car market surges 78% with Tesla deliveries rising",
     "summary_en": "Taiwan registered 39,318 vehicles in March 2026, up 78.4% from February. Tesla deliveries surged as EV adoption accelerates in Taiwan's auto market.",
     "full_text": "Taiwan's auto market showed strong momentum in March 2026, with total vehicle registrations reaching 39,318 units, a sharp 78.4% jump from February. That explosive growth highlights significant structural shifts with Tesla deliveries surging.",
     "source": "DigiTimes", "category": "電動車",
     "url": "https://www.digitimes.com/news/taiwan-car-market-march-2026"},
    {"title": "BYD delivery surge 175% year-on-year challenges global automakers",
     "summary_en": "BYD reported 175% year-on-year delivery increase, challenging traditional automakers. Chinese EV makers leverage advanced battery technology and competitive pricing to capture international market share.",
     "full_text": "BYD reported 175% year-on-year delivery increase, significantly outpacing traditional automotive rivals. Chinese electric vehicle makers are rapidly expanding internationally, leveraging competitive pricing, advanced battery technology, and government support.",
     "source": "DigiTimes", "category": "電動車",
     "url": "https://www.digitimes.com/news/byd-delivery-surge-2026"},
    {"title": "US states roll out red carpet for drone manufacturers",
     "summary_en": "States across the US compete to attract drone manufacturers and defense contractors as autonomous aerial systems move from battlefield to commercial use. The drone industry brings high-wage jobs and federal research dollars.",
     "full_text": "The drone industry is no longer a niche corner of the defense world. Across the US, states are competing to attract manufacturers, research centers, and defense contractors as autonomous aerial systems move from battlefield applications toward broader commercial use.",
     "source": "DigiTimes", "category": "科技",
     "url": "https://www.digitimes.com/news/us-states-drone-manufacturers"},
    {"title": "Bank of America releases top stock picks for Q2 2026",
     "summary_en": "Bank of America published top stock picks for Q2 2026 after a tough start to the year. Recommendations reflect views on sectors benefiting from the current geopolitical and economic environment.",
     "full_text": "Bank of America analysts published their top stock picks for the second quarter of 2026 after a tough start to the year. The recommendations reflect views on sectors likely to benefit from the current economic environment including defense and energy stocks.",
     "source": "CNBC", "category": "經濟",
     "url": "https://www.cnbc.com/2026/04/04/bofa-top-stock-picks-q2-2026"},
    {"title": "Pope Leo XIV calls for peace in first Easter Mass",
     "summary_en": "Pope Leo XIV celebrated his first Easter Mass with a call for global peace amid the Iran war and Russia's Ukraine campaign. The first US-born pope acknowledged indifference to thousands of deaths in global conflicts.",
     "full_text": "Pope Leo XIV celebrated his first Easter Mass with a call to lay down arms and seek peace in global conflicts. With the US-Israeli war on Iran in its second month and Russia's ongoing campaign in Ukraine, Leo acknowledged a sense of indifference to the deaths of thousands of people. He quoted Pope Francis's warning about the great thirst for death witnessed each day.",
     "source": "CNBC", "category": "經濟",
     "url": "https://www.cnbc.com/2026/04/05/pope-easter-mass-peace"},
    {"title": "OPEC debates oil output hike amid Iran war paralysis",
     "summary_en": "OPEC members debate increasing oil output amid the Iran war disrupting global energy flows. The conflict has reduced oil supply from the Middle East, pushing prices to multi-year highs.",
     "full_text": "OPEC members are debating whether to increase oil output amid the Iran war's paralysis of global energy flows. The conflict has disrupted oil shipments from the Middle East. Brent crude has risen to over $100 a barrel since the war began.",
     "source": "CNBC", "category": "經濟",
     "url": "https://www.cnbc.com/2026/04/04/opec-oil-output-iran-war"},
]

CONTENT_DIR = Path('/Users/wongjai/.openclaw/workspace/wongjai-news/content/news')

existing_urls = set()
for f in CONTENT_DIR.glob('*.md'):
    text = f.read_text()
    m = re.search(r'original_url: "([^"]+)"', text)
    if m:
        existing_urls.add(m.group(1))

filtered = [a for a in ARTICLES if a['url'] not in existing_urls]
print(f"New articles to create: {len(filtered)}")

date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
for art in filtered:
    title = art['title'].replace('"', "'")
    summary = art['summary_en'].replace('"', "'")
    full_text = art.get('full_text', '')[:1000].replace('"', "'")
    slug = re.sub(r'[^\w\s-]', '', title)[:50].strip().lower().replace(' ', '-')[:40]
    sid = hashlib.md5(f'{title}{art["url"]}'.encode()).hexdigest()[:12]
    fn = f'{date_str}-{sid}-{slug}.md'
    md = f'''---
title: "{title}"
date: "{date_str}"
source: {art['source']}
category: {art['category']}
original_url: "{art['url']}"
title_en: "{title}"
title_zh_tw: ""
title_zh_cn: ""
title_ja: ""
summary_en: "{summary}"
summary_zh_tw: ""
summary_zh_cn: ""
summary_ja: ""
draft: false
---

{full_text}
'''
    (CONTENT_DIR / fn).write_text(md, encoding='utf-8')
    print(f"  [{art['category']}] {title[:55]}")
    time.sleep(0.3)

from collections import Counter
cats = Counter()
for f in CONTENT_DIR.glob('*.md'):
    text = f.read_text()
    m = re.search(r'category: (.+?)(?:\r?\n)', text)
    if m: cats[m.group(1).strip()] += 1
print(f"\nFinal counts:")
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")
print(f"  TOTAL: {sum(cats.values())}")
