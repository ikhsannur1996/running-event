#!/usr/bin/env python3
"""
Scraper for running events from 4 Indonesian websites:
1. https://jadwallari.id/events/
2. https://kalenderlari.com/jadwal/
3. https://lariku.info/
4. https://indonesiamarathon.com/

Output: events_all.csv and events_all.json
"""

import re
import csv
import json
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

INDONESIAN_MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
    "ags": 8,
}


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_id_date(date_str: str):
    if not date_str:
        return None, None
    date_str = clean_text(date_str)
    parts = re.split(r"\s*[-–—]\s*", date_str)
    start_part = parts[0].strip()
    end_part = parts[1].strip() if len(parts) > 1 else None

    def _parse_single(s: str):
        s = clean_text(s)
        # Full date: DD Month YYYY
        m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
        if m:
            day, month_name, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            month = INDONESIAN_MONTHS.get(month_name)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"
        # Day + Month only (no year) -> default to 2026
        m = re.match(r"(\d{1,2})\s+([A-Za-z]+)$", s)
        if m:
            day, month_name = int(m.group(1)), m.group(2).lower()
            month = INDONESIAN_MONTHS.get(month_name)
            if month:
                return f"2026-{month:02d}-{day:02d}"
        # Just a day number (shared month/year from end part)
        m = re.match(r"^\d{1,2}$", s)
        if m:
            return "DAY_ONLY"
        return None

    start = _parse_single(start_part)
    end = _parse_single(end_part) if end_part else start

    # Handle "DAY_ONLY" start - borrow month/year from end date
    if start == "DAY_ONLY" and end and end != "DAY_ONLY":
        m = re.match(r"(\d{4})-(\d{2})-\d{2}", end)
        if m:
            year, month = m.group(1), m.group(2)
            start_day = int(start_part)
            start = f"{year}-{month}-{start_day:02d}"

    if isinstance(start, tuple):
        return start[0], start[1]
    return start, end


# ---------------------------------------------------------------------------
# 2. kalenderlari.com
# ---------------------------------------------------------------------------

def scrape_kalenderlari() -> list[dict]:
    url = "https://kalenderlari.com/jadwal/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = [clean_text(c.get_text(" ", strip=True)) for c in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            if not re.search(r"\d", cells[0]):
                continue
            date_raw = cells[0]
            name = cells[1] if len(cells) > 1 else ""
            category = cells[2] if len(cells) > 2 else ""
            location = cells[3] if len(cells) > 3 else ""

            start_date, end_date = parse_id_date(date_raw)

            events.append({
                "source": "kalenderlari.com",
                "event_name": name,
                "date_raw": date_raw,
                "start_date": start_date or "",
                "end_date": end_date or "",
                "category": category,
                "location": location,
                "description": f"{name} - {category} - {location}".strip(" -"),
                "url": url,
            })

    if not events:
        text = soup.get_text("\n", strip=True)
        lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]
        for line in lines:
            if re.match(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", line):
                start_date, end_date = parse_id_date(line)
                events.append({
                    "source": "kalenderlari.com",
                    "event_name": "",
                    "date_raw": line,
                    "start_date": start_date or "",
                    "end_date": end_date or "",
                    "category": "",
                    "location": "",
                    "description": line,
                    "url": url,
                })

    return events



# ---------------------------------------------------------------------------
# 3. lariku.info
# ---------------------------------------------------------------------------

def scrape_lariku() -> list[dict]:
    url = "https://lariku.info/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    text = soup.get_text("\n", strip=True)
    lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]

    current_year = ""

    # lariku.info format: 5 lines per event
    #   name
    #   DD Mon          (date)
    #   emoji Distance • Category
    #   location
    #   organizer
    i = 0
    while i < len(lines) - 4:
        line = lines[i]

        # Detect year header line like "Name 2026 Category Agustus Location Organizer"
        m_year = re.search(r"\b(2025|2026|2027)\b", line)
        if m_year and re.search(r"(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|Ags|September|Sep|Oktober|Okt|November|Nov|Desember|Des)", line, re.IGNORECASE):
            current_year = m_year.group(1)
            i += 1
            continue

        # Check if line i+1 is a date like "02 Ags"
        m_date = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,})$", lines[i + 1])
        if not m_date:
            i += 1
            continue

        name = lines[i]
        day = int(m_date.group(1))
        month_name = m_date.group(2).lower()
        month = INDONESIAN_MONTHS.get(month_name)
        year = int(current_year) if current_year else datetime.now().year
        date_str = f"{year:04d}-{month:02d}-{day:02d}" if month else ""

        # Line i+2: "emoji Distance • Category"
        dist_cat = lines[i + 2]
        # Strip leading emoji
        dist_cat_clean = re.sub(r"^[\u2600-\u27BF\u2300-\u23FF\U0001F000-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\uFE00-\uFE0F]\s*", "", dist_cat)
        if " • " in dist_cat_clean:
            distance, category = dist_cat_clean.split(" • ", 1)
        else:
            distance, category = dist_cat_clean, ""

        location = lines[i + 3]
        organizer = lines[i + 4]

        events.append({
            "source": "lariku.info",
            "event_name": name,
            "date_raw": f"{day} {month_name} {year}",
            "start_date": date_str,
            "end_date": date_str,
            "category": clean_text(category),
            "location": clean_text(location),
            "description": f"{clean_text(distance)} {clean_text(category)} - Organizer: {clean_text(organizer)}".strip(),
            "url": url,
        })

        i += 5

    return events



# ---------------------------------------------------------------------------
# 4. indonesiamarathon.com
# ---------------------------------------------------------------------------

def scrape_indonesiamarathon() -> list[dict]:
    url = "https://indonesiamarathon.com/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    # Find <a> tags whose visible text contains "Lihat Detail Event"
    # (text may be inside a nested <span>, so use get_text())
    detail_links = []
    for a in soup.find_all("a"):
        atxt = clean_text(a.get_text(" ", strip=True))
        if "Lihat Detail Event" in atxt:
            detail_links.append(a)

    for link in detail_links:
        # Walk up to find container with date + event type
        container = link
        txt = ""
        for _ in range(8):
            if container.parent is None:
                break
            container = container.parent
            txt = clean_text(container.get_text(" ", strip=True))
            if re.search(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", txt):
                break

        # Remove "Lihat Detail Event" / "Selengkapnya" bits
        txt = re.sub(r"\s*Lihat Detail Event\s*", " ", txt)
        txt = re.sub(r"\s*Selengkapnya\s*", " ", txt)
        txt = clean_text(txt)

        # Extract event type prefix
        m = re.match(r"(Road Run|Trail Run|Fun Run|Virtual Run|Ultra Marathon|Half Marathon|Marathon|Charity Run|Ekiden|Vertical Run|Obstacle|Cross Country)\s+(.+)", txt, re.IGNORECASE)
        if m:
            event_type = m.group(1)
            rest = m.group(2)
        else:
            event_type = ""
            rest = txt

        date_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", rest)
        date_raw = date_m.group(1) if date_m else ""
        start_date, end_date = parse_id_date(date_raw) if date_raw else ("", "")

        location = ""
        if date_m:
            after_date = rest[date_m.end():].strip()
            loc_match = re.search(r"(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|Banyuwangi|Batam|Denpasar|Medan|Palembang|Makassar|Sleman|Bogor|Cilacap|Magelang|Solo|Surakarta|Tangerang|Depok|Lombok|Papua|Sumatera|Jawa Barat|Jawa Timur|Jawa Tengah|DKI Jakarta|DI Yogyakarta|Sumatera Selatan|Kalimantan|Sulawesi|NTB|Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Gowa|Kepulauan Riau|Sleman, DI Yogyakarta|Ternate, Maluku Utara|Singkawang, Kalimantan Barat|Depok, Jawa Barat|Tangerang, Banten)$", after_date, re.IGNORECASE)
            if loc_match:
                location = loc_match.group(0)

        title = rest
        title = re.sub(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", "", title).strip()
        title = re.sub(r"(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|Banyuwangi|Batam|Denpasar|Medan|Palembang|Makassar|Sleman|Bogor|Cilacap|Magelang|Solo|Surakarta|Tangerang|Depok|Lombok|Papua|Sumatera|Jawa Barat|Jawa Timur|Jawa Tengah|DKI Jakarta|DI Yogyakarta|Sumatera Selatan|Kalimantan|Sulawesi|NTB|Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Gowa|Kepulauan Riau|Sleman, DI Yogyakarta|Ternate, Maluku Utara|Singkawang, Kalimantan Barat|Depok, Jawa Barat|Tangerang, Banten)$", "", title, flags=re.IGNORECASE).strip()
        title = clean_text(title)

        href = link.get("href", "")

        events.append({
            "source": "indonesiamarathon.com",
            "event_name": title,
            "date_raw": date_raw,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category": event_type,
            "location": location,
            "description": txt,
            "url": urljoin(url, href) if href else url,
        })

    # Fallback: parse text blocks containing date patterns
    if not events:
        text = soup.get_text("\n", strip=True)
        lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]
        for line in lines:
            if re.search(r"(Road Run|Trail Run|Fun Run|Virtual Run)\s+.+\d{1,2}\s+[A-Za-z]+\s+\d{4}", line):
                m = re.match(r"(Road Run|Trail Run|Fun Run|Virtual Run)\s+(.+)", line, re.IGNORECASE)
                event_type = m.group(1) if m else ""
                rest = m.group(2) if m else line
                date_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", rest)
                date_raw = date_m.group(1) if date_m else ""
                sd, ed = parse_id_date(date_raw) if date_raw else ("", "")
                events.append({
                    "source": "indonesiamarathon.com",
                    "event_name": "",
                    "date_raw": date_raw,
                    "start_date": sd or "",
                    "end_date": ed or "",
                    "category": event_type,
                    "location": "",
                    "description": line,
                    "url": url,
                })

    return events



# ---------------------------------------------------------------------------
# 1. jadwallari.id
# ---------------------------------------------------------------------------

def scrape_jadwallari() -> list[dict]:
    url = "https://jadwallari.id/events/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    candidates = soup.find_all(["div", "li", "tr", "article", "section"])
    seen = set()

    for tag in candidates:
        txt = clean_text(tag.get_text(" ", strip=True))
        if not txt or len(txt) < 10:
            continue
        if not re.match(r"\d{1,2}\s+[A-Za-z]+\s+\d{4}", txt):
            continue
        if txt in seen:
            continue
        seen.add(txt)

        # Multi-pattern date extraction for jadwallari.id
        date_patterns = [
            (r'^(\d{1,2}\s+[A-Za-z]+\s+\d{4}\s*[-–—]\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'full_range'),
            (r'^(\d{1,2}\s+[A-Za-z]+\s*[-–—]\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'start_no_year'),
            (r'^(\d{1,2}\s*[-–]\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'shared_month'),
            (r'^(\d{1,2}[-–]\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'connected_days'),
            (r'^(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'single_date'),
        ]
        date_part = None
        rest = None
        for dp, _ in date_patterns:
            m = re.match(dp, txt)
            if m:
                date_part = m.group(1).strip()
                rest = m.group(2).strip()
                break
        if date_part is None:
            continue

        start_date, end_date = parse_id_date(date_part)

        loc_match = re.search(r"\b(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|"
                              r"Banyuwangi|Batam|Denpasar|Medan|Palembang|Makassar|"
                              r"Anywhere|Sleman|Bogor|Cilacap|Magelang|Solo|Surakarta|"
                              r"Tangerang|Depok|Lombok|Papua|Sumatera|"
                              r"Jawa Barat|Jawa Timur|Jawa Tengah|DKI Jakarta|DI Yogyakarta|"
                              r"Sumatera Selatan|Sumatera Utara|Kalimantan|Sulawesi|NTB|Nusa Tenggara|"
                              r"Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Bangka Belitung|"
                              r"Gorontalo|Maluku|Papua Barat|Kalimantan Barat|Kalimantan Selatan|"
                              r"Kalimantan Tengah|Kalimantan Timur|Kalimantan Utara|Sulawesi Barat|"
                              r"Sulawesi Selatan|Sulawesi Tengah|Sulawesi Tenggara|Sulawesi Utara|"
                              r"Papua Barat Daya|Gowa|Kepulauan Riau|Kep\. Riau)\b",
                              rest, re.IGNORECASE)
        location = loc_match.group(0) if loc_match else ""

        cat_match = re.search(r"\b(Virtual Run|Fun Run|Trail Run|Road Run|Charity Run|"
                              r"Marathon|Half Marathon|Ultra|Ekiden|Fun Walk|Kids Dash|"
                              r"Vertical Run|Obstacle|Cross Country|Mountain Run|Sky Race)\b",
                              rest, re.IGNORECASE)
        category = cat_match.group(0) if cat_match else ""

        title = rest
        # Strip trailing location from title
        if location:
            title = re.sub(re.escape(location) + r"\s*$", "", title, flags=re.IGNORECASE).strip()
        # Remove leading distance numbers (e.g. "30K ", "5K, 10K ")
        title = re.sub(r"^[\d,\s]+(?:K|M|HM|FM)\s*", "", title).strip()
        title = clean_text(title)

        events.append({
            "source": "jadwallari.id",
            "event_name": title or rest,
            "date_raw": date_part,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category": category,
            "location": location,
            "description": rest,
            "url": url,
        })

    return events


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _norm_name(name: str) -> str:
    """Normalize event name for deduplication."""
    n = str(name).lower()
    n = re.sub(
        r"\s*(virtual run|fun run|trail run|road run|charity run|marathon|half marathon|"
        r"ultra|ekiden|fun walk|kids dash|vertical run|obstacle|cross country|mountain run|"
        r"sky race|funwalk)\s*$", "", n
    )
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def scrape_indonesiamarathon_category(category: str) -> list[dict]:
    """Scrape a category page from indonesiamarathon.com."""
    url = f"https://indonesiamarathon.com/event/kategori/{category}"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    # Find event cards - links to /event/ slugs
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/event/") or href == "/event/":
            continue
        if "/kategori/" in href:
            continue

        txt = clean_text(a.get_text(" ", strip=True))
        if not txt or len(txt) < 10:
            continue

        # Pattern: "Event Name Date Location Type, distances"
        # e.g. "Horison Kotaraja Fun Run 2026 - Kota Jayapura 1 Oktober 2026 Jayapura, Papua Fun Run, 5K, 10K"
        # Extract date
        date_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", txt)
        date_raw = date_m.group(1) if date_m else ""
        start_date, end_date = parse_id_date(date_raw) if date_raw else ("", "")

        # Extract category/type (after date, before description)
        category_type = ""
        cat_match = re.search(
            r"\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+([A-Za-z ,]+?)(?:\s+(?:Road Run|Trail Run|Fun Run|Virtual Run|Ultra|Marathon|Half Marathon|Charity Run|Ekiden|Vertical Run|Obstacle|Cross Country)|$)",
            txt,
            re.IGNORECASE,
        )
        if cat_match:
            category_type = clean_text(cat_match.group(1))

        # Extract location (after date)
        location = ""
        if date_m:
            after_date = txt[date_m.end():].strip()
            loc_match = re.search(
                r"(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|Banyuwangi|Batam|"
                r"Denpasar|Medan|Palembang|Makassar|Sleman|Bogor|Cilacap|Magelang|Solo|"
                r"Surakarta|Tangerang|Depok|Lombok|Papua|Sumatera|Jawa Barat|Jawa Timur|"
                r"Jawa Tengah|DKI Jakarta|DI Yogyakarta|Sumatera Selatan|Kalimantan|Sulawesi|"
                r"NTB|Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Gowa|Kepulauan Riau|"
                r"Sleman, DI Yogyakarta|Ternate, Maluku Utara|Singkawang, Kalimantan Barat|"
                r"Depok, Jawa Barat|Tangerang, Banten|Jayapura, Papua|Tanjung Pinang, Kepulauan Riau)"
                r"\b",
                after_date,
                re.IGNORECASE,
            )
            if loc_match:
                location = loc_match.group(0)

        # Title = text before date
        title = txt[: date_m.start()].strip() if date_m else txt
        title = re.sub(r"\s*[-–]\s*$", "", title).strip()
        title = clean_text(title)

        events.append({
            "source": "indonesiamarathon.com",
            "event_name": title,
            "date_raw": date_raw,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category": category_type,
            "location": location,
            "description": txt,
            "url": urljoin("https://indonesiamarathon.com", href),
        })

    return events


def main():
    all_events = []

    scrapers = [
        ("jadwallari.id", scrape_jadwallari),
        ("kalenderlari.com", scrape_kalenderlari),
        ("lariku.info", scrape_lariku),
        ("indonesiamarathon.com", scrape_indonesiamarathon),
    ]

    for name, scraper in scrapers:
        print(f"[INFO] Scraping {name} ...")
        try:
            events = scraper()
            print(f"[INFO] {name}: {len(events)} events found")
            all_events.extend(events)
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
        time.sleep(1)

    # Also scrape indonesiamarathon.com category pages
    for cat in ["fun-run", "road-run", "trail-run", "virtual-run"]:
        print(f"[INFO] Scraping indonesiamarathon.com category: {cat} ...")
        try:
            events = scrape_indonesiamarathon_category(cat)
            print(f"[INFO] indonesiamarathon.com/{cat}: {len(events)} events found")
            all_events.extend(events)
        except Exception as e:
            print(f"[ERROR] indonesiamarathon.com/{cat}: {e}")
        time.sleep(1)

    # Deduplicate using normalized name + start_date
    seen = set()
    unique = []
    for e in all_events:
        key = (e["source"], _norm_name(e["event_name"]), e["start_date"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    unique.sort(key=lambda x: (x["start_date"], x["source"], x["event_name"]))

    csv_path = "/Users/ikhsannur1996/Documents/Running Event/events_all.csv"
    json_path = "/Users/ikhsannur1996/Documents/Running Event/events_all.json"

    fieldnames = ["source", "event_name", "date_raw", "start_date", "end_date",
                  "category", "location", "description", "url"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] Total unique events: {len(unique)}")
    print(f"[INFO] CSV saved to: {csv_path}")
    print(f"[INFO] JSON saved to: {json_path}")

    df = pd.DataFrame(unique)
    print("\n[INFO] Breakdown by source:")
    print(df.groupby("source").size())


if __name__ == "__main__":
    main()

