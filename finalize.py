#!/usr/bin/env python3
"""Finalize and clean the scraped events data"""
import pandas as pd

df = pd.read_csv('events_all.csv')

# Remove entries with no parsed date (nav links, etc.)
df_clean = df[df['start_date'].notna() & (df['start_date'] != '')].copy()
print(f'Before cleaning: {len(df)} events')
print(f'After cleaning: {len(df_clean)} events')

# Save clean version
df_clean.to_csv('events_all_clean.csv', index=False, encoding='utf-8')
print('Saved to events_all_clean.csv')

print('\n=== Final breakdown by source ===')
print(df_clean.groupby('source').size())

print('\n=== Date range ===')
print(f'Earliest: {df_clean["start_date"].min()}')
print(f'Latest: {df_clean["start_date"].max()}')

print('\n=== Categories (top 15) ===')
print(df_clean['category'].value_counts().head(15))

print('\n=== Locations (top 15) ===')
print(df_clean['location'].value_counts().head(15))

print('\n=== Sample events ===')
print(df_clean[['source','event_name','start_date','end_date','category','location']].head(20).to_string())
