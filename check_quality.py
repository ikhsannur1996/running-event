#!/usr/bin/env python3
"""Check data quality of scraped events"""
import pandas as pd
import re

df = pd.read_csv('events_all.csv')
print('Shape:', df.shape)
print()

sub = df[df['source'] == 'jadwallari.id']
print(f'=== jadwallari.id ({len(sub)} events) ===')
print(sub[['event_name', 'start_date', 'end_date', 'category', 'location']].head(15).to_string())
print()

# Check for leading dash or date in names
bad = sub[sub['event_name'].str.match(r'^[-–\s]|\d{1,2}\s+[A-Za-z]+\s+\d{4}', na=False)]
print(f'Names starting with dash or date: {len(bad)}')
if len(bad) > 0:
    print(bad['event_name'].head(10).to_string())
print()

# Normalize and check duplicates
def norm(name):
    n = str(name).lower()
    n = re.sub(r'\s*(virtual run|fun run|trail run|road run|charity run|marathon|half marathon|ultra|ekiden|fun walk|kids dash|vertical run)\s*$', '', n)
    n = re.sub(r'[^a-z0-9\s]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

sub['norm'] = sub['event_name'].apply(norm)
dupes = sub[sub.duplicated(['norm', 'start_date'], keep=False)]
print(f'Potential duplicates (same norm name + date): {len(dupes)}')
if len(dupes) > 0:
    print(dupes[['event_name', 'start_date', 'category', 'norm']].head(20).to_string())

print()
print('=== All sources breakdown ===')
print(df.groupby('source').size())
print()

# Check date parsing success rate
df['date_parsed'] = df['start_date'] != ''
print(f'Events with parsed dates: {df["date_parsed"].sum()} / {len(df)}')
print()

# Show sample from each source
for src in df['source'].unique():
    s = df[df['source'] == src]
    print(f'--- {src} ({len(s)} events) ---')
    print(s[['event_name', 'start_date', 'category', 'location']].head(3).to_string())
    print()
