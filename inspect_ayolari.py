#!/usr/bin/env python3
"""Inspect ayolari.id structure"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

html = requests.get('https://ayolari.id/', headers=HEADERS, timeout=30).text
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
    if '/event/' in href and txt and len(txt) > 3:
        print(f'  {txt[:90]!r} -> {href}')
        count += 1
        if count >= 15:
            break
print(f'  Total event links found (showing first 15)')

print("\n=== EVENT CONTAINER CLASSES ===")
# Look for repeating event card structures
for div in soup.find_all(['div', 'article']):
    txt = div.get_text(' ', strip=True)
    if re.search(r'\d{1,2}\s+(JAN|FEB|MAR|APR|MEI|JUN|JUL|AGU|SEP|OKT|NOV|DES)', txt):
        cls = div.get('class', [])
        if len(txt) < 300:
            print(f'  TAG={div.name} CLASS={cls}')
            print(f'  TEXT={txt[:200]!r}')
            print()

# Look for script tags with API endpoints or data
print("\n=== SCRIPT TAGS / API ENDPOINTS ===")
for script in soup.find_all('script', src=True):
    src = script['src']
    if 'api' in src.lower() or 'event' in src.lower():
        print(f'  SRC={src}')

# Check for inline data
for script in soup.find_all('script'):
    content = script.string or script.get_text()
    if content and ('event' in content.lower() or 'api' in content.lower()):
        if len(content) < 2000:
            print(f'  INLINE SCRIPT: {content[:500]!r}')
