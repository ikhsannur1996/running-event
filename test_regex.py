#!/usr/bin/env python3
"""Test date extraction regex - multiple patterns"""
import re

test_strings = [
    '10 Desember 2025 - 4 Januari 2026 Run for Sumatera 30K Multiple Run Virtual Run Anywhere',
    '04 - 06 Desember 2026 Karimunjawa Beach Trail Run 7K, 10K, 21K',
    '1-14 Januari 2026 Avocado Health Virtual Run 7K, 15K Virtual Run Anywhere',
    '10 Desember 2025 Run for Sumatera 30K Multiple Run Anywhere',
    '28 Desember 2025 - 10 Februari 2026 Resolution Virtual Run 10K Virtual Run Anywhere',
    '17 Januari – 16 Februari 2026 Charity Run Kilometer for Aceh 25K, 50K Charity Run Jakarta Pusat, DKI Jakarta',
    '13 Januari - 1 Maret 2026 Heart of Speed Run 5K, 10K, 21K, 42K Virtual Run Anywhere',
]

patterns = [
    (r'^(\d{1,2}\s+[A-Za-z]+\s+\d{4}\s*[-–—]\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'full_range'),
    (r'^(\d{1,2}\s+[A-Za-z]+\s*[-–—]\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'start_no_year'),
    (r'^(\d{1,2}\s*[-–]\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'shared_month'),
    (r'^(\d{1,2}[-–]\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'connected_days'),
    (r'^(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(.+)$', 'single_date'),
]


def extract_date_and_rest(txt):
    for pattern, name in patterns:
        m = re.match(pattern, txt)
        if m:
            return m.group(1), m.group(2), name
    return None, None, None


for s in test_strings:
    date_part, rest, pname = extract_date_and_rest(s)
    if date_part:
        print(f'PATTERN: {pname}')
        print(f'  DATE: {date_part!r}')
        print(f'  REST: {rest!r}')
    else:
        print(f'NO MATCH: {s!r}')
    print()
