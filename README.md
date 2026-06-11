# SEB — TJK Yarış Verisi Çekme ve Analiz Aracı

Python ile geliştirilmiş, TJK (Türkiye Jokey Kulübü) verilerini çeken ve SQLite veritabanında saklayan veri işleme aracı.

## Özellikler

- **TJK Veri Çekme**: tjk.org'dan son 6 aylık Türkiye yarış sonuçlarını otomatik çekme
- **Veritabanı**: SQLite ile yapılandırılmış veri saklama (hipodromlar, atlar, jokeyler, mesafeler, yarışlar, sonuçlar)
- **İstatistik Analizi**: At, jokey ve mesafe bazlı detaylı istatistikler
- **CLI Arayüzü**: Komut satırından kolay kullanım

## Kurulum

```bash
pip install -e .
```

Geliştirme için:
```bash
pip install -e ".[dev]"
```

## Kullanım

### TJK'dan Veri Çekme

```bash
# Son 6 aylık tüm Türkiye yarışlarını çek ve veritabanına kaydet
seb fetch

# Son 3 aylık verileri çek
seb fetch --months 3

# CSV olarak da kaydet
seb fetch --csv veriler.csv

# Belirli bir tarihin verilerini çek
seb fetch-date 2026-06-01
```

### İstatistikler

```bash
# Veritabanı genel istatistikleri
seb stats

# At bazlı istatistikler
seb at-stats --min-yaris 5 --limit 30

# Jokey bazlı istatistikler
seb jokey-stats --min-yaris 10

# Mesafe bazlı istatistikler
seb mesafe-stats

# Verbose mod
seb -v fetch --months 1
```

## Veritabanı Yapısı

| Tablo | Açıklama |
|-------|----------|
| `hipodromlar` | Türkiye hipodromları (İstanbul, Ankara, İzmir, Bursa, Adana, Elazığ, Şanlıurfa, Diyarbakır, Kocaeli, Antalya) |
| `atlar` | At kayıtları (isim, ırk: İngiliz/Arap) |
| `jokeyler` | Jokey kayıtları |
| `mesafeler` | Yarış mesafeleri ve kategorileri (sprint/kısa/orta/uzun) |
| `yarislar` | Yarış detayları (tarih, hipodrom, mesafe, koşu tipi, zemin) |
| `yaris_sonuclari` | Her yarıştaki at-jokey sonuçları (sıralama, derece, ganyan, sıklet) |

## Python API

```python
from seb.database import DatabaseManager
from seb.tjk_scraper import scrape_tjk

# Veri çek
df = scrape_tjk(months=6)

# Veritabanına aktar
db = DatabaseManager("yarislar.db")
db.create_tables()
counts = db.import_from_dataframe(df)

# İstatistikler
print(db.get_statistics())
print(db.query_at_istatistikleri(min_yaris=3))
print(db.query_jokey_istatistikleri(min_yaris=5))
print(db.query_mesafe_istatistikleri())
```

## Testler

```bash
pytest
```

## Proje Yapısı

```
seb/
├── __init__.py
├── cli.py            # Komut satırı arayüzü
├── database.py       # SQLAlchemy ORM modelleri ve veritabanı yönetimi
├── tjk_scraper.py    # TJK web scraper
tests/
├── test_database.py
└── test_tjk_scraper.py
```

## Lisans

MIT
