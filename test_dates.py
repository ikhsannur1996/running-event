#!/usr/bin/env python3
"""Test date parsing with actual strings from the scraped data"""
import csv
import re

INDONESIAN_MONTHS = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'agt': 8, 'sep': 9,
    'okt': 10, 'nov': 11, 'des': 12, 'ags': 8,
}

def parse_id_date(date_str):
    if not date_str:
        return None, None
    date_str = re.sub(r'\s+', ' ', date_str or '').strip()
    parts = re.split(r'\s*[-–—]\s*', date_str)
    start_part = parts[0].strip()
    end_part = parts[1].strip() if len(parts) > 1 else None

    def _parse_single(s):
        s = re.sub(r'\s+', ' ', s or '').strip()
        # Full date: DD Month YYYY
        m = re.match(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', s)
        if m:
            day, month_name, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
            month = INDONESIAN_MONTHS.get(month_name)
            if month:
                return f'{year:04d}-{month:02d}-{day:02d}'
        # Just day + month (no year) - use context
        m = re.match(r'(\d{1,2})\s+([A-Za-z]+)$', s)
        if m:
            day, month_name = int(m.group(1)), m.group(2).lower()
            month = INDONESIAN_MONTHS.get(month_name)
            if month:
                return f'2026-{month:02d}-{day:02d}'
        # Just a day number - need month/year from context (handled by caller)
        m = re.match(r'^\d{1,2}$', s)
        if m:
            return 'DAY_ONLY'
        return None

    start = _parse_single(start_part)
    end = _parse_single(end_part) if end_part else start

    # Handle "DAY_ONLY" start - need to borrow month/year from end
    if start == 'DAY_ONLY' and end:
        # Extract month/year from end date
        m = re.match(r'\d{4}-(\d{2})-(\d{2})', end)
        if m:
            month, day = m.group(1), m.group(2)
            start_day = int(start_part)
            start = f'2026-{month}-{start_day:02d}'

    if isinstance(start, tuple):
        return start[0], start[1]
    return start, end


# Read actual date_raw values from CSV
df_raw = []
with open('events_all.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        df_raw.append(row)

# Show unique date_raw patterns
date_patterns = {}
for row in df_raw:
    dr = row['date_raw']
    if dr not in date_patterns:
        date_patterns[dr] = 0
    date_patterns[dr] += 1

print("=== Unique date_raw patterns (sample) ===")
for dr, count in sorted(date_patterns.items(), key=lambda x: -x[1])[:30]:
    print(f'  {count:4d}x  {dr!r}')

print("\n=== Testing parse_id_date on samples ===")
test_dates = [
    '04 - 06 Desember 2026',
    '10 Desember 2025 - 4 Januari 2026',
    '10 Desember 2025',
    '4 Januari 2026',
    '02 Ags',
    '13 Januari - 1 Maret 2026',
    '16 Januari – 16 Februari 2026',
    '28 Desember 2025 - 10 Februari 2026',
    '1-14 Januari 2026',
    '17 Januari - 15 Februari 2026',
]
for t in test_dates:
    print(f'  {t!r} -> {parse_id_date(t)}')
