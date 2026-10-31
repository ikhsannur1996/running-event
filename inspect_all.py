#!/usr/bin/env python3
"""Quick inspection of all 13 sites"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

sites = [
    ("jadwallari.id", "https://jadwallari.id/events/"),
    ("kalenderlari.com", "https://kalenderlari.com/jadwal/"),
    ("lariku.info", "https://lariku.info/"),
    ("indonesiamarathon.com", "https://indonesiamarathon.com/"),
    ("tias.co.id", "https://tias.co.id/kalender-lari"),
    ("ayolari.id", "https://ayolari.id/"),
    ("ruanglari.com", "https://ruanglari.com/jadwal-lari"),
    ("dorangadget.com", "https://dorangadget.com/jadwal-event-lari-indonesia/"),
    ("kalenderlari.net", "https://www.kalenderlari.net/"),
    ("eventlari.com", "http://eventlari.com/"),
    ("koncolari.com", "https://koncolari.com/event"),
]

for name, url in sites:
    print(f"\n{'='*70}")
    print(f"SITE: {name} - {url}")
    print('='*70)
    try:
        html = requests.get(url, headers=HEADERS, timeout=30).text
        soup = BeautifulSoup(html, 'lxml')
        print(f"  Size: {len(html)} bytes")
        
        # Pagination
        pag_links = []
        for a in soup.find_all('a', href=True):
            txt = a.get_text(' ', strip=True)
            href = a['href']
            if 'page' in href.lower() or txt.isdigit() or txt in ('Next','Prev','»','«','›','‹','Lebih banyak','Muat lebih','Selanjutnya','Halaman'):
                pag_links.append((txt, href))
        if pag_links:
            print(f"  Pagination links: {pag_links[:10]}")
        else:
            print(f"  Pagination: None found in HTML")
        
        # Event links
        event_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            txt = a.get_text(' ', strip=True)
            if any(kw in href.lower() for kw in ['/event', '/jadwal', '/detail', '/lomba']) and txt and len(txt) > 3:
                event_links.append((txt[:60], href))
        if event_links:
            print(f"  Event links sample: {event_links[:5]}")
            print(f"  Total event links: {len(event_links)}")
        else:
            print(f"  Event links: None found")
        
        # Check for JS rendering indicators
        if 'Memuat' in html or 'memuat' in html or 'loading' in html.lower()[:2000]:
            print(f"  JS Rendering: Likely (loading text found)")
        
        # Check for date patterns
        date_matches = re.findall(r'\d{1,2}\s+\w+\s+2026', html)
        print(f"  Date patterns (2026): {len(date_matches)} found")
        
    except Exception as e:
        print(f"  ERROR: {e}")
