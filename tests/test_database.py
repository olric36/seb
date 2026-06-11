"""database.py modülü için unit testler."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from seb.database import (
    DatabaseManager,
    mesafe_kategorisi,
)


@pytest.fixture
def db(tmp_path):
    """Geçici veritabanı oluştur."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)
    manager.create_tables()
    return manager


class TestMesafeKategorisi:
    def test_sprint(self):
        assert mesafe_kategorisi(1000) == "sprint"
        assert mesafe_kategorisi(1200) == "sprint"

    def test_kisa(self):
        assert mesafe_kategorisi(1400) == "kısa"
        assert mesafe_kategorisi(1500) == "kısa"

    def test_orta(self):
        assert mesafe_kategorisi(1600) == "orta"
        assert mesafe_kategorisi(1800) == "orta"

    def test_uzun(self):
        assert mesafe_kategorisi(2000) == "uzun"
        assert mesafe_kategorisi(2400) == "uzun"
        assert mesafe_kategorisi(3000) == "uzun"


class TestDatabaseManager:
    def test_create_tables(self, db):
        stats = db.get_statistics()
        assert stats["hipodromlar"] == 0
        assert stats["atlar"] == 0
        assert stats["jokeyler"] == 0
        assert stats["mesafeler"] == 0
        assert stats["yarislar"] == 0
        assert stats["yaris_sonuclari"] == 0

    def test_get_or_create_hipodrom(self, db):
        session = db.get_session()
        h1 = db.get_or_create_hipodrom(session, tjk_id=3, isim="Veliefendi", sehir="İstanbul")
        session.commit()
        assert h1.id is not None
        assert h1.tjk_id == 3
        assert h1.isim == "Veliefendi"

        # Aynı tjk_id ile tekrar çağırınca mevcut kaydı döndürmeli
        h2 = db.get_or_create_hipodrom(session, tjk_id=3, isim="Veliefendi", sehir="İstanbul")
        assert h2.id == h1.id
        session.close()

    def test_get_or_create_at(self, db):
        session = db.get_session()
        at1 = db.get_or_create_at(session, ad="BOLD PILOT", irk="İngiliz")
        session.commit()
        assert at1.id is not None
        assert at1.ad == "BOLD PILOT"
        assert at1.irk == "İngiliz"
        assert at1.yaris_sayisi == 1

        # Aynı ad+ırk ile tekrar — yaris_sayisi artar
        at2 = db.get_or_create_at(session, ad="BOLD PILOT", irk="İngiliz")
        assert at2.id == at1.id
        assert at2.yaris_sayisi == 2

        # Farklı ırk ile ayrı kayıt
        at3 = db.get_or_create_at(session, ad="BOLD PILOT", irk="Arap")
        session.commit()
        assert at3.id != at1.id
        session.close()

    def test_get_or_create_jokey(self, db):
        session = db.get_session()
        j1 = db.get_or_create_jokey(session, ad="A.ÇELIK")
        session.commit()
        assert j1.id is not None
        assert j1.ad == "A.ÇELIK"
        assert j1.yarsay == 1

        j2 = db.get_or_create_jokey(session, ad="A.ÇELIK")
        assert j2.id == j1.id
        assert j2.yarsay == 2
        session.close()

    def test_get_or_create_mesafe(self, db):
        session = db.get_session()
        m1 = db.get_or_create_mesafe(session, metre=1200)
        session.commit()
        assert m1.id is not None
        assert m1.metre == 1200
        assert m1.kategori == "sprint"

        m2 = db.get_or_create_mesafe(session, metre=1200)
        assert m2.id == m1.id

        m3 = db.get_or_create_mesafe(session, metre=2400)
        session.commit()
        assert m3.kategori == "uzun"
        assert m3.id != m1.id
        session.close()

    def test_get_or_create_yaris(self, db):
        session = db.get_session()
        h = db.get_or_create_hipodrom(session, tjk_id=3, isim="Veliefendi", sehir="İstanbul")
        session.commit()

        y1 = db.get_or_create_yaris(
            session,
            tarih=date(2026, 6, 1),
            hipodrom_id=h.id,
            kosu_no=1,
            kosu_tipi="maiden",
            zemin="çim",
        )
        session.commit()
        assert y1.id is not None

        y2 = db.get_or_create_yaris(
            session, tarih=date(2026, 6, 1), hipodrom_id=h.id, kosu_no=1
        )
        assert y2.id == y1.id
        session.close()

    def test_add_yaris_sonucu(self, db):
        session = db.get_session()
        h = db.get_or_create_hipodrom(session, tjk_id=3, isim="Veliefendi", sehir="İstanbul")
        at = db.get_or_create_at(session, ad="STORM", irk="İngiliz")
        jokey = db.get_or_create_jokey(session, ad="B.MIRIK")
        y = db.get_or_create_yaris(
            session, tarih=date(2026, 6, 1), hipodrom_id=h.id, kosu_no=1
        )
        session.commit()

        s1 = db.add_yaris_sonucu(
            session,
            yaris_id=y.id,
            at_id=at.id,
            jokey_id=jokey.id,
            tarih=date(2026, 6, 1),
            hipodrom_id=h.id,
            kosu_no=1,
            kulvar=3,
            siklet=57.0,
            siralama=1,
            derece_sn=66.96,
            derece_str="1.06.96",
            ganyan=6.70,
        )
        session.commit()
        assert s1.id is not None
        assert s1.siralama == 1

        # Duplikasyon kontrolü
        s2 = db.add_yaris_sonucu(
            session,
            yaris_id=y.id,
            at_id=at.id,
            jokey_id=jokey.id,
            tarih=date(2026, 6, 1),
            hipodrom_id=h.id,
            kosu_no=1,
        )
        assert s2.id == s1.id
        session.close()

    def test_import_from_dataframe(self, db):
        df = pd.DataFrame(
            [
                {
                    "tarih": "2026-06-01",
                    "hipodrom": "Bursa",
                    "hipodrom_id": 4,
                    "kosu_no": 1,
                    "kosu_tipi": "maiden",
                    "mesafe": 1100,
                    "zemin": "çim",
                    "at_ismi": "MELONCITTO",
                    "irk": "İngiliz",
                    "kulvar": 4,
                    "siklet": 57.0,
                    "jokey": "O.YILDIZ",
                    "derece_sn": 66.96,
                    "derece_str": "1.06.96",
                    "ganyan": 6.70,
                    "siralama": 1,
                },
                {
                    "tarih": "2026-06-01",
                    "hipodrom": "Bursa",
                    "hipodrom_id": 4,
                    "kosu_no": 1,
                    "kosu_tipi": "maiden",
                    "mesafe": 1100,
                    "zemin": "çim",
                    "at_ismi": "I LOVE SPEED",
                    "irk": "İngiliz",
                    "kulvar": 3,
                    "siklet": 57.0,
                    "jokey": "B.M.MIRIK",
                    "derece_sn": 66.97,
                    "derece_str": "1.06.97",
                    "ganyan": 3.50,
                    "siralama": 2,
                },
            ]
        )

        counts = db.import_from_dataframe(df)
        assert counts["hipodromlar"] == 1
        assert counts["atlar"] == 2
        assert counts["jokeyler"] == 2
        assert counts["mesafeler"] == 1
        assert counts["yarislar"] == 1
        assert counts["sonuclar"] == 2

    def test_import_empty_dataframe(self, db):
        counts = db.import_from_dataframe(pd.DataFrame())
        assert counts["sonuclar"] == 0

    def test_import_idempotent(self, db):
        """Aynı veriyi iki kez import etmek kayıt sayısını artırmamalı."""
        df = pd.DataFrame(
            [
                {
                    "tarih": "2026-06-01",
                    "hipodrom": "Bursa",
                    "hipodrom_id": 4,
                    "kosu_no": 1,
                    "kosu_tipi": "maiden",
                    "mesafe": 1100,
                    "zemin": "çim",
                    "at_ismi": "TEST AT",
                    "irk": "Arap",
                    "kulvar": 1,
                    "siklet": 55.0,
                    "jokey": "TEST JOKEY",
                    "derece_sn": 70.0,
                    "derece_str": "1.10.00",
                    "ganyan": 5.0,
                    "siralama": 1,
                },
            ]
        )
        counts1 = db.import_from_dataframe(df)
        counts2 = db.import_from_dataframe(df)
        assert counts1 == counts2

    def test_get_statistics(self, db):
        stats = db.get_statistics()
        assert isinstance(stats, dict)
        assert "hipodromlar" in stats
        assert "atlar" in stats
        assert "mesafeler" in stats

    def test_query_mesafe_istatistikleri(self, db):
        df = pd.DataFrame(
            [
                {
                    "tarih": "2026-06-01",
                    "hipodrom": "Bursa",
                    "hipodrom_id": 4,
                    "kosu_no": 1,
                    "kosu_tipi": "maiden",
                    "mesafe": 1200,
                    "zemin": "çim",
                    "at_ismi": "AT1",
                    "irk": "İngiliz",
                    "kulvar": 1,
                    "siklet": 57.0,
                    "jokey": "JOKEY1",
                    "derece_sn": 72.0,
                    "derece_str": "1.12.00",
                    "ganyan": 4.0,
                    "siralama": 1,
                },
            ]
        )
        db.import_from_dataframe(df)
        results = db.query_mesafe_istatistikleri()
        assert len(results) == 1
        assert results[0]["metre"] == 1200
        assert results[0]["kategori"] == "sprint"
