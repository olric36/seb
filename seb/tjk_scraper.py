"""TJK (Türkiye Jokey Kulübü) web sitesinden yarış verisi çekme.

Sadece Türkiye hipodromlarından son 6 aylık yarış sonuçlarını toplar.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Türkiye hipodromları (SehirId -> İsim)
TURKISH_CITIES: dict[int, str] = {
    1: "Adana",
    2: "İzmir",
    3: "İstanbul",
    4: "Bursa",
    5: "Ankara",
    6: "Şanlıurfa",
    7: "Elazığ",
    8: "Diyarbakır",
    9: "Kocaeli",
    10: "Antalya",
}

BASE_URL = "https://www.tjk.org"
DATA_URL = f"{BASE_URL}/TR/YarisSever/Info/Data/GunlukYarisSonuclari"
CITY_URL = f"{BASE_URL}/TR/YarisSever/Info/Sehir/GunlukYarisSonuclari"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Request delay to be respectful to the server
REQUEST_DELAY_SECONDS = 1.5


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session


def _parse_time_to_seconds(time_str: str) -> float | None:
    """TJK derece formatını saniyeye çevir (ör: '1.06.96' -> 66.96)."""
    time_str = time_str.strip()
    if not time_str or time_str == "-":
        return None

    parts = time_str.replace(",", ".").split(".")
    try:
        if len(parts) == 3:
            minutes = int(parts[0])
            seconds = int(parts[1])
            centiseconds = int(parts[2])
            return minutes * 60 + seconds + centiseconds / 100
        elif len(parts) == 2:
            seconds = int(parts[0])
            centiseconds = int(parts[1])
            return seconds + centiseconds / 100
    except ValueError:
        return None
    return None


def _parse_weight(weight_str: str) -> float | None:
    """Sıklet metnini kilogram olarak parse et (ör: '57+0.30Fazla Kilo' -> 57.3)."""
    weight_str = weight_str.strip()
    if not weight_str:
        return None
    match = re.match(r"(\d+(?:[.,]\d+)?)", weight_str)
    if match:
        base = float(match.group(1).replace(",", "."))
        extra_match = re.search(r"[+](\d+[.,]?\d*)", weight_str)
        if extra_match:
            base += float(extra_match.group(1).replace(",", "."))
        return base
    return None


def _parse_age(age_str: str) -> int | None:
    """Yaş metnini parse et (ör: '2y d  e' -> 2)."""
    age_str = age_str.strip()
    match = re.match(r"(\d+)", age_str)
    if match:
        return int(match.group(1))
    return None


def _parse_ganyan(ganyan_str: str) -> float | None:
    """Ganyan oranını parse et (ör: '6,70' -> 6.70)."""
    ganyan_str = ganyan_str.strip()
    if not ganyan_str or ganyan_str == "-":
        return None
    try:
        return float(ganyan_str.replace(",", "."))
    except ValueError:
        return None


def _parse_race_distance(detail_div: Tag) -> int | None:
    """Yarış mesafesini race-details div'inden çıkar."""
    text = detail_div.get_text(separator=" ", strip=True)
    match = re.search(r"(\d{3,5})\s*(?:Çim|Kum|Sentetik)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d{3,5})", text)
    if match:
        val = int(match.group(1))
        if 400 <= val <= 5000:
            return val
    return None


def _parse_race_surface(detail_div: Tag) -> str:
    """Pist yüzeyini çıkar."""
    text = detail_div.get_text(separator=" ", strip=True)
    if "Çim" in text:
        return "çim"
    if "Kum" in text:
        return "kum"
    if "Sentetik" in text:
        return "sentetik"
    return "bilinmiyor"


def _parse_race_type(detail_div: Tag) -> str:
    """Yarış tipini çıkar (Maiden, Şartlı, Handicap, vs.)."""
    text = detail_div.get_text(separator=" ", strip=True)
    if "Maiden" in text:
        return "maiden"
    if "Handicap" in text or "HCP" in text:
        return "handicap"
    if "ŞARTLI" in text or "Şartlı" in text:
        return "şartlı"
    if "GRUP" in text or "Grup" in text:
        return "grup"
    if "LİSTED" in text or "Listed" in text:
        return "listed"
    return "diğer"


def _parse_race_breed(detail_div: Tag) -> str:
    """Yarış şartlarından at ırkını çıkar ('İngiliz' veya 'Arap').

    TJK koşu detaylarında "İngilizler" veya "Araplar" kelimeleri geçer.
    """
    text = detail_div.get_text(separator=" ", strip=True)
    if "İngiliz" in text:
        return "İngiliz"
    if "Arap" in text:
        return "Arap"
    return "Bilinmiyor"


def _extract_era(href: str) -> str:
    """TJK link'inden Era parametresini çıkar."""
    match = re.search(r"Era=([^&]+)", href)
    return match.group(1) if match else "lastMonth"


def fetch_race_dates(
    session: requests.Session,
    start_date: date,
    end_date: date,
) -> list[tuple[date, list[tuple[int, str, str]]]]:
    """Tarih aralığındaki yarış günlerini ve hipodromları bul.

    Returns:
        [(tarih, [(sehir_id, sehir_adi, era), ...]), ...]
    """
    results: list[tuple[date, list[tuple[int, str, str]]]] = []
    current = start_date

    while current <= end_date:
        date_str = current.strftime("%d/%m/%Y")
        logger.info("Tarih kontrol ediliyor: %s", date_str)

        try:
            resp = session.post(
                DATA_URL,
                data={"QueryParameter_Tarih": date_str, "Era": "past"},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Tarih %s için veri alınamadı: %s", date_str, e)
            current += timedelta(days=1)
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        cities: list[tuple[int, str, str]] = []

        for a_tag in soup.find_all("a"):
            href = a_tag.get("href", "")
            if "SehirId" not in href:
                continue
            match = re.search(r"SehirId=(\d+)", href)
            if not match:
                continue
            sehir_id = int(match.group(1))
            if sehir_id in TURKISH_CITIES:
                city_name = TURKISH_CITIES[sehir_id]
                era = _extract_era(href)
                cities.append((sehir_id, city_name, era))

        if cities:
            results.append((current, cities))
            city_names = [c[1] for c in cities]
            logger.info("  -> %d Türkiye hipodromu: %s", len(cities), city_names)

        current += timedelta(days=1)
        time.sleep(REQUEST_DELAY_SECONDS)

    return results


def fetch_city_races(
    session: requests.Session,
    race_date: date,
    sehir_id: int,
    sehir_adi: str,
    era: str = "lastMonth",
) -> list[dict]:
    """Belirli bir tarih ve hipodrom için yarış sonuçlarını çek.

    Args:
        session: HTTP session.
        race_date: Yarış tarihi.
        sehir_id: TJK şehir ID'si.
        sehir_adi: Şehir adı.
        era: TJK'nın kullandığı dönem parametresi (ör: lastMonth, lastWeek).

    Returns:
        Yarış kayıtları listesi (her satır bir at girişi).
    """
    date_str = race_date.strftime("%d/%m/%Y")

    try:
        resp = session.get(
            CITY_URL,
            params={
                "SehirId": sehir_id,
                "QueryParameter_Tarih": date_str,
                "SehirAdi": sehir_adi,
                "Era": era,
            },
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("%s %s verisi alınamadı: %s", date_str, sehir_adi, e)
        return []

    if len(resp.text) < 1000:
        logger.warning("%s %s için veri yok veya çok kısa", date_str, sehir_adi)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    records: list[dict] = []

    # Her yarış bir race-details div ve ardından bir table içerir
    detail_divs = soup.find_all("div", class_="race-details")
    tables = soup.find_all("table")

    if len(detail_divs) != len(tables):
        logger.warning(
            "%s %s: details(%d) != tables(%d), minimum kullanılacak",
            date_str,
            sehir_adi,
            len(detail_divs),
            len(tables),
        )

    num_races = min(len(detail_divs), len(tables))

    for race_idx in range(num_races):
        detail = detail_divs[race_idx]
        table = tables[race_idx]

        distance = _parse_race_distance(detail)
        surface = _parse_race_surface(detail)
        race_type = _parse_race_type(detail)
        breed = _parse_race_breed(detail)
        race_no = race_idx + 1

        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        for row in rows[1:]:  # İlk satır header
            cells = row.find_all("td")
            if len(cells) < 12:
                continue

            finish_pos_str = cells[1].get_text(strip=True)
            horse_name_raw = cells[2].get_text(strip=True)
            _ = cells[3].get_text(strip=True)  # yaş (artık DB'de tutulmuyor)
            _ = cells[4].get_text(strip=True)  # orijin (artık DB'de tutulmuyor)
            weight_str = cells[5].get_text(strip=True)
            jockey_name = cells[6].get_text(strip=True)
            _ = cells[7].get_text(strip=True)  # sahip
            _ = cells[8].get_text(strip=True)  # antrenör
            time_str = cells[9].get_text(strip=True)
            ganyan_str = cells[10].get_text(strip=True)

            # At isminden kulvar numarasını ayıkla (ör: "MELONCITTO(4)" -> name=MELONCITTO, post=4)
            horse_match = re.match(r"(.+?)\((\d+)\)", horse_name_raw)
            if horse_match:
                horse_name = horse_match.group(1).strip()
                post_position = int(horse_match.group(2))
            else:
                horse_name = horse_name_raw.strip()
                post_position = None

            # Finish position
            try:
                finish_position = int(finish_pos_str)
            except ValueError:
                finish_position = None

            record = {
                "tarih": race_date.isoformat(),
                "hipodrom": sehir_adi,
                "hipodrom_id": sehir_id,
                "kosu_no": race_no,
                "kosu_tipi": race_type,
                "mesafe": distance,
                "zemin": surface,
                "at_ismi": horse_name,
                "irk": breed,
                "kulvar": post_position,
                "siklet": _parse_weight(weight_str),
                "jokey": jockey_name,
                "derece_sn": _parse_time_to_seconds(time_str),
                "derece_str": time_str,
                "ganyan": _parse_ganyan(ganyan_str),
                "siralama": finish_position,
            }
            records.append(record)

    logger.info(
        "%s %s: %d koşu, %d kayıt",
        date_str,
        sehir_adi,
        num_races,
        len(records),
    )
    return records


def scrape_tjk(
    months: int = 6,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """TJK'dan son N aylık Türkiye yarış verilerini çek.

    Args:
        months: Kaç ay geriye gidilecek (varsayılan 6).
        output_path: Sonuç CSV dosyasının kaydedileceği yol (opsiyonel).

    Returns:
        Tüm yarış kayıtlarını içeren DataFrame.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    logger.info("TJK veri çekme başlıyor: %s - %s", start_date, end_date)

    session = _create_session()
    all_records: list[dict] = []

    # Önce yarış günlerini bul
    race_days = fetch_race_dates(session, start_date, end_date)
    logger.info("Toplam %d yarış günü bulundu", len(race_days))

    # Her yarış günü ve hipodrom için sonuçları çek
    for race_date, cities in race_days:
        for sehir_id, sehir_adi, era in cities:
            records = fetch_city_races(
                session, race_date, sehir_id, sehir_adi, era,
            )
            all_records.extend(records)
            time.sleep(REQUEST_DELAY_SECONDS)

    if not all_records:
        logger.warning("Hiç yarış verisi bulunamadı")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("Veri kaydedildi: %s (%d satır)", output_path, len(df))

    return df


def scrape_tjk_single_date(
    race_date: date,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Tek bir gün için TJK yarış sonuçlarını çek."""
    if session is None:
        session = _create_session()

    date_str = race_date.strftime("%d/%m/%Y")

    try:
        resp = session.post(
            DATA_URL,
            data={"QueryParameter_Tarih": date_str, "Era": "past"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Tarih %s için veri alınamadı: %s", date_str, e)
        return pd.DataFrame()

    soup = BeautifulSoup(resp.text, "lxml")
    all_records: list[dict] = []

    for a_tag in soup.find_all("a"):
        href = a_tag.get("href", "")
        if "SehirId" not in href:
            continue
        match = re.search(r"SehirId=(\d+)", href)
        if not match:
            continue
        sehir_id = int(match.group(1))
        if sehir_id not in TURKISH_CITIES:
            continue

        sehir_adi = TURKISH_CITIES[sehir_id]
        era = _extract_era(href)
        records = fetch_city_races(
            session, race_date, sehir_id, sehir_adi, era,
        )
        all_records.extend(records)
        time.sleep(REQUEST_DELAY_SECONDS)

    return pd.DataFrame(all_records) if all_records else pd.DataFrame()
