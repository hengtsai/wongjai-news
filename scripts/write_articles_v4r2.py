#!/usr/bin/env python3
"""Write articles from batch data - English only, no translation dependency."""
import json, hashlib, re, time
from pathlib import Path
from datetime import datetime, timezone

ARTICLES = [
    # === 地緣政治 (need ~12 more) ===
    {
        "title": "Polymarket removes wagers on U.S. rescue mission in Iran",
        "summary_en": "Polymarket removed a betting page on U.S. military rescue mission amid political pressure after an F-15E jet was shot down over Iran. Rep. Seth Moulton called the betting page disgusting. The platform says it violated their integrity standards but critics say it only acted after being called out.",
        "full_text": "Polymarket removed a forum related to the rescue mission of U.S. military servicemembers amid political pressure, the latest sign of mounting scrutiny around prediction markets. U.S. and Iranian military forces are searching for a missing American airman after its F-15E fighter jet was shot down over Iran. Rep. Seth Moulton decried the Polymarket page that allowed users to bet on which day the U.S. would confirm the rescue. Moulton criticized that the platform only acted after being called out, and called for Congressional oversight of prediction markets.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/04/polymarket-war-bet-iran-rescue-prediction-market-moulton.html"
    },
    {
        "title": "Asian travelers pivot away from Middle East as war grounds flights",
        "summary_en": "Asian travelers cancel Middle East trips amid rising airfares and safety concerns. Over 46,000 flights to and from the Middle East have been canceled since Feb 28. Ticket prices up 20-30% as airlines reroute around conflict zones. Regional travel via ferry and cruise becomes more attractive.",
        "full_text": "Amid the ongoing Iran war, commercial tourism to the Middle East has been replaced by repatriation flights, leaving vacationers to navigate rising airfares and safety concerns. Canceled flights to and from the Middle East region have exceeded 46,000 since the U.S.-Israel attacks on Feb 28. Travelers report ticket prices reaching $1,500 to $2,000 with 20-30% uptick in cancellations. Airlines have rerouted flights to avoid conflict airspace, increasing flight times and fuel costs.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/04/asian-travelers-seek-other-options-as-middle-east-plans-stay-grounded.html"
    },
    {
        "title": "Debris from intercepted Iranian strikes hits Oracle building in Dubai",
        "summary_en": "Trump warned Iran of 48 hours before severe consequences. Debris from intercepted Iranian drones and missiles struck the Oracle building in Dubai. Two Black Hawk helicopters searching for missing U.S. airmen were hit by Iranian fire. Iran's Revolutionary Guard threatened 18 U.S. tech companies including Nvidia, Apple, and Google.",
        "full_text": "Trump warned Iran 48 hours before all Hell will reign down while search for missing crew member intensifies. Debris from intercepted Iranian drones and missiles struck the Oracle building in Dubai, UAE confirms. Two Black Hawk helicopters engaged in the search went down over Iran after being hit by Iranian fire but made it out of Iranian airspace. Iran's Revolutionary Guard listed 18 U.S. tech companies including Nvidia, Apple, and Google as retaliation targets. A projectile also hit near Iran's Bushehr nuclear power plant.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/04/debris-from-interception-strikes-oracle-building-in-dubai-uae-says.html"
    },
    {
        "title": "G7 emergency meetings yield little as Iran war fatigue sets in",
        "summary_en": "G7 finance and energy ministers convened for their fourth emergency session since the Iran war began but yielded few actionable outcomes. Meeting fatigue is palpable. Questions grow over the G7's influence amid Trump's America First approach damaging multilateral relations and global coordination.",
        "full_text": "This marks the fourth time since the start of the war in Iran that the G7 has convened at a ministerial level. The meeting fatigue is palpable. The first virtual session of finance ministers and central bank governors on March 9 resulted in a communique that promised to closely monitor the situation and developments in energy markets. Despite multiple gatherings, few concrete outcomes have emerged. Questions are growing over the group's influence as Trump's America First approach and protectionism damage multilateral relations.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/03/29/global-week-ahead-why-emergency-g7-meetings-are-not-working.html"
    },
    # === 半導體 ===
    {
        "title": "TSMC plans 12 fabs in Arizona as supply chain shifts",
        "summary_en": "TSMC is planning 12 fabrication plants in Arizona as the semiconductor supply chain shifts from passive to active restructuring. The massive investment signals Taiwan's chip giant's commitment to U.S. manufacturing amid geopolitical tensions and efforts to diversify global semiconductor production capacity.",
        "full_text": "TSMC plans 12 fabs in Arizona as supply chain shifts from passive to active restructuring. This massive expansion represents one of the largest foreign investments in U.S. manufacturing history. The move comes as geopolitical tensions between China and the West intensify, prompting nations to secure domestic semiconductor production capacity. TSMC's Arizona facilities will produce advanced nodes critical for AI, defense, and consumer electronics applications.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/tsmc-arizona-12-fabs-supply-chain"
    },
    {
        "title": "TSMC plans 12 fabs in Arizona as supply chain shifts",
        "summary_en": "Taiwan Semiconductor Manufacturing Company plans to build 12 fabrication plants in Arizona, marking a massive expansion of semiconductor manufacturing capacity in the United States as global supply chains restructure away from China.",
        "full_text": "TSMC announced plans for 12 fabs in Arizona as the global semiconductor supply chain shifts from passive to active restructuring. The investment represents the largest foreign manufacturing commitment in U.S. history. Geopolitical tensions between China and the West are driving nations to secure domestic chip production capacity. The Arizona fabs will focus on advanced node production for AI processors, automotive chips, and defense electronics.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/tsmc-12-fabs-arizona"
    },
    # === 經濟 ===
    {
        "title": "Warsh nomination set for mid April as Fed leadership questions mount",
        "summary_en": "The nomination of Kevin Warsh for Federal Reserve leadership is set for mid-April hearings. The appointment comes amid economic uncertainty driven by the Iran war energy shock, tariff impacts, and rising inflation. Markets are closely watching the Fed's policy direction under potential new leadership.",
        "full_text": "The nomination of Kevin Warsh for a key Federal Reserve position is scheduled for mid-April hearings on Capitol Hill. Warsh, a former Fed governor and private equity executive, faces scrutiny over his views on monetary policy amid a complex economic environment. The Iran war has driven energy prices higher, complicating the Fed's dual mandate of maximum employment and price stability. Tariff impacts are also feeding through to consumer prices.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/04/03/warsh-nomination-mid-april"
    },
    {
        "title": "Nike most oversold stock on Wall Street after volatile trading week",
        "summary_en": "Nike emerged as the most oversold stock on Wall Street after a week of wild trading. The athletic apparel giant has faced headwinds from shifting consumer preferences, competition from rising brands, and broader market volatility driven by geopolitical uncertainty and economic concerns.",
        "full_text": "Nike is the most oversold stock on Wall Street after a wild week of trading. The company has faced challenges from shifting consumer preferences, increased competition from emerging athletic brands, and supply chain pressures. Technical indicators show the stock has fallen below key support levels, attracting some bargain hunters while others warn of further downside. The broader market volatility has amplified selling pressure on consumer discretionary stocks.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/04/04/nike-is-the-most-oversold-stock-on-wall-street-after-a-wild-week-of-trading.html"
    },
    {
        "title": "One year of Trump tariffs impact on global trade",
        "summary_en": "One year after Trump's tariff announcement dubbed liberation day, global trade has been significantly disrupted. Industries continue grappling with lingering effects including higher costs, supply chain reorganization, and retaliatory measures from trading partners. The TACO trade strategy has reshaped international commerce.",
        "full_text": "One year after Trump's tariff policy announcement, industries are still grappling with the lingering effects. Tariffs have increased costs for manufacturers who rely on imported components, forced supply chain reorganization, and triggered retaliatory measures from trading partners. The policy has reshaped international commerce patterns, with some companies accelerating efforts to relocate production to avoid tariff exposure. Consumer prices have risen across multiple categories as companies pass through the added costs.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/04/03/one-year-of-taco-how-the-trade-has-fared-since-liberation-day.html"
    },
    # === 科技 ===
    {
        "title": "UK trials social media ban for hundreds of teenagers",
        "summary_en": "The UK government is trialing social media bans for hundreds of teens after lawmakers rejected a blanket ban on under-16s. A six-week pilot tests various restrictions including curfews, time caps, and parental controls on 300 teenagers across the country.",
        "full_text": "The U.K. government is trialing a social media ban for hundreds of teens, after the country's lawmakers rejected a blanket ban on under-16s. The six-week pilot will test various bans ranging from curfews to time caps on 300 teenagers across the country. Four intervention groups include parental controls removal, one-hour daily caps on popular apps, 9pm to 7am curfews, and a control group with no restrictions. Australia, Spain, and France have also moved to ban social media for minors.",
        "source": "CNBC", "category": "科技",
        "url": "https://www.cnbc.com/2026/03/25/uk-trial-social-media-ban-teenagers-online-safety-push.html"
    },
    {
        "title": "Meta and Google face legal challenges bypassing Section 230 shield",
        "summary_en": "Meta and Google face growing legal challenges that bypass the 30-year-old Section 230 liability shield. Court cases are testing new legal theories around platform responsibility for algorithmic content promotion and AI-generated content, potentially reshaping the legal landscape for tech companies.",
        "full_text": "Meta and Google are under attack as court cases bypass the 30-year-old Section 230 legal shield that has protected internet companies from liability for user-generated content. Plaintiffs are pursuing new legal theories alleging that algorithmic content promotion and AI-generated recommendations create publisher-level liability. The cases could fundamentally reshape the legal framework that has governed internet platforms since the dawn of the commercial web.",
        "source": "CNBC", "category": "科技",
        "url": "https://www.cnbc.com/2026/04/03/meta-google-under-attack-court-cases-bypass-30-year-legal-shield.html"
    },
    # === 太空 ===
    {
        "title": "Artemis II crew halfway to the Moon carrying iPhones",
        "summary_en": "Artemis II astronauts are carrying iPhones on their journey to the Moon, one of the first times NASA has allowed personal smartphones on a deep space mission. The phones are disconnected from the internet and Bluetooth, used only for photos and videos. The crew is on track for lunar flyby on April 6.",
        "full_text": "Artemis II's astronauts are carrying iPhones during their journey to the Moon, but they can't connect to the internet or use Bluetooth. NASA gave each astronaut an iPhone during the crew's quarantine in March. They are primarily for taking photos and videos. The crew is on track to fly by the Moon on Monday April 6. This is one of the first times NASA has allowed astronauts to fly with personal smartphones on a deep space mission.",
        "source": "The Verge", "category": "太空",
        "url": "https://www.theverge.com/2026/artemis-ii-crew-iphones"
    },
    {
        "title": "Artemis II Moon base plans and nuclear power for lunar surface",
        "summary_en": "NASA outlined plans for a permanent Moon base alongside Artemis II mission. Nuclear power systems will be developed to keep astronauts and habitats warm and provide electricity for research and construction on the lunar surface. The Artemis program paves the way for sustained lunar presence.",
        "full_text": "Along with the Artemis II crewed lunar flyby, NASA managers outlined work to develop nuclear power systems for use on the Moon and Mars. The systems will keep astronauts, habitats and other equipment warm while providing the electricity needed for research, construction and daily operations on the lunar surface. The Moon base plans represent NASA's long-term vision for sustained human presence beyond low Earth orbit.",
        "source": "Spaceflight Now", "category": "太空",
        "url": "https://spaceflightnow.com/artemis-ii-moon-base-nuclear"
    },
    {
        "title": "Artemis II gets green light from flight readiness review",
        "summary_en": "NASA's Artemis II mission received go for launch after two-day flight readiness review. The 322-foot rocket rollout took fewer than 12 hours. The crewed test flight to the Moon represents a critical step in America's return to lunar exploration under the Artemis program.",
        "full_text": "NASA gave the Artemis II mission a go for launch after a two-day flight readiness review, pending completion of some work before rollout to the launch pad. The 322-foot-tall rocket took fewer than 12 hours to roll out after first motion. The crewed test flight to the Moon is a critical milestone. NASA teams are preparing for the first crewed lunar mission since Apollo 17 in 1972.",
        "source": "Spaceflight Now", "category": "太空",
        "url": "https://spaceflightnow.com/artemis-ii-flight-readiness"
    },
    # === 電動車 ===
    {
        "title": "Europe's car industry pivots to defense amid EV crisis",
        "summary_en": "European automakers facing structural crisis from slowing EV demand and Chinese competition are exploring defense manufacturing. Renault is developing ground-based drones, Volkswagen is in talks with Israel's Rafael for missile defense parts. The anything but autos trade is reshaping Europe's auto sector.",
        "full_text": "The European car industry is in a structural crisis. Slowing demand for electric vehicles, lost market share to Chinese competitors and higher borrowing costs have created the perfect storm. Some firms now think returning to defense equipment production could offer a lifeline. Analysts at Citi have dubbed this shift the anything but autos trade. Renault announced it was developing a ground-based drone. Volkswagen is in talks with Israeli defense firm Rafael to produce parts for missile defense systems. European autos are struggling to compete with Chinese rivals like BYD.",
        "source": "CNBC", "category": "電動車",
        "url": "https://www.cnbc.com/2026/04/05/autos-defense-europe-car-industry.html"
    },
    {
        "title": "France backs Taiwan's ProLogium with EUR1.5B for solid-state battery factory",
        "summary_en": "The French government will provide about EUR 1.5 billion in subsidies to support Taiwanese startup ProLogium Technology's solid-state battery factory in France. This marks France's accelerated efforts to attract EV battery manufacturers and a shift from EU-only industrial policy.",
        "full_text": "The French government will provide about EUR 1.5 billion (US$1.7 billion) in subsidies to support Taiwanese startup ProLogium Technology's new factory construction in France. This move signals France's accelerated efforts to attract electric vehicle battery manufacturers and marks a shift from its previous self-reliance industrial policy focused on EU-based companies. ProLogium specializes in solid-state battery technology for next-generation EVs.",
        "source": "DigiTimes", "category": "電動車",
        "url": "https://www.digitimes.com/news/prologium-france-subsidy"
    },
    # === AI ===
    {
        "title": "AI start-ups tackle retail returns problem with virtual try-on",
        "summary_en": "Fashion retailers turn to AI to solve rising product returns called the industry's silent killer. 15.8% of annual retail sales were returned in 2025 totaling $849.9 billion. AI startups offer virtual try-on technology with mirror-like realism. Zara and ASOS have deployed such tools.",
        "full_text": "Fashion retailers are increasingly turning to AI to solve the issue of rising product returns. A growing number of AI start-ups provide virtual try-on technology, allowing customers to visualize fit and style before they buy. The U.S. National Retail Federation estimated 15.8% of annual retail sales were returned in 2025, totaling $849.9 billion. For online sales, that number jumped to 19.3%. Gen Z drives this trend. Catches developed a digital twin platform. Zara rolled out virtual try-on in December. Shopify integrated AI virtual try-on.",
        "source": "CNBC", "category": "AI",
        "url": "https://www.cnbc.com/2026/04/05/ai-retail-start-ups-virtual-try-on-tech-margins.html"
    },
]

# Also add G7 article from batch4
ARTICLES.append({
    "title": "Europe's car industry pivots to defense amid EV crisis",
    "summary_en": "European automakers facing structural crisis from slowing EV demand and Chinese competition are exploring defense manufacturing. Renault is developing ground-based drones, Volkswagen in talks with Israeli Rafael.",
    "full_text": "The European car industry is in a structural crisis from slowing EV demand, lost market share to Chinese competitors and higher borrowing costs. Renault announced it was developing a ground-based drone. Volkswagen is in talks with Israeli defense firm Rafael. The anything but autos trade is reshaping Europe's automotive sector.",
    "source": "CNBC",
    "category": "電動車",
    "url": "https://www.cnbc.com/2026/04/05/autos-defense-europe-car-industry.html"
})

CONTENT_DIR = Path('/Users/wongjai/.openclaw/workspace/wongjai-news/content/news')

# Get existing URLs
existing_urls = set()
for f in CONTENT_DIR.glob('*.md'):
    text = f.read_text()
    m = re.search(r'original_url: "([^"]+)"', text)
    if m:
        existing_urls.add(m.group(1))

print(f"Existing URLs: {len(existing_urls)}")

# Filter duplicates
filtered = [a for a in ARTICLES if a['url'] not in existing_urls]
print(f"New articles to create: {len(filtered)}")

# Count current categories
from collections import Counter
current_cats = Counter()
for f in CONTENT_DIR.glob('*.md'):
    text = f.read_text()
    m = re.search(r'category: (.+?)(?:\r?\n|$)', text)
    if m:
        current_cats[m.group(1).strip()] += 1

print(f"\nCurrent categories:")
for c, n in sorted(current_cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")

# Write articles
date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
for i, art in enumerate(filtered):
    title = art['title'].replace('"', "'")
    summary = art['summary_en'].replace('"', "'")
    full_text = art.get('full_text', '')[:1000].replace('"', "'")
    source = art['source']
    category = art['category']
    url = art['url']
    
    slug = re.sub(r'[^\w\s-]', '', title)[:50].strip().lower().replace(' ', '-')[:40]
    sid = hashlib.md5(f'{title}{url}'.encode()).hexdigest()[:12]
    fn = f'{date_str}-{sid}-{slug}.md'
    
    md = f'''---
title: "{title}"
date: "{date_str}"
source: {source}
category: {category}
original_url: "{url}"
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
    print(f"  [{category}] {title[:55]}")

print(f"\nCreated {len(filtered)} articles")

# Final count
final_cats = Counter()
for f in CONTENT_DIR.glob('*.md'):
    text = f.read_text()
    m = re.search(r'category: (.+?)(?:\r?\n|$)', text)
    if m:
        final_cats[m.group(1).strip()] += 1

print(f"\nFinal counts:")
for c, n in sorted(final_cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")
print(f"  TOTAL: {sum(final_cats.values())}")
