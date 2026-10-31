#!/usr/bin/env python3
"""Inspect detail pages for fee/prize/target info"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

# Check ayolari.id detail page
print("=" * 70)
print("AYOLARI.ID DETAIL PAGE")
print("=" * 70)
html = requests.get('https://ayolari.id/events/detail/metland-run-for-fun-series-2026/', headers=HEADERS, timeout=30).text
soup = BeautifulSoup(html, 'lxml')
text = soup.get_text('\n', strip=True)
print(f"Size: {len(html)} bytes")
print(f"\nText content (first 3000 chars):\n{text[:3000]}")

# Look for fee, prize, target keywords
for kw in ['biaya', 'fee', 'pendaftaran', 'hadiah', 'prize', 'peserta', 'participant', 'world athlet', 'WA ', 'label', 'target', 'quota', 'kuota']:
    matches = re.findall(r'.{0,80}' + re.escape(kw) + r'.{0,80}', text, re.IGNORECASE)
    if matches:
        print(f"\n--- Keyword: {kw} ---")
        for m in matches[:3]:
            print(f'  {m.strip()}')
