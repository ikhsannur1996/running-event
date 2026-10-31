#!/usr/bin/env python3
"""Debug HTML structure of lariku.info and indonesiamarathon.com"""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}


def debug_lariku():
    print("===== LARIKU.INFO =====")
    html = requests.get("https://lariku.info/", headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "lxml")

    # Find all links
    links = soup.find_all("a")
    print(f"Total links: {len(links)}")

    # Look for links containing event-like patterns
    count = 0
    for l in links:
        txt = l.get_text(" ", strip=True)
        href = l.get("href", "")
        if re.search(r"\d{1,2}\s+(Ags|Sep|Okt|Nov|Des|Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agustus|September|Oktober|November|Desember)", txt, re.IGNORECASE):
            count += 1
            if count <= 15:
                print(f"  TEXT: {txt[:110]}")
                print(f"  HREF: {href}")
                print()
    print(f"Event-like links found: {count}")

    # Look at text lines
    text = soup.get_text("\n", strip=True)
    lines = [l for l in text.split("\n") if l.strip()]
    print(f"\nTotal text lines: {len(lines)}")
    print("First 50 lines:")
    for i, l in enumerate(lines[:50]):
        print(f"  {i}: {l[:130]}")


def debug_indonesiamarathon():
    print("\n===== INDONESIAMARATHON.COM =====")
    html = requests.get("https://indonesiamarathon.com/", headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "lxml")

    # Find all links with "Lihat Detail Event" or "Selengkapnya"
    links = soup.find_all("a", string=re.compile("Lihat Detail Event|Selengkapnya", re.IGNORECASE))
    print(f"Detail links found: {len(links)}")
    for l in links[:10]:
        txt = l.get_text(" ", strip=True)
        href = l.get("href", "")
        print(f"  LINK TEXT: {txt}")
        print(f"  HREF: {href}")
        # Parent container text
        parent = l.parent
        ptext = clean(parent.get_text(" ", strip=True)) if parent else ""
        print(f"  PARENT TEXT: {ptext[:200]}")
        print()

    # Look at text lines containing dates
    text = soup.get_text("\n", strip=True)
    lines = [l for l in text.split("\n") if l.strip()]
    print(f"Total text lines: {len(lines)}")
    date_lines = [l for l in lines if re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", l)]
    print(f"Lines with dates: {len(date_lines)}")
    for l in date_lines[:20]:
        print(f"  {l[:160]}")


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


if __name__ == "__main__":
    debug_lariku()
    debug_indonesiamarathon()
