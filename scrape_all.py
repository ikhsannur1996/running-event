#!/usr/bin/env python3
"""
Comprehensive scraper for 13 Indonesian running event websites.
Extracts event data including fees, prizes, target participants, WA labels.
Filters: 2026 only. Deduplicates across sources.
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

AYOLARI_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "agu": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
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
        m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
        if m:
            day, month_name, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            month = INDONESIAN_MONTHS.get(month_name)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"
        m = re.match(r"(\d{1,2})\s+([A-Za-z]+)$", s)
        if m:
            day, month_name = int(m.group(1)), m.group(2).lower()
            month = INDONESIAN_MONTHS.get(month_name)
            if month:
                return f"2026-{month:02d}-{day:02d}"
        m = re.match(r"^\d{1,2}$", s)
        if m:
            return "DAY_ONLY"
        return None

    start = _parse_single(start_part)
    end = _parse_single(end_part) if end_part else start

    if start == "DAY_ONLY" and end and end != "DAY_ONLY":
        m = re.match(r"(\d{4})-(\d{2})-\d{2}", end)
        if m:
            year, month = m.group(1), m.group(2)
            start_day = int(start_part)
            start = f"{year}-{month}-{start_day:02d}"

    if isinstance(start, tuple):
        return start[0], start[1]
    return start, end


def is_2026(date_str: str) -> bool:
    if not date_str:
        return False
    return date_str.startswith("2026")


def extract_fee(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"(?:IDR|Rp\.?|Rp)\s*[\d.,]+(?:\s*(?:rb|ribu|juta|jt|k|K))?",
        r"[\d.,]+(?:\s*(?:rb|ribu|juta|jt|k|K))\s*(?:IDR|Rp\.?|Rp)?",
        r"Biaya[:\s]*([^\n|•]+)",
        r"Harga[:\s]*([^\n|•]+)",
        r"Gratis",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return clean_text(m.group(0))
    return ""


def extract_target_participants(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*(?:peserta|participant|orang|jiwa|calon)",
        r"target\s*(?:peserta|participant)[:\s]*(\d+(?:[.,]\d+)?)",
        r"kuota[:\s]*(\d+(?:[.,]\d+)?)",
        r"(\d+(?:[.,]\d+)?)\s*kuota",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return clean_text(m.group(0))
    return ""


def extract_prize(text: str) -> str:
    if not text:
        return ""
    for kw in ["hadiah", "prize", "benefit", "fasilitas peserta", "benefit peserta"]:
        m = re.search(rf"{kw}[:\s]*([^\n|•]{{0,200}})", text, re.IGNORECASE)
        if m:
            return clean_text(m.group(0))
    return ""


def extract_wa_label(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(?:World\s*Athletics\s*)?(?:Label\s*)?(?:WA\s*)?\s*(\d|Gold|Silver|Bronze|Platinum)\s*(?:Label)?", text, re.IGNORECASE)
    if m:
        return clean_text(m.group(0))
    if re.search(r"world\s*athletics", text, re.IGNORECASE):
        return "World Athletics"
    return ""


def completeness_score(event: dict) -> int:
    score = 0
    for field in ["event_name", "start_date", "end_date", "category", "location",
                  "registration_fee", "prize_benefits", "target_participants",
                  "organizer", "wa_label", "description"]:
        if event.get(field):
            score += 1
    return score


# ============================================================================
# 1. jadwallari.id
# ============================================================================

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
        if not is_2026(start_date or ""):
            continue

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

        dist_match = re.search(r"\d+(?:\.\d+)?\s*K", rest)
        distance = dist_match.group(0) if dist_match else ""

        title = rest
        if location:
            title = re.sub(re.escape(location) + r"\s*$", "", title, flags=re.IGNORECASE).strip()
        title = re.sub(r"^[\d,\s]+(?:K|M|HM|FM)\s*", "", title).strip()
        title = clean_text(title)

        events.append({
            "source": "jadwallari.id",
            "event_name": title or rest,
            "date_raw": date_part,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category": category,
            "distance": distance,
            "location": location,
            "registration_fee": "",
            "prize_benefits": "",
            "target_participants": "",
            "organizer": "",
            "wa_label": "",
            "description": rest,
            "url": url,
        })

    return events



# ============================================================================
# 2. ayolari.id
# ============================================================================

def scrape_ayolari_detail(detail_url: str) -> dict:
    """Scrape detail page for fee, prize, target, organizer, WA label."""
    extra = {
        "registration_fee": "",
        "prize_benefits": "",
        "target_participants": "",
        "organizer": "",
        "wa_label": "",
        "description": "",
    }
    try:
        html = fetch(detail_url)
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n", strip=True)

        # Organizer
        org_match = re.search(r"Penyelenggara[:\s]*([^\n]+)", text, re.IGNORECASE)
        if org_match:
            extra["organizer"] = clean_text(org_match.group(1))

        # Fee
        fee_match = re.search(r"Biaya[:\s]*([^\n]+)", text, re.IGNORECASE)
        if fee_match:
            extra["registration_fee"] = clean_text(fee_match.group(1))
        else:
            extra["registration_fee"] = extract_fee(text)

        # Prize/benefits
        prize_match = re.search(r"(?:Fasilitas|Benefit) Peserta[:\s]*([^\n]+)", text, re.IGNORECASE)
        if prize_match:
            extra["prize_benefits"] = clean_text(prize_match.group(1))
        else:
            extra["prize_benefits"] = extract_prize(text)

        # Target participants
        extra["target_participants"] = extract_target_participants(text)

        # WA Label
        extra["wa_label"] = extract_wa_label(text)

        # Description (first meaningful paragraph)
        desc_match = re.search(r"(?:Deskripsi|Detail Event|Tentang Event)[:\s]*([^\n]{20,500})", text, re.IGNORECASE)
        if desc_match:
            extra["description"] = clean_text(desc_match.group(1))
        else:
            # Use a chunk of text as description
            extra["description"] = clean_text(text[:500])

    except Exception as e:
        print(f"      [WARN] Detail scrape failed for {detail_url}: {e}")

    return extra


def scrape_ayolari() -> list[dict]:
    url = "https://ayolari.id/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    # Find event detail links
    event_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = a.get_text(" ", strip=True)
        if "/events/detail/" in href and txt and len(txt) > 5:
            event_links.append((txt, href))

    print(f"  [INFO] ayolari.id: {len(event_links)} event detail links found")

    for txt, href in event_links:
        full_url = urljoin(url, href)

        # Extract date from link text (format: "01 JAN 2026 Event Name Location Type | Distance")
        date_m = re.match(r"(\d{1,2})\s+(JAN|FEB|MAR|APR|MEI|JUN|JUL|AGU|SEP|OKT|NOV|DES)\s+(\d{4})\s+(.+)", txt, re.IGNORECASE)
        if not date_m:
            continue

        day = int(date_m.group(1))
        month_name = date_m.group(2).lower()
        year = int(date_m.group(3))
        rest = date_m.group(4).strip()

        month = AYOLARI_MONTHS.get(month_name)
        if not month:
            continue
        start_date = f"{year:04d}-{month:02d}-{day:02d}"

        if not is_2026(start_date):
            continue

        # Parse rest for event name, location, type, distance
        # Format: "Event Name Location Status Type | Distance"
        # e.g. "Metland Run for Fun Series 2026 Jakarta, Jawa Barat Selesai Fun | 5K"
        parts = rest.split("|")
        left_part = parts[0].strip() if parts else rest
        distance = parts[1].strip() if len(parts) > 1 else ""

        # Remove status words (Selesai, Coming Soon, etc.)
        left_part = re.sub(r"\b(Selesai|Coming Soon|Upcoming|Berlangsung)\b", "", left_part, flags=re.IGNORECASE).strip()

        # Extract location (city, province pattern at end)
        loc_match = re.search(r"(\w+(?:\s+\w+)?,\s*(?:Jawa|DKI|DI|Bali|Sumatera|Kalimantan|Sulawesi|NTB|Nusa|Papua|Aceh|Riau|Jambi|Lampung|Bengkulu|Gorontalo|Maluku|Kepulauan)[^\s]*)", left_part)
        location = loc_match.group(1) if loc_match else ""

        # Extract type (Fun, Road, Trail, Charity, Virtual)
        type_match = re.search(r"\b(Fun|Road|Trail|Charity|Virtual|Road Run|Trail Run|Fun Run|Charity Run|Virtual Run)\b", left_part, re.IGNORECASE)
        event_type = type_match.group(0) if type_match else ""

        # Event name = left_part minus location, type, status
        event_name = left_part
        if location:
            event_name = re.sub(re.escape(location) + r"\s*", "", event_name, flags=re.IGNORECASE).strip()
        if event_type:
            event_name = re.sub(re.escape(event_type) + r"\s*", "", event_name, flags=re.IGNORECASE).strip()
        event_name = clean_text(event_name)

        # Scrape detail page for fee, prize, etc.
        detail = scrape_ayolari_detail(full_url)

        events.append({
            "source": "ayolari.id",
            "event_name": event_name or txt,
            "date_raw": f"{day:02d} {month_name.upper()} {year}",
            "start_date": start_date,
            "end_date": start_date,
            "category": event_type,
            "distance": distance,
            "location": location,
            "registration_fee": detail["registration_fee"],
            "prize_benefits": detail["prize_benefits"],
            "target_participants": detail["target_participants"],
            "organizer": detail["organizer"],
            "wa_label": detail["wa_label"],
            "description": detail["description"] or rest,
            "url": full_url,
        })

        time.sleep(0.3)  # Be polite

    return events



# ============================================================================
# 3. kalenderlari.com
# ============================================================================

def scrape_kalenderlari() -> list[dict]:
    url = "https://kalenderlari.com/jadwal-event-lari-indonesia-2026/"
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
            if not is_2026(start_date or ""):
                continue

            events.append({
                "source": "kalenderlari.com",
                "event_name": name,
                "date_raw": date_raw,
                "start_date": start_date or "",
                "end_date": end_date or "",
                "category": category,
                "distance": "",
                "location": location,
                "registration_fee": "",
                "prize_benefits": "",
                "target_participants": "",
                "organizer": "",
                "wa_label": "",
                "description": f"{name} - {category} - {location}".strip(" -"),
                "url": url,
            })

    return events


# ============================================================================
# 4. lariku.info
# ============================================================================

def scrape_lariku() -> list[dict]:
    url = "https://lariku.info/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    text = soup.get_text("\n", strip=True)
    lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]

    current_year = ""

    i = 0
    while i < len(lines) - 4:
        line = lines[i]

        m_year = re.search(r"\b(2025|2026|2027)\b", line)
        if m_year and re.search(r"(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|Ags|September|Sep|Oktober|Okt|November|Nov|Desember|Des)", line, re.IGNORECASE):
            current_year = m_year.group(1)
            i += 1
            continue

        m_date = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,})$", lines[i + 1])
        if not m_date:
            i += 1
            continue

        name = lines[i]
        day = int(m_date.group(1))
        month_name = m_date.group(2).lower()
        month = INDONESIAN_MONTHS.get(month_name)
        year = int(current_year) if current_year else 2026
        date_str = f"{year:04d}-{month:02d}-{day:02d}" if month else ""

        if not is_2026(date_str):
            i += 5
            continue

        dist_cat = lines[i + 2]
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
            "distance": clean_text(distance),
            "location": clean_text(location),
            "registration_fee": "",
            "prize_benefits": "",
            "target_participants": "",
            "organizer": clean_text(organizer),
            "wa_label": "",
            "description": f"{clean_text(distance)} {clean_text(category)} - Organizer: {clean_text(organizer)}".strip(),
            "url": url,
        })

        i += 5

    return events



# ============================================================================
# 5. indonesiamarathon.com
# ============================================================================

def scrape_indonesiamarathon_category(category: str) -> list[dict]:
    """Scrape a category page from indonesiamarathon.com."""
    url = f"https://indonesiamarathon.com/event/kategori/{category}"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/event/") or href == "/event/":
            continue
        if "/kategori/" in href:
            continue

        txt = clean_text(a.get_text(" ", strip=True))
        if not txt or len(txt) < 10:
            continue

        date_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", txt)
        date_raw = date_m.group(1) if date_m else ""
        start_date, end_date = parse_id_date(date_raw) if date_raw else ("", "")

        if not is_2026(start_date or ""):
            continue

        # Extract event type
        cat_type = ""
        cat_match = re.search(
            r"\d{1,2}\s+[A-Za-z]+\s+\d{4}\s+([A-Za-z ,]+?)(?:\s+(?:Road Run|Trail Run|Fun Run|Virtual Run|Ultra|Marathon|Half Marathon|Charity Run|Ekiden|Vertical Run|Obstacle|Cross Country)|$)",
            txt, re.IGNORECASE,
        )
        if cat_match:
            cat_type = clean_text(cat_match.group(1))

        # Extract location
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
                after_date, re.IGNORECASE,
            )
            if loc_match:
                location = loc_match.group(0)

        # Title
        title = txt[:date_m.start()].strip() if date_m else txt
        title = re.sub(r"\s*[-–]\s*$", "", title).strip()
        title = clean_text(title)

        events.append({
            "source": "indonesiamarathon.com",
            "event_name": title,
            "date_raw": date_raw,
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category": cat_type,
            "distance": "",
            "location": location,
            "registration_fee": "",
            "prize_benefits": "",
            "target_participants": "",
            "organizer": "",
            "wa_label": "",
            "description": txt,
            "url": urljoin("https://indonesiamarathon.com", href),
        })

    return events


def scrape_indonesiamarathon() -> list[dict]:
    events = []
    # Homepage
    try:
        html = fetch("https://indonesiamarathon.com/")
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a"):
            atxt = clean_text(a.get_text(" ", strip=True))
            if "Lihat Detail Event" in atxt:
                href = a.get("href", "")
                txt = atxt
                date_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", txt)
                date_raw = date_m.group(1) if date_m else ""
                start_date, end_date = parse_id_date(date_raw) if date_raw else ("", "")
                if not is_2026(start_date or ""):
                    continue
                events.append({
                    "source": "indonesiamarathon.com",
                    "event_name": txt.replace("Lihat Detail Event", "").strip(),
                    "date_raw": date_raw,
                    "start_date": start_date or "",
                    "end_date": end_date or "",
                    "category": "",
                    "distance": "",
                    "location": "",
                    "registration_fee": "",
                    "prize_benefits": "",
                    "target_participants": "",
                    "organizer": "",
                    "wa_label": "",
                    "description": txt,
                    "url": urljoin("https://indonesiamarathon.com", href) if href else "https://indonesiamarathon.com/",
                })
    except Exception as e:
        print(f"  [ERROR] indonesiamarathon.com homepage: {e}")

    # Category pages
    for cat in ["fun-run", "road-run", "trail-run", "virtual-run"]:
        try:
            cat_events = scrape_indonesiamarathon_category(cat)
            print(f"  [INFO] indonesiamarathon.com/{cat}: {len(cat_events)} events")
            events.extend(cat_events)
        except Exception as e:
            print(f"  [ERROR] indonesiamarathon.com/{cat}: {e}")
        time.sleep(0.5)

    return events



# ============================================================================
# 6. kalenderlari.net
# ============================================================================

def scrape_kalenderlari_net() -> list[dict]:
    events = []
    base_url = "https://www.kalenderlari.net/"

    months_2026 = [
        "1-januari-2026", "1-februari-2026", "1-maret-2026", "1-april-2026",
        "1-mei-2026", "1-juni-2026", "1-juli-2026", "1-agustus-2026",
        "1-september-2026", "1-oktober-2026", "1-november-2026", "1-desember-2026",
    ]

    for month_path in months_2026:
        url = urljoin(base_url, month_path)
        try:
            html = fetch(url)
            soup = BeautifulSoup(html, "lxml")

            for a in soup.find_all("a", href=True):
                href = a["href"]
                txt = clean_text(a.get_text(" ", strip=True))
                if not href.startswith("/event/") or not txt or len(txt) < 5:
                    continue

                date_m = re.search(r"(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+(\d{4})", txt, re.IGNORECASE)
                if not date_m:
                    continue

                day = int(date_m.group(1))
                month_name = date_m.group(2).lower()
                year = int(date_m.group(3))
                month = INDONESIAN_MONTHS.get(month_name)
                if not month:
                    continue
                start_date = f"{year:04d}-{month:02d}-{day:02d}"

                if not is_2026(start_date):
                    continue

                type_match = re.search(r"\b(Road|Trail|Fun|Virtual|Charity|Marathon|Half|Ultra|Ekiden|Kids)\b", txt, re.IGNORECASE)
                event_type = type_match.group(0) if type_match else ""

                dist_match = re.search(r"\d+(?:\.\d+)?\s*K", txt)
                distance = dist_match.group(0) if dist_match else ""

                title = txt[:date_m.start()].strip()
                title = clean_text(title)

                events.append({
                    "source": "kalenderlari.net",
                    "event_name": title,
                    "date_raw": f"{day} {month_name} {year}",
                    "start_date": start_date,
                    "end_date": start_date,
                    "category": event_type,
                    "distance": distance,
                    "location": "",
                    "registration_fee": "",
                    "prize_benefits": "",
                    "target_participants": "",
                    "organizer": "",
                    "wa_label": "",
                    "description": txt,
                    "url": urljoin(base_url, href),
                })

        except Exception as e:
            print(f"  [ERROR] kalenderlari.net/{month_path}: {e}")
        time.sleep(0.3)

    return events



# ============================================================================
# 7. dorangadget.com
# ============================================================================

def scrape_dorangadget() -> list[dict]:
    url = "https://dorangadget.com/jadwal-event-lari-indonesia/"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    text = soup.get_text("\n", strip=True)
    lines = [clean_text(l) for l in text.split("\n") if clean_text(l)]

    date_line_re = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+(.+)$")

    for line in lines:
        m = date_line_re.match(line)
        if not m:
            continue

        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        rest = m.group(4).strip()

        month = INDONESIAN_MONTHS.get(month_name)
        if not month:
            continue
        start_date = f"{year:04d}-{month:02d}-{day:02d}"

        if not is_2026(start_date):
            continue

        loc_match = re.search(r"\b(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|"
                              r"Banyuwangi|Batam|Denpasar|Medan|Palembang|Makassar|Sleman|"
                              r"Bogor|Cilacap|Magelang|Solo|Surakarta|Tangerang|Depok|"
                              r"Lombok|Papua|Sumatera|Jawa Barat|Jawa Timur|Jawa Tengah|"
                              r"DKI Jakarta|DI Yogyakarta|Sumatera Selatan|Kalimantan|Sulawesi|"
                              r"NTB|Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Gowa|"
                              r"Kepulauan Riau|Kep\. Riau|Cianjur|Kulon Progo|Bondowoso|"
                              r"Pasuruan|Sleman)\b", rest, re.IGNORECASE)
        location = loc_match.group(0) if loc_match else ""

        cat_match = re.search(r"\b(Virtual Run|Fun Run|Trail Run|Road Run|Charity Run|Marathon|Half Marathon|Ultra|Ekiden|Kids Dash)\b", rest, re.IGNORECASE)
        category = cat_match.group(0) if cat_match else ""

        dist_match = re.search(r"\d+(?:\.\d+)?\s*K", rest)
        distance = dist_match.group(0) if dist_match else ""

        title = rest
        if location:
            title = re.sub(re.escape(location) + r"\s*$", "", title, flags=re.IGNORECASE).strip()
        title = clean_text(title)

        events.append({
            "source": "dorangadget.com",
            "event_name": title,
            "date_raw": f"{day} {month_name} {year}",
            "start_date": start_date,
            "end_date": start_date,
            "category": category,
            "distance": distance,
            "location": location,
            "registration_fee": "",
            "prize_benefits": "",
            "target_participants": "",
            "organizer": "",
            "wa_label": "",
            "description": rest,
            "url": url,
        })

    return events



# ============================================================================
# 8. ruanglari.com
# ============================================================================

def scrape_ruanglari() -> list[dict]:
    base_url = "https://ruanglari.com/jadwal-lari"
    events = []
    seen_urls = set()

    for page in range(1, 11):  # Up to 10 pages
        url = f"{base_url}?page={page}" if page > 1 else base_url
        try:
            html = fetch(url)
            soup = BeautifulSoup(html, "lxml")

            # Find event cards
            for tag in soup.find_all(["div", "article", "section", "a"]):
                txt = clean_text(tag.get_text(" ", strip=True))
                if not txt or len(txt) < 10:
                    continue
                if not re.search(r"\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}", txt):
                    continue
                if txt in seen_urls:
                    continue
                seen_urls.add(txt)

                date_m = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", txt)
                if not date_m:
                    continue

                day = int(date_m.group(1))
                month_name = date_m.group(2)
                year = int(date_m.group(3))

                EN_MONTHS = {
                    "january": 1, "february": 2, "march": 3, "april": 4,
                    "may": 5, "june": 6, "july": 7, "august": 8,
                    "september": 9, "october": 10, "november": 11, "december": 12,
                }
                month = EN_MONTHS.get(month_name.lower())
                if not month:
                    continue
                start_date = f"{year:04d}-{month:02d}-{day:02d}"

                if not is_2026(start_date):
                    continue

                # Extract type
                type_match = re.search(r"\b(Road|Trail|Fun|Virtual|Charity|Marathon|Half|Ultra|Ekiden|Kids|Run)\b", txt, re.IGNORECASE)
                event_type = type_match.group(0) if type_match else ""

                # Extract distance
                dist_match = re.search(r"\d+(?:\.\d+)?\s*K", txt)
                distance = dist_match.group(0) if dist_match else ""

                # Extract location
                loc_match = re.search(r"\b(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|Malang|Batam|Denpasar|Medan|Palembang|Makassar|Sleman|Bogor|Cilacap|Magelang|Solo|Surakarta|Tangerang|Depok|Lombok|Papua|Sumatera|Jawa Barat|Jawa Timur|Jawa Tengah|DKI Jakarta|DI Yogyakarta|Sumatera Selatan|Kalimantan|Sulawesi|NTB|Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Gowa)\b", txt, re.IGNORECASE)
                location = loc_match.group(0) if loc_match else ""

                title = txt
                if location:
                    title = re.sub(re.escape(location) + r"\s*$", "", title, flags=re.IGNORECASE).strip()
                title = re.sub(r"\d{1,2}\s+\w+\s+\d{4}", "", title).strip()
                title = clean_text(title)

                events.append({
                    "source": "ruanglari.com",
                    "event_name": title or txt,
                    "date_raw": f"{day} {month_name} {year}",
                    "start_date": start_date,
                    "end_date": start_date,
                    "category": event_type,
                    "distance": distance,
                    "location": location,
                    "registration_fee": "",
                    "prize_benefits": "",
                    "target_participants": "",
                    "organizer": "",
                    "wa_label": "",
                    "description": txt,
                    "url": url,
                })

            # Check if there's a next page
            next_link = soup.find("a", string=re.compile("Next|»|›", re.IGNORECASE))
            if not next_link:
                break

        except Exception as e:
            print(f"  [ERROR] ruanglari.com page {page}: {e}")
            break
        time.sleep(0.5)

    return events



# ============================================================================
# 9. koncolari.com
# ============================================================================

def scrape_koncolari() -> list[dict]:
    url = "https://koncolari.com/event"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    events = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = clean_text(a.get_text(" ", strip=True))
        if not href.startswith("/event/") or href == "/event/":
            continue
        if not txt or len(txt) < 3:
            continue

        date_m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", txt)
        if not date_m:
            continue

        day = int(date_m.group(1))
        month_name = date_m.group(2).lower()
        year = int(date_m.group(3))
        month = INDONESIAN_MONTHS.get(month_name)
        if not month:
            continue
        start_date = f"{year:04d}-{month:02d}-{day:02d}"

        if not is_2026(start_date):
            continue

        rest = txt
        # Extract location
        loc_match = re.search(r"\b(Jakarta|Bandung|Surabaya|Bali|Yogyakarta|Semarang|Bekasi|Malang|Batam|Denpasar|Medan|Palembang|Makassar|Sleman|Bogor|Cilacap|Magelang|Solo|Surakarta|Tangerang|Depok|Lombok|Papua|Sumatera|Jawa Barat|Jawa Timur|Jawa Tengah|DKI Jakarta|DI Yogyakarta|Sumatera Selatan|Kalimantan|Sulawesi|NTB|Banten|Aceh|Riau|Jambi|Lampung|Bengkulu|Gowa)\b", rest, re.IGNORECASE)
        location = loc_match.group(0) if loc_match else ""

        cat_match = re.search(r"\b(Virtual Run|Fun Run|Trail Run|Road Run|Charity Run|Marathon|Half Marathon|Ultra|Ekiden|Kids Dash)\b", rest, re.IGNORECASE)
        category = cat_match.group(0) if cat_match else ""

        dist_match = re.search(r"\d+(?:\.\d+)?\s*K", rest)
        distance = dist_match.group(0) if dist_match else ""

        title = txt[:date_m.start()].strip() if date_m else txt
        title = clean_text(title)

        events.append({
            "source": "koncolari.com",
            "event_name": title,
            "date_raw": f"{day} {month_name} {year}",
            "start_date": start_date,
            "end_date": start_date,
            "category": category,
            "distance": distance,
            "location": location,
            "registration_fee": "",
            "prize_benefits": "",
            "target_participants": "",
            "organizer": "",
            "wa_label": "",
            "description": txt,
            "url": urljoin(url, href),
        })

    return events



# ============================================================================
# 10. tias.co.id (JS-rendered calendar)
# ============================================================================

def scrape_tias() -> list[dict]:
    events = []
    try:
        html = fetch("https://tias.co.id/kalender-lari")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["div", "section", "article"]):
            txt = clean_text(tag.get_text(" ", strip=True))
            if not txt or len(txt) < 10:
                continue
            date_m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", txt)
            if not date_m:
                continue
            year = int(date_m.group(3))
            if year != 2026:
                continue
            events.append({
                "source": "tias.co.id",
                "event_name": txt[:100],
                "date_raw": date_m.group(0),
                "start_date": "",
                "end_date": "",
                "category": "",
                "distance": "",
                "location": "",
                "registration_fee": "",
                "prize_benefits": "",
                "target_participants": "",
                "organizer": "",
                "wa_label": "",
                "description": txt,
                "url": "https://tias.co.id/kalender-lari",
            })
    except Exception as e:
        print(f"  [ERROR] tias.co.id: {e}")
    return events



# ============================================================================
# 11. eventlari.com (JS-rendered)
# ============================================================================

def scrape_eventlari() -> list[dict]:
    events = []
    try:
        html = fetch("http://eventlari.com/")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["div", "section", "article", "tr"]):
            txt = clean_text(tag.get_text(" ", strip=True))
            if not txt or len(txt) < 10:
                continue
            date_m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", txt)
            if not date_m:
                continue
            year = int(date_m.group(3))
            if year != 2026:
                continue
            events.append({
                "source": "eventlari.com",
                "event_name": txt[:100],
                "date_raw": date_m.group(0),
                "start_date": "",
                "end_date": "",
                "category": "",
                "distance": "",
                "location": "",
                "registration_fee": "",
                "prize_benefits": "",
                "target_participants": "",
                "organizer": "",
                "wa_label": "",
                "description": txt,
                "url": "http://eventlari.com/",
            })
    except Exception as e:
        print(f"  [ERROR] eventlari.com: {e}")
    return events


# ============================================================================
# 12. schedules.run (JS-rendered)
# ============================================================================

def scrape_schedules_run() -> list[dict]:
    events = []
    try:
        html = fetch("https://schedules.run/")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(["div", "section", "article"]):
            txt = clean_text(tag.get_text(" ", strip=True))
            if not txt or len(txt) < 10:
                continue
            date_m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", txt)
            if not date_m:
                continue
            year = int(date_m.group(3))
            if year != 2026:
                continue
            events.append({
                "source": "schedules.run",
                "event_name": txt[:100],
                "date_raw": date_m.group(0),
                "start_date": "",
                "end_date": "",
                "category": "",
                "distance": "",
                "location": "",
                "registration_fee": "",
                "prize_benefits": "",
                "target_participants": "",
                "organizer": "",
                "wa_label": "",
                "description": txt,
                "url": "https://schedules.run/",
            })
    except Exception as e:
        print(f"  [ERROR] schedules.run: {e}")
    return events



# ============================================================================
# Main with deduplication
# ============================================================================

def normalize_name(name: str) -> str:
    n = str(name).lower()
    n = re.sub(r"\s*(virtual run|fun run|trail run|road run|charity run|marathon|half marathon|ultra|ekiden|fun walk|kids dash|vertical run|obstacle|cross country|mountain run|sky race|funwalk)\s*$", "", n)
    n = re.sub(r"2026\s*$", "", n)
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def main():
    all_events = []

    scrapers = [
        ("jadwallari.id", scrape_jadwallari),
        ("ayolari.id", scrape_ayolari),
        ("kalenderlari.com", scrape_kalenderlari),
        ("lariku.info", scrape_lariku),
        ("indonesiamarathon.com", scrape_indonesiamarathon),
        ("kalenderlari.net", scrape_kalenderlari_net),
        ("dorangadget.com", scrape_dorangadget),
        ("ruanglari.com", scrape_ruanglari),
        ("koncolari.com", scrape_koncolari),
        ("tias.co.id", scrape_tias),
        ("eventlari.com", scrape_eventlari),
        ("schedules.run", scrape_schedules_run),
    ]

    for name, scraper in scrapers:
        print(f"[INFO] Scraping {name} ...")
        try:
            events = scraper()
            print(f"[INFO] {name}: {len(events)} events found (2026)")
            all_events.extend(events)
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
        time.sleep(1)

    # Deduplicate: normalize name + start_date, keep most complete
    seen = {}
    for e in all_events:
        key = (e["source"], normalize_name(e["event_name"]), e["start_date"])
        if key not in seen:
            seen[key] = e
        else:
            if completeness_score(e) > completeness_score(seen[key]):
                seen[key] = e

    unique = list(seen.values())
    unique.sort(key=lambda x: (x["start_date"], x["source"], x["event_name"]))

    csv_path = "/Users/ikhsannur1996/Documents/Running Event/events_all_2026.csv"
    json_path = "/Users/ikhsannur1996/Documents/Running Event/events_all_2026.json"

    fieldnames = ["source", "event_name", "date_raw", "start_date", "end_date",
                  "category", "distance", "location", "registration_fee",
                  "prize_benefits", "target_participants", "organizer",
                  "wa_label", "description", "url"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] Total unique events (2026): {len(unique)}")
    print(f"[INFO] CSV saved to: {csv_path}")
    print(f"[INFO] JSON saved to: {json_path}")

    df = pd.DataFrame(unique)
    print("\n[INFO] Breakdown by source:")
    print(df.groupby("source").size())

    print("\n[INFO] Events with registration fee:", df["registration_fee"].ne("").sum())
    print("[INFO] Events with prize/benefits:", df["prize_benefits"].ne("").sum())
    print("[INFO] Events with target participants:", df["target_participants"].ne("").sum())
    print("[INFO] Events with organizer:", df["organizer"].ne("").sum())
    print("[INFO] Events with WA label:", df["wa_label"].ne("").sum())


if __name__ == "__main__":
    main()

