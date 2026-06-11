"""tjk_scraper.py modülü için unit testler."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from seb.tjk_scraper import (
    TURKISH_CITIES,
    _parse_age,
    _parse_ganyan,
    _parse_race_breed,
    _parse_race_distance,
    _parse_race_surface,
    _parse_race_type,
    _parse_time_to_seconds,
    _parse_weight,
)


class TestParseTimeToSeconds:
    def test_standard_format(self):
        assert _parse_time_to_seconds("1.06.96") == pytest.approx(66.96)

    def test_longer_race(self):
        assert _parse_time_to_seconds("2.30.50") == pytest.approx(150.50)

    def test_two_part(self):
        assert _parse_time_to_seconds("66.96") == pytest.approx(66.96)

    def test_empty(self):
        assert _parse_time_to_seconds("") is None

    def test_dash(self):
        assert _parse_time_to_seconds("-") is None

    def test_with_comma(self):
        assert _parse_time_to_seconds("1.06,96") == pytest.approx(66.96)


class TestParseWeight:
    def test_simple(self):
        assert _parse_weight("57") == pytest.approx(57.0)

    def test_with_extra(self):
        assert _parse_weight("57+0.30Fazla Kilo") == pytest.approx(57.3)

    def test_with_comma(self):
        assert _parse_weight("57,5") == pytest.approx(57.5)

    def test_empty(self):
        assert _parse_weight("") is None


class TestParseAge:
    def test_standard(self):
        assert _parse_age("2y d  e") == 2

    def test_three_year_old(self):
        assert _parse_age("3y k  e") == 3

    def test_empty(self):
        assert _parse_age("") is None


class TestParseGanyan:
    def test_standard(self):
        assert _parse_ganyan("6,70") == pytest.approx(6.70)

    def test_dot_format(self):
        assert _parse_ganyan("3.50") == pytest.approx(3.50)

    def test_empty(self):
        assert _parse_ganyan("") is None

    def test_dash(self):
        assert _parse_ganyan("-") is None

    def test_invalid(self):
        assert _parse_ganyan("abc") is None


class TestParseRaceBreed:
    def _make_div(self, text: str):
        return BeautifulSoup(f"<div>{text}</div>", "lxml").find("div")

    def test_ingiliz(self):
        div = self._make_div("Maiden , 2 Yaşlı İngilizler, 57 kg, 1100 Çim")
        assert _parse_race_breed(div) == "İngiliz"

    def test_arap(self):
        div = self._make_div("ŞARTLI 4/DHÖW , 3 Yaşlı Araplar, 57 kg, 1200 Çim")
        assert _parse_race_breed(div) == "Arap"

    def test_unknown(self):
        div = self._make_div("Handicap , 4+ Yaşlılar, 58 kg, 1600 Kum")
        assert _parse_race_breed(div) == "Bilinmiyor"


class TestParseRaceDistance:
    def _make_div(self, text: str):
        return BeautifulSoup(f"<div>{text}</div>", "lxml").find("div")

    def test_with_surface(self):
        div = self._make_div("1100 Çim")
        assert _parse_race_distance(div) == 1100

    def test_kum(self):
        div = self._make_div("1600 Kum")
        assert _parse_race_distance(div) == 1600

    def test_sentetik(self):
        div = self._make_div("2000 Sentetik")
        assert _parse_race_distance(div) == 2000


class TestParseRaceSurface:
    def _make_div(self, text: str):
        return BeautifulSoup(f"<div>{text}</div>", "lxml").find("div")

    def test_cim(self):
        assert _parse_race_surface(self._make_div("1200 Çim")) == "çim"

    def test_kum(self):
        assert _parse_race_surface(self._make_div("1600 Kum")) == "kum"

    def test_sentetik(self):
        assert _parse_race_surface(self._make_div("2000 Sentetik")) == "sentetik"

    def test_unknown(self):
        assert _parse_race_surface(self._make_div("mesafe bilgisi yok")) == "bilinmiyor"


class TestParseRaceType:
    def _make_div(self, text: str):
        return BeautifulSoup(f"<div>{text}</div>", "lxml").find("div")

    def test_maiden(self):
        assert _parse_race_type(self._make_div("Maiden 2 Yaşlı")) == "maiden"

    def test_handicap(self):
        assert _parse_race_type(self._make_div("Handicap 4+")) == "handicap"

    def test_sartli(self):
        assert _parse_race_type(self._make_div("ŞARTLI 4/DHÖW")) == "şartlı"

    def test_grup(self):
        assert _parse_race_type(self._make_div("GRUP 1 KOŞUSU")) == "grup"

    def test_listed(self):
        assert _parse_race_type(self._make_div("LİSTED KOŞU")) == "listed"

    def test_diger(self):
        assert _parse_race_type(self._make_div("Bilinmeyen tip")) == "diğer"


class TestTurkishCities:
    def test_all_turkish_cities_present(self):
        expected_cities = {
            "Adana", "İzmir", "İstanbul", "Bursa", "Ankara",
            "Şanlıurfa", "Elazığ", "Diyarbakır", "Kocaeli", "Antalya",
        }
        actual_cities = set(TURKISH_CITIES.values())
        assert actual_cities == expected_cities

    def test_ids_range(self):
        for city_id in TURKISH_CITIES:
            assert 1 <= city_id <= 10
