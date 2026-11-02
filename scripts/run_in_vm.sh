#!/bin/bash
# Script menjalankan scraper di VM
# Bisa dipause dengan environment variable SCRAPE_PAUSE

cd /home/$(whoami)/running-event
source venv/bin/activate

echo "[$(date)] Memulai scraping..."
python3 scrape_all.py

echo "[$(date)] Scraping selesai."
