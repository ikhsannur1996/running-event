#!/usr/bin/env python3
"""Inspect tias.co.id structure"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

html = requests.get('https://tias.co.id/kalender-lari', headers=HEADERS, timeout=30).text
soup = BeautifulSoup(html, 'lxml')

print("=== PAGINATION LINKS ===")
for a in soup.find_all('a', href=True):
    txt = a.get_text(' ', strip=True)
    href = a['href']
    if 'page' in href.lower() or txt.isdigit() or txt in ('Next','Prev','»','«','›','‹','Lebih banyak','Muat lebih','Selanjutnya'):
        print(f'  TEXT={txt!r} HREF={href}')

print("\n=== EVENT LINKS ===")
count = 0
for a in soup.find_all('a', href=True):
    href = a['href']
    txt = a.get_text(' ', strip=True)
    if ('/event' in href.lower() or '/kalender' in href.lower()) and txt and len(txt) > 3:
        print(f'  {txt[:90]!r} -> {href}')
        count += 1
        if count >= 20:
            break
print(f'  Total event-like links found: {count}')

print("\n=== LOOKING FOR EVENT CONTAINERS ===")
# Find divs that contain event dates like "7-8 November 2026"
for div in soup.find_all(['div', 'article', 'section']):
    txt = div.get_text(' ', strip=True)
    if re.search(r'\d{1,2}[–-]\d{1,2}\s+\w+\s+2026', txt) or re.search(r'\d{1,2}\s+\w+\s+2026', txt):
        if len(txt) < 500:
            cls = div.get('class', [])
            print(f'  TAG={div.name} CLASS={cls}')
            print(f'  TEXT={txt[:200]!r}')
            print()
