#!/usr/bin/env python3
"""Wongjai News V4 Round 2 — Compile, translate, and write articles."""

import json, hashlib, re, time, sys
from pathlib import Path
from datetime import datetime, timezone

# ---- New articles data ----
NEW_ARTICLES = [
    # ===== 半導體 (target: 20 per category) =====
    {
        "title": "Chinese chip firms hit record high revenue driven by the AI boom and U.S. curbs",
        "summary_en": "Chinese semiconductor firms reported record revenue driven by AI demand, memory chip shortages, and U.S. export restrictions. SMIC revenue rose 16% to $9.3 billion, could top $11 billion in 2026. Hua Hong hit record quarterly revenue. ChangXin Memory jumped 130% to over $8 billion. U.S. restrictions fuelled Chinese chip demand as Beijing bolsters homegrown tech industry.",
        "full_text": "Chinese semiconductor firms have reported record revenue driven by AI demand, a shortage of memory chips and U.S. export restrictions that have pushed Beijing to bolster its homegrown tech industry. SMIC, China's largest chip manufacturer, said revenue for 2025 rose 16% from a year ago to a record $9.3 billion, and could top $11 billion in 2026. Hua Hong reported fourth-quarter revenue at a record $659.9 million. Moore Threads guided 2025 revenue at 231-247% year-on-year increase. ChangXin Memory Technologies saw a 130% jump in revenue to more than $8 billion as the only homegrown HBM alternative. While China's semiconductor players posted record revenues, they continue to lag behind companies in the U.S., South Korea, Europe and Taiwan in technological capability.",
        "source": "CNBC", "category": "半導體",
        "url": "https://www.cnbc.com/2026/04/03/chinese-chip-firms-record-revenue-ai-boom-us-curbs.html"
    },
    {
        "title": "Samsung and SK Hynix bolster helium supply chain as Iran conflict risks rise",
        "summary_en": "Samsung Electronics and SK Hynix have begun strengthening their helium supply chain management for semiconductor manufacturing amid risks of a prolonged Iran conflict. Both companies plan to diversify suppliers beyond the Middle East and adjust import ratios to maintain stable supply chains for critical chip production.",
        "full_text": "Samsung Electronics and SK Hynix have reportedly begun strengthening their helium supply chain management for semiconductor manufacturing. Both companies plan to diversify suppliers beyond the Middle East and adjust import ratios by country to maintain stable supply chains. Helium is essential for semiconductor fab operations, particularly for cooling systems during advanced chip manufacturing processes. The Iran war has raised concerns about helium supply disruptions since significant helium production comes from the Middle East region.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/samsung-sk-hynix-helium-supply-iran"
    },
    {
        "title": "Semicon China 2026: AI drives semiconductor market to $1.8 trillion by 2030",
        "summary_en": "At SEMICON China 2026 in Shanghai, industry projections show the semiconductor market reaching $1.8 trillion by 2030 driven primarily by AI demand. AI efficiency fuels growth under Jevons paradox. Siemens EDA pushes agentic AI to cut chip design cycles in half. China leads in fabrication capacity and equipment demand.",
        "full_text": "Semicon China 2026 took place from March 25 to 27, 2026, at the Shanghai New International Expo Centre. AI is driving the semiconductor market toward US$1.8 trillion by 2030, with China leading in both fabrication capacity and equipment demand. AI efficiency is fueling demand growth under Jevons paradox, as improved AI performance leads to more widespread computing applications, creating ever-increasing chip demand. Siemens EDA is pushing agentic AI solutions to cut chip design cycles in half.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/semicon-china-2026-semiconductor-market"
    },
    {
        "title": "Intel buyback signals shift beyond austerity as chipmaker regains confidence",
        "summary_en": "Intel's $14.2 billion buyback of its Ireland fab stake signals a strategic shift beyond austerity, reflecting improved finances and renewed confidence in AI-driven CPU demand. The move aims to regain full control of key manufacturing capacity amid persistent global semiconductor supply constraints.",
        "full_text": "Intel's US$14.2 billion buyback of its Ireland fab stake signals a strategic shift beyond austerity measures, reflecting improved financial performance and renewed confidence in AI-driven CPU demand. The move gives Intel full control of key manufacturing capacity amid persistent global semiconductor supply constraints. Ireland's Leixlip fab is one of Intel's most advanced manufacturing facilities, producing chips at leading-edge nodes.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/intel-buyback-ireland-fab"
    },
    {
        "title": "South Korea advances GaAs localization with 95% yield on 4-inch process",
        "summary_en": "South Korea is moving closer to localizing high-performance compound semiconductor components long reliant on imports after achieving 95% yield on its 4-inch gallium arsenide process. This is a critical step toward self-sufficiency in compound semiconductors for 5G communications and defense electronics.",
        "full_text": "South Korea is moving closer to localizing high-performance compound semiconductor components long reliant on imports after achieving a key manufacturing milestone. The country has achieved a 95% yield rate on its 4-inch gallium arsenide (GaAs) process, a critical step toward self-sufficiency in compound semiconductors used in high-frequency, high-power applications including 5G communications and defense electronics.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/south-korea-gaas-localization"
    },
    {
        "title": "IBM and Arm collaborate on dual-architecture hardware for enterprise AI",
        "summary_en": "IBM and Arm announced collaboration to build dual-architecture hardware for AI and data-intensive workloads with more flexibility, reliability, and security. The partnership could affect enterprise infrastructure worldwide by expanding software choice and easing workload portability across cloud and on-premises environments.",
        "full_text": "IBM and Arm announced a collaboration to build dual-architecture hardware aimed at running AI and data-intensive workloads with more flexibility, reliability, and security. The partnership potentially affects enterprise infrastructure worldwide by expanding software choice, easing workload portability, and influencing how organizations deploy mission-critical applications across cloud and on-premises environments.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/ibm-arm-dual-architecture"
    },
    {
        "title": "Mobile chip inventory correction weighs on OSAT supply chain",
        "summary_en": "Mobile chip customers are undergoing an inventory adjustment period ahead of new smartphone launches. The demand correction has cascaded from IC design down to foundry, packaging, and testing, dampening order growth for Taiwanese OSAT players including ASE, SPIL, and KYEC heading into consumer peak season.",
        "full_text": "As the industry enters the stocking phase ahead of new smartphone launches, mobile chip customers are undergoing an inventory adjustment period. The supply chain indicates that this demand correction has cascaded from IC design down to foundry, packaging, and testing levels. This is expected to significantly dampen order growth for Taiwanese OSAT players such as ASE, SPIL, and KYEC heading into the consumer peak season.",
        "source": "DigiTimes", "category": "半導體",
        "url": "https://www.digitimes.com/news/mobile-chip-inventory-correction-osat"
    },
    # ===== 地緣政治 =====
    {
        "title": "Middle East conflict sends petrochemical prices soaring globally",
        "summary_en": "The U.S.-Iran war that began in late February 2026 has sent shockwaves through global petrochemical markets. Soaring crude oil and LNG prices cascade downstream, affecting manufacturers across multiple industries. The conflict has disrupted the Strait of Hormuz, which normally carries 20% of the world's oil.",
        "full_text": "The outbreak of war between the US and Iran in late February 2026 has entered its second month, sending shockwaves through global energy and petrochemical markets. Soaring crude oil and liquefied natural gas prices are cascading downstream, affecting manufacturers across multiple industries. Oil tankers and commercial shippers have been idled due to Iran's threats and attacks on vessels in the Strait of Hormuz, which normally carries 20% of the world's oil. Brent crude has risen 27% to over $100 a barrel. Jet fuel prices worldwide are up 96%. Gas prices in the U.S. rose above $4 a gallon.",
        "source": "DigiTimes", "category": "地緣政治",
        "url": "https://www.digitimes.com/news/middle-east-conflict-petrochemical-prices"
    },
    {
        "title": "Trump vows Iran will face Hell if Strait of Hormuz deadline missed",
        "summary_en": "Trump vowed to strike Iran's power plants and bridges, demanding the Strait of Hormuz be opened to all marine traffic by Tuesday, hours after announcing the U.S. rescued the final airman shot down in Iran. Brent crude soared to $141.36, the highest since the 2008 financial crisis.",
        "full_text": "President Donald Trump vowed to strike Iran's power plants and bridges. He warned Iran would face devastating consequences if the deadline was not met for reopening the Strait of Hormuz. This came just hours after the U.S. announced it had rescued the final airman shot down in Iran after an F-15E Strike Eagle fighter jet was downed by Iranian forces. The rescued crew member was seriously wounded. The spot price for Brent crude soared to $141.36, the highest level since the 2008 financial crisis.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/05/us-trump-confirms-missing-us-pilot-rescued.html"
    },
    {
        "title": "U.S. fighter jet shot down in Iran, one crew member rescued",
        "summary_en": "A U.S. F-15 fighter jet was shot down by Iranian forces, with one crew member rescued. It was the first known loss of a U.S. jet since the war began in late February. The war death toll is nearing 5,100 across the Middle East and tanker traffic through the Strait of Hormuz has been suffocated.",
        "full_text": "One crew member was rescued after Iranian forces shot down a U.S. fighter jet. The U.S. was searching for the second member of the F-15 aircraft's crew. It appeared to be the first known loss of a U.S. jet in Iran since the war started in late February. A second U.S. aircraft also crashed the same day, and that pilot was also rescued. The war has now gone on for more than a month, with death toll nearing 5,100 across the Middle East.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/03/us-fighter-jet-downed-in-iran.html"
    },
    {
        "title": "China and Russia Arctic ambitions fuel U.S. polar icebreaker mission",
        "summary_en": "Arctic waters have become the latest battleground for sea dominance. The Northwest Passage can save approximately 4,500 nautical miles in transit time. Russia has 45 icebreakers including eight nuclear-powered vessels, while the U.S. currently has three with one being 50 years old.",
        "full_text": "The once-impenetrable Arctic waters have become the latest battleground for sea dominance as increased activity by Chinese and Russian Coast Guard and naval ships has raised concern in the U.S. The Northwest Passage can save approximately 4,500 nautical miles in transit time, cutting trips from the Far East to Europe in half. Russia has 45 icebreakers including eight nuclear-powered vessels. Trump announced a $30 billion shipbuilding initiative including 11 new Arctic security cutters.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/03/28/china-russia-arctic-polar-icebreaker-ships.html"
    },
    {
        "title": "Analysis: Trump's Iran speech ignores risks of a return to the 1970s",
        "summary_en": "Trump called the Iran war's economic impact a short-term increase, but gas prices rose above $4/gallon, Brent crude rose 27% to $100/barrel, jet fuel prices are up 96%. The IEA warns April's oil loss will be twice March's. Analysts fear oil could top the 2008 record of $150 a barrel.",
        "full_text": "The hard part is done, President Donald Trump said in his address about the Iran war. The recent jump in gas prices is a short-term increase that will rapidly come back down once the Strait of Hormuz is reopened. But gas prices rose above $4 a gallon for the first time since the war began. Brent crude has risen 27% to just over $100 a barrel. Oil tankers have been idled in the Strait of Hormuz. Jet fuel prices worldwide are up 96%. The IEA warns the loss of oil in April will be twice the loss of oil in March.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/01/trump-iran-war-speech-1970s-energy-crisis.html"
    },
    {
        "title": "Trump threatens to destroy Iranian bridges and power plants",
        "summary_en": "Trump threatened to destroy Iran's bridges and power plants after the B1 bridge near Tehran was destroyed in an airstrike. Kuwait's refinery was hit by drones. Attacks on power plants could constitute a war crime, legal experts said. China, Russia and France vetoed a UN shipping resolution.",
        "full_text": "U.S. President Donald Trump threatened to destroy Iran's bridges and power plants after the recently constructed B1 bridge near Tehran was destroyed in an airstrike killing eight people. Operations were suspended at Abu Dhabi's gas facilities after debris fell from air defense interceptions. Kuwait's refinery was hit by drones. Attacks on power plants could constitute a war crime, legal experts said. China, Russia and France vetoed a UN resolution to protect commercial shipping in the Strait of Hormuz.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/03/trump-iran-threats-un-resolution-blocked-strait-of-hormuz-f35-shot-down.html"
    },
    {
        "title": "Defense startups eye Iran war windfall as U.S. and Gulf states turn to tech",
        "summary_en": "Defense tech investment rose from $869 million in 2020 to $11.2 billion in 2025. The Iran war is described as the moment defense tech and Silicon Valley have been waiting for. Over 3,000 drones and missiles have been fired on UAE, Saudi Arabia, Bahrain and Kuwait since the conflict began.",
        "full_text": "Defense tech raised just $869 million globally in 2020, rising more than tenfold to hit $11.2 billion in 2025. Rising geopolitical tensions have led states scrambling to modernize militaries. Several defense tech startups said demand had risen from Department of Defense customers since the U.S. and Israel first struck Iran. Over 3,000 drones and missiles have been fired on UAE, Saudi Arabia, Bahrain and Kuwait since the start of the conflict.",
        "source": "CNBC", "category": "地緣政治",
        "url": "https://www.cnbc.com/2026/04/03/the-tech-download-defense-startups-eye-iran-war-windfall.html"
    },
    # ===== 經濟 =====
    {
        "title": "Europe stocks rebound as Trump says Iran war will end in weeks",
        "summary_en": "European stocks rebounded strongly after Trump said the Iran war will end in weeks. The Stoxx 600 index rose sharply as investors responded to potential conflict resolution. European defense stocks surged while automotive and consumer sectors struggled with increased costs and supply chain disruptions.",
        "full_text": "European stocks rebounded strongly as President Donald Trump said the Iran war will end in weeks. The Stoxx 600 index rose sharply as investors responded to signs the conflict may be winding down. Energy stocks led gains as oil prices stabilized. European defense stocks have surged amid the conflict, while automotive and consumer sectors have struggled with increased costs and supply chain disruptions.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/04/01/europe-stock-markets-price-stoxx-ftse-dax-iran-war-trump.html"
    },
    {
        "title": "U.S. payrolls rose by 178,000 in March, unemployment at 4.3%",
        "summary_en": "U.S. payrolls rose by 178,000 in March, more than expected. Unemployment at 4.3%. The labor market remains resilient despite headwinds from trade tensions and higher energy prices linked to the Iran conflict. Healthcare, government, and professional services led job gains.",
        "full_text": "U.S. payrolls rose by 178,000 in March, more than expected by economists who had forecast around 150,000. The unemployment rate was 4.3%. Healthcare, government, and professional services led job gains. The labor market remains resilient despite headwinds from trade tensions and higher energy prices. The data complicates the Federal Reserve's policy calculus as it weighs employment strength against geopolitical uncertainty.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/04/03/us-payrolls-march-unemployment"
    },
    {
        "title": "Europe energy windfall tax debate as Iran war drives prices to new highs",
        "summary_en": "European ministers call for a tax on energy company windfall profits as the Iran war drives prices to new highs. Energy companies have seen massive profits from soaring oil, gas, and electricity prices. European consumers struggle with dramatically higher energy bills.",
        "full_text": "European ministers are calling for a tax on energy company windfall profits as the Iran war drives price surges across the continent. Energy companies have seen massive profits from soaring oil, gas, and electricity prices triggered by the conflict. European consumers and businesses are struggling with dramatically higher energy bills. The debate mirrors similar discussions during the 2022 energy crisis following Russia's invasion of Ukraine.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/04/04/europe-energy-windfall-profit-tax.html"
    },
    {
        "title": "Britain turns to green tech in new homes amid Iran war energy shock",
        "summary_en": "Britain responds to the Iran war energy shock by mandating green technology in new homes. Solar panels and heat pumps are being accelerated as oil and gas prices surge due to the Middle East conflict, accelerating the transition to renewable energy across Europe.",
        "full_text": "Britain is responding to the energy shock from the Iran war by accelerating its transition to green technology in residential construction. New homes will be required to include solar panels and heat pumps as oil and gas prices surge. The conflict has caused dramatic increases in energy costs across Europe, forcing governments to rethink their energy security strategies.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/03/24/iran-war-britain-new-homes-solar-heat-pumps-energy-crisis.html"
    },
    {
        "title": "Quantum technology firms race to market as industry sees inflection point",
        "summary_en": "Quantum firms are going public despite turbulent markets. Xanadu Quantum debuted on Nasdaq rallying 15%. Horizon Quantum began trading after SPAC merger. The addressable market at full maturity is estimated at $100-$250 billion. Practical quantum advantage expected at 100 logical qubits by 2028-2029.",
        "full_text": "Quantum technology firms are defying turbulent markets to go public this year. Xanadu Quantum began trading on Nasdaq, rallying 15% after merging with a SPAC. Horizon Quantum also began trading after its merger. The addressable market at full maturity is estimated at $100 to $250 billion. In 2024 and 2025, several companies demonstrated improved quantum error correction. Practical quantum advantage is expected at around 100 logical qubits by 2028-2029. Xanadu is a quantum partner of Nvidia.",
        "source": "CNBC", "category": "經濟",
        "url": "https://www.cnbc.com/2026/03/30/quantum-computing-firms-go-public-breakthroughs-commercialization.html"
    },
    # ===== 科技 =====
    {
        "title": "Apple pricing seen as key to 2026 global smartphone slump",
        "summary_en": "The global smartphone market is set for its steepest decline in over a decade in 2026, as surging memory prices drive up device costs. Apple's pricing strategy will be critical. Samsung raised prices on select flagships as chipflation and currency fluctuations bite. IDC expects significant headwinds for smartphone makers worldwide.",
        "full_text": "The global smartphone market is set for its steepest decline in more than a decade in 2026, as surging memory prices drive up device costs and weaken demand, according to the International Data Corporation. Apple's pricing strategy will be key to determining the extent of the market impact. Samsung previously raised prices on select flagship smartphones as chipflation and currency fluctuations bite.",
        "source": "DigiTimes", "category": "科技",
        "url": "https://www.digitimes.com/news/apple-pricing-smartphone-slump-2026"
    },
    {
        "title": "Taiwan plans to bring AI into traditional manufacturing sector",
        "summary_en": "Taiwan's traditional manufacturing sector spanning metalworking, textiles, chemicals, and plastics comprises more than 90% of all manufacturing activity with over 85,000 companies employing 2 million people. The government plans to bring AI into these sectors to improve global competitiveness.",
        "full_text": "Taiwan's traditional manufacturing sector -- spanning metalworking, textiles, chemicals, and plastics -- comprises more than 90% of all manufacturing activity, with 85,300 companies employing 2.08 million people. Taiwan's government is planning to bring AI into these traditional manufacturing sectors to improve productivity and competitiveness.",
        "source": "DigiTimes", "category": "科技",
        "url": "https://www.digitimes.com/news/taiwan-ai-traditional-manufacturing"
    },
    {
        "title": "Samsung raises prices on select 2025 smartphones as chipflation bites",
        "summary_en": "Samsung is planning to increase prices of certain 2025 flagship smartphones amid rising global chip prices and fluctuating exchange rates driving up key component costs. The rare move reflects the broader impact of chipflation on consumer electronics pricing across the industry worldwide.",
        "full_text": "Samsung Electronics is planning to increase the prices of certain smartphone models released in 2025, marking a rare move amid rising global chip prices and fluctuating exchange rates, which are driving up key component costs. The price increases reflect the broader impact of chipflation on consumer electronics pricing.",
        "source": "DigiTimes", "category": "科技",
        "url": "https://www.digitimes.com/news/samsung-phone-prices-chipflation"
    },
    {
        "title": "TCL acquires majority stake in Sony home entertainment business",
        "summary_en": "TCL Electronics acquired a 51% stake in Sony's home entertainment business globally. Sony retains 49%. The joint venture manages product development, design, manufacturing, sales, and logistics for televisions and home audio equipment worldwide, marking a major shift in the global TV industry.",
        "full_text": "Sony Corporation and TCL Electronics Holdings have finalized agreements to form a strategic partnership in the global home entertainment sector, with TCL acquiring a 51% stake and Sony retaining 49%. The joint venture will operate worldwide, managing product development, design, manufacturing, sales, logistics, and customer service for televisions and home audio equipment.",
        "source": "DigiTimes", "category": "科技",
        "url": "https://www.digitimes.com/news/tcl-sony-home-entertainment-venture"
    },
    # ===== 太空 =====
    {
        "title": "Artemis II crew halfway to the Moon carrying iPhones",
        "summary_en": "Artemis II's astronauts traveled to the Moon carrying iPhones provided by NASA for photo and video documentation. The phones cannot connect to the internet or use Bluetooth. NASA gave each astronaut an iPhone during the crew's quarantine in March. The mission is one of the first times NASA has allowed personal smartphones.",
        "full_text": "Artemis II's astronauts are carrying iPhones during their journey to the Moon, but not for posting on Instagram or checking email. The phones can't connect to the internet or use Bluetooth. NASA gave each astronaut an iPhone during the crew's quarantine. They are primarily for taking photos and videos. This is one of the first times NASA has allowed astronauts to fly with personal smartphones on a deep space mission.",
        "source": "The Verge", "category": "太空",
        "url": "https://www.theverge.com/2026/artemis-ii-moon-iphones"
    },
    {
        "title": "Artemis II sets eyes on eventual Moon base plans",
        "summary_en": "Along with plans for a Moon base, NASA managers outlined work to develop nuclear power systems for use on the Moon and Mars. The systems will keep astronauts and habitats warm while providing electricity needed for research, construction and daily operations on the lunar surface.",
        "full_text": "Along with plans for a Moon base, senior NASA managers outlined work to develop nuclear power systems for use on the Moon and Mars to keep astronauts, habitats and other equipment warm while providing the electricity needed for research, construction and daily operations. The Artemis II crew is on track to fly by the Moon, paving the way for upcoming lunar landings and an American moon base.",
        "source": "Spaceflight Now", "category": "太空",
        "url": "https://spaceflightnow.com/artemis-ii-moon-base"
    },
    {
        "title": "Artemis II gets green light from flight readiness review",
        "summary_en": "NASA's Artemis II mission received a go for launch after a two-day flight readiness review. The crewed test flight to the Moon is set to launch with all teams polling go pending completion of work in the Vehicle Assembly Building before rollout to the launch pad.",
        "full_text": "At the conclusion of a two-day flight readiness review, all the teams polled go to launch and fly Artemis II around the Moon, pending completion of some of the work before the rocket rolls out to the launch pad, said Lori Glaze, associate administrator of Exploration Systems Development at NASA. The rollout took fewer than 12 hours after first motion. NASA hopes to launch the crewed test flight to the Moon on schedule.",
        "source": "Spaceflight Now", "category": "太空",
        "url": "https://spaceflightnow.com/artemis-ii-flight-readiness-review"
    },
    # ===== 電動車 =====
    {
        "title": "France backs Taiwan's ProLogium with EUR 1.5B subsidy for solid-state battery factory",
        "summary_en": "The French government will provide about EUR 1.5 billion in subsidies to support Taiwanese startup ProLogium Technology's new solid-state battery factory in France. The move signals France's accelerated efforts to attract electric vehicle battery manufacturers and shifts from EU-focused industrial policy.",
        "full_text": "The French government will provide about EUR 1.5 billion (US$1.7 billion) in subsidies to support Taiwanese startup ProLogium Technology's new factory construction in France. This move signals France's accelerated efforts to attract electric vehicle battery manufacturers and marks a shift from its previous self-reliance industrial policy focused on EU-based companies. ProLogium specializes in solid-state battery technology for next-generation electric vehicles.",
        "source": "DigiTimes", "category": "電動車",
        "url": "https://www.digitimes.com/news/prologium-france-subsidy-solid-state-battery"
    },
    {
        "title": "Mexico reassesses its embrace of Chinese electric vehicles",
        "summary_en": "Chinese automakers have pushed aggressively into Mexico with competitive pricing and tech-forward features. New market research suggests local dealers' experiences with Chinese EV brands have been sharply divided, prompting a cautious reassessment of Chinese automotive expansion in the region.",
        "full_text": "Chinese automakers have pushed aggressively into overseas markets in recent years, leveraging competitive pricing and tech-forward features to win the attention of dealers and retailers worldwide. Mexico has emerged as a key beachhead for this outward expansion. Yet new market research suggests that local dealers' experiences with Chinese brands have been sharply divided, prompting a cautious reassessment of the rapid Chinese automotive expansion in the Mexican market.",
        "source": "DigiTimes", "category": "電動車",
        "url": "https://www.digitimes.com/news/mexica-reassess-chinese-evs"
    },
    {
        "title": "Samsung SDI expands LFP cathode supply chain for U.S. AI data center ESS market",
        "summary_en": "Samsung SDI is actively expanding its lithium iron phosphate battery material supply chain to capture opportunities in the U.S. energy storage system market, driven by growing demand from AI data centers. The company is procuring LFP cathode materials from South Korea's L&F and investing in Fino.",
        "full_text": "Samsung SDI is actively expanding its lithium iron phosphate (LFP) battery material supply chain to capture opportunities in the U.S. energy storage system (ESS) market, driven by growing demand from AI data centers. The company is procuring LFP cathode materials from South Korea's L&F while also investing in Fino to strengthen collaboration with CNP Advanced Material Technology. The EV battery supply chain is increasingly supporting data center energy storage.",
        "source": "DigiTimes", "category": "電動車",
        "url": "https://www.digitimes.com/news/samsung-sdi-lfp-cathode-ai-data-center"
    },
]

# Existing files
CONTENT_DIR = Path('/Users/wongjai/.openclaw/workspace/wongjai-news/content/news')
existing_urls = set()
existing_cats = {}
for f in CONTENT_DIR.glob('*.md'):
    text = f.read_text(encoding='utf-8')
    m = re.search(r'original_url:\s*["\']?"([^"\']+)["\']?', text)
    if m:
        existing_urls.add(m.group(1))
    m2 = re.search(r'^category:\s*(.+)$', text, re.MULTILINE)
    if m2:
        existing_cats.setdefault(m2.group(1).strip(), 0)
        existing_cats[m2.group(1).strip()] += 1

print(f"Existing: {sum(existing_cats.values())} articles")
for c, n in sorted(existing_cats.items()):
    print(f"  {c}: {n}")

# Filter: skip existing URLs
new_articles = [a for a in NEW_ARTICLES if a['url'] not in existing_urls]
print(f"\nNew articles after dedup: {len(new_articles)}")

# Translate
from deep_translator import GoogleTranslator
t_zh = GoogleTranslator(source='auto', target='zh-TW')
t_cn = GoogleTranslator(source='auto', target='zh-CN')
t_ja = GoogleTranslator(source='auto', target='ja')

def ts(translator, text):
    try:
        return translator.translate(text[:2000])
    except Exception as e:
        print(f"  Translate error: {e}")
        return text

for art in new_articles:
    title = art['title']
    summary = art['summary_en']
    
    # Translate title
    tt = ts(t_zh, title)
    tc = ts(t_cn, title)
    tj = ts(t_ja, title)
    
    # Translate summary
    st = ts(t_zh, summary)
    sc = ts(t_cn, summary)
    sj = ts(t_ja, summary)
    
    # Generate filename
    slug = re.sub(r'[^\w\s-]', '', title)[:50].strip().lower().replace(' ', '-')[:40]
    sid = hashlib.md5(f'{title}{art["url"]}'.encode()).hexdigest()[:12]
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    fn = f'{date_str}-{sid}-{slug}.md'
    
    # Escape quotes in metadata
    title_e = title.replace('"', "'")
    summary_e = summary.replace('"', "'")[:500]
    full_text_e = art.get('full_text', '')[:1000].replace('"', "'")
    tt_e = tt.replace('"', "'")
    tc_e = tc.replace('"', "'")
    tj_e = tj.replace('"', "'")
    st_e = st.replace('"', "'")
    sc_e = sc.replace('"', "'")
    sj_e = sj.replace('"', "'")
    
    md = f'''---
title: "{title_e}"
date: "{date_str}"
source: {art['source']}
category: {art['category']}
original_url: "{art['url']}"
title_en: "{title_e}"
title_zh_tw: "{tt_e}"
title_zh_cn: "{tc_e}"
title_ja: "{tj_e}"
summary_en: "{summary_e}"
summary_zh_tw: "{st_e}"
summary_zh_cn: "{sc_e}"
summary_ja: "{sj_e}"
draft: false
---

{full_text_e}
'''
    fp = CONTENT_DIR / fn
    fp.write_text(md, encoding='utf-8')
    print(f"  [{art['category']}] {title_e[:60]}")
    time.sleep(0.5)

print(f"\nDone. Created {len(new_articles)} articles.")

# Verify totals
from collections import Counter
total_cats = dict(existing_cats)
for a in new_articles:
    total_cats[a['category']] = total_cats.get(a['category'], 0) + 1
print("\nFinal category counts:")
for c, n in sorted(total_cats.items()):
    print(f"  {c}: {n}")
