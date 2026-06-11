"""Veritabanı yönetimi (DatabaseManager).

Tablo modelleri ayrı dosyalarda:
    - at.py: At (atlar)
    - jokey.py: Jokey (jokeyler)
    - mesafe.py: Mesafe (mesafeler)
    - race.py: Hipodrom (hipodromlar) + Yaris (yarislar)
    - result.py: YarisSonucu (yaris_sonuclari)
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Integer, create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from seb.at import At
from seb.base import Base
from seb.jokey import Jokey
from seb.mesafe import Mesafe
from seb.race import Hipodrom, Yaris
from seb.result import YarisSonucu

if TYPE_CHECKING:
    from pandas import DataFrame

DEFAULT_DB_PATH = "seb_yarislar.db"


class DatabaseManager:
    """Veritabanı bağlantı ve işlem yöneticisi."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self._session_factory = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Tüm tabloları oluştur."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Tüm tabloları sil."""
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Yeni bir veritabanı oturumu döndür."""
        return self._session_factory()

    def get_or_create_hipodrom(
        self, session: Session, tjk_id: int, isim: str, sehir: str
    ) -> Hipodrom:
        """Hipodromu bul veya oluştur."""
        hipodrom = session.query(Hipodrom).filter_by(tjk_id=tjk_id).first()
        if hipodrom is None:
            hipodrom = Hipodrom(tjk_id=tjk_id, isim=isim, sehir=sehir)
            session.add(hipodrom)
            session.flush()
        return hipodrom

    def get_or_create_at(self, session: Session, ad: str, irk: str | None = None) -> At:
        """Atı bul veya oluştur."""
        at = session.query(At).filter_by(ad=ad, irk=irk).first()
        if at is None:
            at = At(ad=ad, irk=irk, yaris_sayisi=1)
            session.add(at)
            session.flush()
        else:
            at.yaris_sayisi = (at.yaris_sayisi or 0) + 1
        return at

    def get_or_create_jokey(self, session: Session, ad: str) -> Jokey:
        """Jokeyi bul veya oluştur."""
        jokey = session.query(Jokey).filter_by(ad=ad).first()
        if jokey is None:
            jokey = Jokey(ad=ad, yarsay=1)
            session.add(jokey)
            session.flush()
        else:
            jokey.yarsay = (jokey.yarsay or 0) + 1
        return jokey

    def get_or_create_mesafe(self, session: Session, metre: int) -> Mesafe:
        """Mesafeyi bul veya oluştur."""
        from seb.mesafe import mesafe_kategorisi

        mesafe_obj = session.query(Mesafe).filter_by(metre=metre).first()
        if mesafe_obj is None:
            kategori = mesafe_kategorisi(metre)
            mesafe_obj = Mesafe(metre=metre, kategori=kategori)
            session.add(mesafe_obj)
            session.flush()
        return mesafe_obj

    def get_or_create_yaris(
        self,
        session: Session,
        yartar: date,
        il: str | None = None,
        pist: str | None = None,
        kosuno: int = 1,
        irk: str | None = None,
        mesafe: int | None = None,
        atsay: int | None = None,
        pist_durumu: str | None = None,
    ) -> Yaris:
        """Yarışı bul veya oluştur."""
        yaris = (
            session.query(Yaris)
            .filter_by(yartar=yartar, il=il, kosuno=kosuno)
            .first()
        )
        if yaris is None:
            yaris = Yaris(
                yartar=yartar,
                il=il,
                pist=pist,
                kosuno=kosuno,
                irk=irk,
                mesafe=mesafe,
                atsay=atsay,
                pist_durumu=pist_durumu,
            )
            session.add(yaris)
            session.flush()
        return yaris

    def add_yaris_sonucu(
        self,
        session: Session,
        yaris_id: int,
        at_id: int,
        jokey_id: int,
        tarih: date,
        hipodrom_id: int,
        kosu_no: int,
        kulvar: int | None = None,
        siklet: float | None = None,
        siralama: int | None = None,
        derece_sn: float | None = None,
        derece_str: str | None = None,
        ganyan: float | None = None,
    ) -> YarisSonucu:
        """Yarış sonucu ekle (zaten varsa atla)."""
        existing = (
            session.query(YarisSonucu)
            .filter_by(yaris_id=yaris_id, at_id=at_id)
            .first()
        )
        if existing is not None:
            return existing

        sonuc = YarisSonucu(
            yaris_id=yaris_id,
            at_id=at_id,
            jokey_id=jokey_id,
            tarih=tarih,
            hipodrom_id=hipodrom_id,
            kosu_no=kosu_no,
            kulvar=kulvar,
            siklet=siklet,
            siralama=siralama,
            derece_sn=derece_sn,
            derece_str=derece_str,
            ganyan=ganyan,
        )
        session.add(sonuc)
        session.flush()
        return sonuc

    def import_from_dataframe(self, df: "DataFrame") -> dict[str, int]:
        """Scraper DataFrame'ini veritabanına aktar.

        Returns:
            Tablolardaki toplam kayıt sayıları.
        """
        import pandas as pd

        if df.empty:
            return {
                "hipodromlar": 0, "atlar": 0, "jokeyler": 0,
                "mesafeler": 0, "yarislar": 0, "sonuclar": 0,
            }

        session = self.get_session()
        try:
            for _, row in df.iterrows():
                # Hipodrom
                hipodrom = self.get_or_create_hipodrom(
                    session,
                    tjk_id=int(row["hipodrom_id"]),
                    isim=str(row["hipodrom"]),
                    sehir=str(row["hipodrom"]),
                )

                # At
                irk = str(row.get("irk", "")) or None
                at = self.get_or_create_at(
                    session,
                    ad=str(row["at_ismi"]),
                    irk=irk,
                )

                # Jokey
                jokey = self.get_or_create_jokey(session, ad=str(row["jokey"]))

                # Mesafe (ayrı tablo)
                mesafe_val = None
                if pd.notna(row.get("mesafe")) and int(row["mesafe"]) > 0:
                    mesafe_val = int(row["mesafe"])
                    self.get_or_create_mesafe(session, metre=mesafe_val)

                # Yarış
                yartar = (
                    row["tarih"]
                    if isinstance(row["tarih"], date)
                    else datetime.fromisoformat(str(row["tarih"])).date()
                )
                il_str = str(row["hipodrom"]) if pd.notna(row.get("hipodrom")) else None
                yaris = self.get_or_create_yaris(
                    session,
                    yartar=yartar,
                    il=il_str,
                    pist=str(row.get("zemin", "")) or None,
                    kosuno=int(row["kosu_no"]),
                    irk=irk,
                    mesafe=mesafe_val,
                    pist_durumu=str(row.get("kosu_tipi", "")) or None,
                )

                # Sonuç (denormalize alanlar dahil)
                self.add_yaris_sonucu(
                    session,
                    yaris_id=yaris.id,
                    at_id=at.id,
                    jokey_id=jokey.id,
                    tarih=yartar,
                    hipodrom_id=hipodrom.id,
                    kosu_no=int(row["kosu_no"]),
                    kulvar=int(row["kulvar"]) if pd.notna(row.get("kulvar")) else None,
                    siklet=float(row["siklet"]) if pd.notna(row.get("siklet")) else None,
                    siralama=int(row["siralama"]) if pd.notna(row.get("siralama")) else None,
                    derece_sn=float(row["derece_sn"]) if pd.notna(row.get("derece_sn")) else None,
                    derece_str=str(row.get("derece_str", "")) or None,
                    ganyan=float(row["ganyan"]) if pd.notna(row.get("ganyan")) else None,
                )

            session.commit()

            counts = {
                "hipodromlar": session.query(Hipodrom).count(),
                "atlar": session.query(At).count(),
                "jokeyler": session.query(Jokey).count(),
                "mesafeler": session.query(Mesafe).count(),
                "yarislar": session.query(Yaris).count(),
                "sonuclar": session.query(YarisSonucu).count(),
            }

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return counts

    def get_statistics(self) -> dict[str, int]:
        """Veritabanı istatistiklerini döndür."""
        session = self.get_session()
        try:
            return {
                "hipodromlar": session.query(Hipodrom).count(),
                "atlar": session.query(At).count(),
                "jokeyler": session.query(Jokey).count(),
                "mesafeler": session.query(Mesafe).count(),
                "yarislar": session.query(Yaris).count(),
                "yaris_sonuclari": session.query(YarisSonucu).count(),
            }
        finally:
            session.close()

    def query_at_istatistikleri(self, min_yaris: int = 3) -> list[dict]:
        """At bazlı istatistikleri sorgula."""
        session = self.get_session()
        try:
            results = (
                session.query(
                    At.ad,
                    At.irk,
                    func.count(YarisSonucu.id).label("toplam_yaris"),
                    func.sum(
                        func.cast(YarisSonucu.siralama == 1, Integer)
                    ).label("birincilik"),
                    func.sum(
                        func.cast(YarisSonucu.siralama <= 3, Integer)
                    ).label("ilk_uc"),
                    func.avg(YarisSonucu.ganyan).label("ort_ganyan"),
                )
                .join(At)
                .group_by(At.id)
                .having(func.count(YarisSonucu.id) >= min_yaris)
                .order_by(
                    (
                        func.sum(func.cast(YarisSonucu.siralama == 1, Integer))
                        * 1.0
                        / func.count(YarisSonucu.id)
                    ).desc()
                )
                .all()
            )
            return [
                {
                    "at": r.ad,
                    "irk": r.irk,
                    "toplam_yaris": r.toplam_yaris,
                    "birincilik": r.birincilik or 0,
                    "ilk_uc": r.ilk_uc or 0,
                    "kazanma_orani": round((r.birincilik or 0) / r.toplam_yaris, 3),
                    "ort_ganyan": round(r.ort_ganyan, 2) if r.ort_ganyan else None,
                }
                for r in results
            ]
        finally:
            session.close()

    def query_jokey_istatistikleri(self, min_yaris: int = 5) -> list[dict]:
        """Jokey bazlı istatistikleri sorgula."""
        session = self.get_session()
        try:
            results = (
                session.query(
                    Jokey.ad,
                    func.count(YarisSonucu.id).label("toplam_yaris"),
                    func.sum(
                        func.cast(YarisSonucu.siralama == 1, Integer)
                    ).label("birincilik"),
                    func.sum(
                        func.cast(YarisSonucu.siralama <= 3, Integer)
                    ).label("ilk_uc"),
                )
                .join(Jokey)
                .group_by(Jokey.id)
                .having(func.count(YarisSonucu.id) >= min_yaris)
                .order_by(
                    (
                        func.sum(func.cast(YarisSonucu.siralama == 1, Integer))
                        * 1.0
                        / func.count(YarisSonucu.id)
                    ).desc()
                )
                .all()
            )
            return [
                {
                    "jokey": r.ad,
                    "toplam_yaris": r.toplam_yaris,
                    "birincilik": r.birincilik or 0,
                    "ilk_uc": r.ilk_uc or 0,
                    "kazanma_orani": round((r.birincilik or 0) / r.toplam_yaris, 3),
                }
                for r in results
            ]
        finally:
            session.close()

    def query_mesafe_istatistikleri(self) -> list[dict]:
        """Mesafe bazlı yarış istatistikleri."""
        session = self.get_session()
        try:
            results = (
                session.query(
                    Mesafe.metre,
                    Mesafe.kategori,
                    func.count(Yaris.id).label("toplam_yaris"),
                )
                .join(Yaris, Yaris.mesafe == Mesafe.metre)
                .group_by(Mesafe.id)
                .order_by(Mesafe.metre)
                .all()
            )
            return [
                {
                    "metre": r.metre,
                    "kategori": r.kategori,
                    "toplam_yaris": r.toplam_yaris,
                }
                for r in results
            ]
        finally:
            session.close()
