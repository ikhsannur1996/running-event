#!/usr/bin/env python3
"""Debug indonesiamarathon.com HTML structure around events"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

html = requests.get("https://indonesiamarathon.com/", headers=HEADERS, timeout=30).text
soup = BeautifulSoup(html, "lxml")

# Find all <a> tags and look at their text
links = soup.find_all("a")
print(f"Total <a> tags: {len(links)}")
for l in links:
    txt = l.get_text(" ", strip=True)
    href = l.get("href", "")
    if "Detail" in txt or "Selengkapnya" in txt or "Event" in txt:
        print(f"  TEXT: '{txt}' | HREF: {href}")

print("\n--- Looking for event cards/containers ---")
# Look for divs containing both a date and "Lihat Detail"
for div in soup.find_all(["div", "article", "section", "li"]):
    txt = div.get_text(" ", strip=True)
    if "Lihat Detail Event" in txt and re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", txt):
        print(f"  TAG: {div.name} CLASS: {div.get('class')}")
        print(f"  TEXT: {txt[:250]}")
        print(f"  ID: {div.get('id')}")
        print()

print("\n--- Looking for all 'Lihat Detail' occurrences in raw HTML ---")
count = html.count("Lihat Detail Event")
print(f"'Lihat Detail Event' count: {count}")
count2 = html.count("Selengkapnya")
print(f"'Selengkapnya' count: {count2}")

# Find the context around first occurrence
idx = html.find("Lihat Detail Event")
if idx >= 0:
    snippet = html[max(0, idx-500):idx+500]
    print(f"\n--- Context around first 'Lihat Detail Event' ---")
    print(snippet[:1000])
