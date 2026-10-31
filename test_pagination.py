#!/usr/bin/env python3
"""Check pagination on indonesiamarathon.com category pages - compare content"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}


def get_event_slugs(page):
    url = f'https://indonesiamarathon.com/event/kategori/road-run?page={page}'
    html = requests.get(url, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, 'lxml')
    slugs = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/event/') and '/kategori/' not in href and href != '/event/':
            slug = href.replace('/event/', '')
            if slug not in slugs:
                slugs.append(slug)
    return slugs, soup.get_text(' ', strip=True)


slugs1, text1 = get_event_slugs(1)
slugs2, text2 = get_event_slugs(2)
slugs3, text3 = get_event_slugs(3)

print(f'Page 1: {len(slugs1)} unique event slugs')
print(f'Page 2: {len(slugs2)} unique event slugs')
print(f'Page 3: {len(slugs3)} unique event slugs')

overlap_12 = set(slugs1) & set(slugs2)
overlap_13 = set(slugs1) & set(slugs3)
overlap_23 = set(slugs2) & set(slugs3)

print(f'\nOverlap 1-2: {len(overlap_12)}')
print(f'Overlap 1-3: {len(overlap_13)}')
print(f'Overlap 2-3: {len(overlap_23)}')

print(f'\nPage 1 slugs: {slugs1[:10]}')
print(f'Page 2 slugs: {slugs2[:10]}')

print(f'\nPage 1 == Page 2: {text1 == text2}')
print(f'Page 1 == Page 3: {text1 == text3}')

print(f'\nPage 1 length: {len(text1)}')
print(f'Page 2 length: {len(text2)}')

