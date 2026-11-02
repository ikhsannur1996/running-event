# 🏃‍♂️ SCRAPER EVENT LARI INDONESIA 2026 - 55 KOLOM

## 📋 TUJUAN
Proyek ini bertujuan untuk **menyaring dan mengumpulkan data lengkap event lari di Indonesia tahun 2026** dari 13 website utama, dengan format data yang terstruktur dan ready untuk analisis.

## 📦 INSTALASI

### 1. Clone Repository
```bash
git clone https://github.com/username/running-event.git
cd running-event
```

### 2. Buat Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Jalankan Awal
```bash
python3 scrape_all.py
```

## 🚀 CARA MENJALANKAN

### A. Jalankan Secara Default (Full Run)
```bash
python3 scrape_all.py
```
*Proses akan men-scrape semua 13 website dan menyimpan data ke `data/events_raw.json`*

### B. Fitur Start/Pause Otomatis
Anda bisa menghentikan dan melanjutkan scraping kapan saja:

```bash
# Cek status saat ini
echo $SCRAPE_PAUSE

# Hentikan sementara (akan melanjutkan otomatis setelah 60 detik)
SCRAPE_PAUSE=true python3 scrape_all.py

# Untuk stop total: Tekan Ctrl+C
```

### C. Jalankan di Virtual Machine (Cron Job)
```bash
# Setiap hari pukul 06:00 WIB
crontab -e
# Tambahkan baris ini:
0 6 * * * /home/username/running-event/venv/bin/python scrape_all.py >> /home/username/running-event/logs/cron.log 2>&1
```

### D. Auto-Resume dari Data Sebelumnya
Script akan otomatis melanjutkan dari data yang sudah ada (incremental save), jadi tidak akan kehilangan data jika proses terputus.

## 📊 FILE-YANG-DIHASIL

Setiap kali dijalankan, script akan menghasilkan:

| File | Deskripsi |
|------|-----------|
| `data/events_raw.json` | Data mentah lengkap (55 kolom) - selalu diperbarui |
| `data/events_YYYYMMDD.csv` | CSV harian (field terpilih) |
| `logs/scraping_YYYYMMDD.log` | Log operasi harian |

### Contoh Struktur Data (55 Kolom):
1. `source` - Website sumber
2. `event_name` - Nama event
3. `start_date` - Tanggal mulai (YYYY-MM-DD)
4. `end_date` - Tanggal selesai
5. `kota` - Kota event
6. `provinsi` - Provinsi event
7. `kategori_lari_1` - Kategori utama (Fun Run/Road Run/Ultra Run/...)
8. `kategori_lari_2` - Kategori kedua (jika ada)
9. `distance_km_min` - Jarak minimum (KM)
10. `distance_km_max` - Jarak maksimum (KM)
11. `registration_fee` - Biaya registrasi
12. `registration_fee_tiers` - Tier biaya (JSON Array)
13. `prize_benefits` - Hadiah & fasilitas
14. `organizer` - Race Organizer (RO)
15. `event_promoter` - Promotor Acara
15. `sponsor` - Sponsor event
16. `cut_off_time_5km` - Cut-off time 5km
17. `cut_off_time_10km` - Cut-off time 10km
18. `cut_off_time_21km` - Cut-off time half marathon
17. `cut_off_time_42km` - Cut-off time full marathon
17. `cut_off_time_other` - Cut-off time jarak lain
18. `course_elevation_gain` - Kenaikan ketinggian (meter)
18. `course_surface` - Jenis permukaan (Road/Trail/Mixed)
19. `age_group_min` - Umur minimum
20. `age_group_max` - Umur maksimum
20. `prize_money_usd` - Hadiah uang USD
20. `result_link` - Link hasil akhir
20. `parking_info` - Info parkir
20. `public_transport` - Transport umum
20. `accommodation_info` - Saran akomodasi
21. `weather_conditions_typical` - Cuaca rata-rata
21. `kid_friendly` - Baik untuk anak?
21. `pet_friendly` - Boolehadi anjing?
22. `scraped_at` - Waktu di-scrape
22. `data_completeness_score` - Skor lengkapnya data (0-55)
23. `event_frequency` - Frekuensi event
24. `registration_status` - Status pendaftaran
25. `result_link` - Link hasil akhir
25. `social_media_hashtag` - Hashtag resmi
26. `official_website` - Website resmi event
26. `email_contact` - Email kontakt
26. `phone_contact` - Phone/WhatsApp
27. `alternative_date` - Tanggal cadangan
27. `notes` - Catatan tambahan

## 📊 FILE-YANG-DIHASIL

Setiap eksekusi menghasilkan:
- `data/events_raw.json` - Semua event (55 kolom) - **Selalu diperbarui**
- `data/events_YYYYMMDD.csv` - CSV harian (field terpilih)
- `logs/scraping_YYYYMMDD.log` - Log operasi harian

## 🔧 TROUBLESHOOTING

### Masalah Umum:
1. **Script terhenti tiba-tiba**: Coba jalankan ulang, script akan melanjutkan dari data terakhir (incremental save)
2. **Data duplikat**: Script sudah otomatis melakukan deduplikasi berdasarkan (source, nama event, tanggal)
3. **Tidak ada event terbaru**: Coba jalankan dengan `SCRAPE_PAUSE=true` dan cek log untuk pesan error
4. **Koneksi lambat**: Set `time.sleep(2)` di antara setiap website di script

### Menambahkan Website Baru:
Tambahkan fungsi scraper baru di bagian `main()` dan tambahkan ke dalam daftar `scrapers`. Setiap fungsi scraper harus mengembalikan list of dict dengan struktur kolom yang sama.

## 📬 KONTAK
Untuk pertanyaan atau kontribusi, buka issue di GitHub repository.

---
Dibuat dengan ❤️ untuk komunitas pelari Indonesia
