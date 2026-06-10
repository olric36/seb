"""SQLite veritabanı modelleri ve yönetimi.

Tablolar:
    - hipodromlar: Türkiye hipodromları
    - atlar: At kayıtları (isim + ırk)
    - jokeyler: Jokey kayıtları
    - mesafeler: Yarış mesafeleri ve kategorileri
    - yarislar: Yarış detayları
    - yaris_sonuclari: Her yarıştaki at-jokey sonuçları (denormalize alanlar dahil)
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

if TYPE_CHECKING:
    from pandas import DataFrame

DEFAULT_DB_PATH = "seb_yarislar.db"

# Mesafe kategorileri
MESAFE_KATEGORILERI = {
    "sprint": (0, 1300),
    "kısa": (1300, 1600),
    "orta": (1600, 2000),
    "uzun": (2000, 9999),
}


def mesafe_kategorisi(metre: int) -> str:
    """Mesafeye göre kategori belirle."""
    for kategori, (alt, ust) in MESAFE_KATEGORILERI.items():
        if alt <= metre < ust:
            return kategori
    return "bilinmiyor"


class Base(DeclarativeBase):
    pass


class Hipodrom(Base):
    """Hipodrom (yarış pisti) tablosu."""

    __tablename__ = "hipodromlar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tjk_id = Column(Integer, unique=True, nullable=False)
    isim = Column(String(100), nullable=False)
    sehir = Column(String(100), nullable=False)

    yarislar = relationship("Yaris", back_populates="hipodrom")
    sonuclar = relationship("YarisSonucu", back_populates="hipodrom")

    def __repr__(self) -> str:
        return f"<Hipodrom(id={self.id}, isim='{self.isim}', sehir='{self.sehir}')>"


class At(Base):
    """At tablosu."""

    __tablename__ = "atlar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isim = Column(String(200), nullable=False)
    irk = Column(String(50), nullable=True)  # "İngiliz" veya "Arap"

    __table_args__ = (UniqueConstraint("isim", "irk", name="uq_at_isim_irk"),)

    sonuclar = relationship("YarisSonucu", back_populates="at")

    def __repr__(self) -> str:
        return f"<At(id={self.id}, isim='{self.isim}', irk='{self.irk}')>"


class Jokey(Base):
    """Jokey tablosu."""

    __tablename__ = "jokeyler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isim = Column(String(200), unique=True, nullable=False)

    sonuclar = relationship("YarisSonucu", back_populates="jokey")

    def __repr__(self) -> str:
        return f"<Jokey(id={self.id}, isim='{self.isim}')>"


class Mesafe(Base):
    """Mesafe tablosu."""

    __tablename__ = "mesafeler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metre = Column(Integer, unique=True, nullable=False)
    kategori = Column(String(50), nullable=False)  # sprint / kısa / orta / uzun

    yarislar = relationship("Yaris", back_populates="mesafe")

    def __repr__(self) -> str:
        return f"<Mesafe(id={self.id}, metre={self.metre}, kategori='{self.kategori}')>"


class Yaris(Base):
    """Yarış tablosu."""

    __tablename__ = "yarislar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tarih = Column(Date, nullable=False)
    hipodrom_id = Column(Integer, ForeignKey("hipodromlar.id"), nullable=False)
    mesafe_id = Column(Integer, ForeignKey("mesafeler.id"), nullable=True)
    kosu_no = Column(Integer, nullable=False)
    kosu_tipi = Column(String(50), nullable=True)
    zemin = Column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("tarih", "hipodrom_id", "kosu_no", name="uq_yaris_tarih_hipodrom_kosu"),
    )

    hipodrom = relationship("Hipodrom", back_populates="yarislar")
    mesafe = relationship("Mesafe", back_populates="yarislar")
    sonuclar = relationship("YarisSonucu", back_populates="yaris")

    def __repr__(self) -> str:
        return (
            f"<Yaris(id={self.id}, tarih={self.tarih}, "
            f"hipodrom_id={self.hipodrom_id}, kosu_no={self.kosu_no})>"
        )


class YarisSonucu(Base):
    """Yarış sonucu tablosu — her yarıştaki at-jokey girişi.

    Denormalize alanlar (tarih, hipodrom_id, kosu_no) sorgu kolaylığı için eklendi.
    """

    __tablename__ = "yaris_sonuclari"

    id = Column(Integer, primary_key=True, autoincrement=True)
    yaris_id = Column(Integer, ForeignKey("yarislar.id"), nullable=False)
    at_id = Column(Integer, ForeignKey("atlar.id"), nullable=False)
    jokey_id = Column(Integer, ForeignKey("jokeyler.id"), nullable=False)

    # Denormalize alanlar
    tarih = Column(Date, nullable=False)
    hipodrom_id = Column(Integer, ForeignKey("hipodromlar.id"), nullable=False)
    kosu_no = Column(Integer, nullable=False)

    # Yarış detayları
    kulvar = Column(Integer, nullable=True)
    siklet = Column(Float, nullable=True)
    siralama = Column(Integer, nullable=True)
    derece_sn = Column(Float, nullable=True)
    derece_str = Column(String(20), nullable=True)
    ganyan = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("yaris_id", "at_id", name="uq_sonuc_yaris_at"),
    )

    yaris = relationship("Yaris", back_populates="sonuclar")
    at = relationship("At", back_populates="sonuclar")
    jokey = relationship("Jokey", back_populates="sonuclar")
    hipodrom = relationship("Hipodrom", back_populates="sonuclar")

    def __repr__(self) -> str:
        return (
            f"<YarisSonucu(yaris_id={self.yaris_id}, at_id={self.at_id}, "
            f"siralama={self.siralama})>"
        )


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

    def get_or_create_at(self, session: Session, isim: str, irk: str | None = None) -> At:
        """Atı bul veya oluştur."""
        at = session.query(At).filter_by(isim=isim, irk=irk).first()
        if at is None:
            at = At(isim=isim, irk=irk)
            session.add(at)
            session.flush()
        return at

    def get_or_create_jokey(self, session: Session, isim: str) -> Jokey:
        """Jokeyi bul veya oluştur."""
        jokey = session.query(Jokey).filter_by(isim=isim).first()
        if jokey is None:
            jokey = Jokey(isim=isim)
            session.add(jokey)
            session.flush()
        return jokey

    def get_or_create_mesafe(self, session: Session, metre: int) -> Mesafe:
        """Mesafeyi bul veya oluştur."""
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
        tarih: date,
        hipodrom_id: int,
        kosu_no: int,
        mesafe_id: int | None = None,
        kosu_tipi: str | None = None,
        zemin: str | None = None,
    ) -> Yaris:
        """Yarışı bul veya oluştur."""
        yaris = (
            session.query(Yaris)
            .filter_by(tarih=tarih, hipodrom_id=hipodrom_id, kosu_no=kosu_no)
            .first()
        )
        if yaris is None:
            yaris = Yaris(
                tarih=tarih,
                hipodrom_id=hipodrom_id,
                kosu_no=kosu_no,
                mesafe_id=mesafe_id,
                kosu_tipi=kosu_tipi,
                zemin=zemin,
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
                    isim=str(row["at_ismi"]),
                    irk=irk,
                )

                # Jokey
                jokey = self.get_or_create_jokey(session, isim=str(row["jokey"]))

                # Mesafe
                mesafe_id = None
                if pd.notna(row.get("mesafe")) and int(row["mesafe"]) > 0:
                    mesafe_obj = self.get_or_create_mesafe(session, metre=int(row["mesafe"]))
                    mesafe_id = mesafe_obj.id

                # Yarış
                tarih = (
                    row["tarih"]
                    if isinstance(row["tarih"], date)
                    else datetime.fromisoformat(str(row["tarih"])).date()
                )
                yaris = self.get_or_create_yaris(
                    session,
                    tarih=tarih,
                    hipodrom_id=hipodrom.id,
                    kosu_no=int(row["kosu_no"]),
                    mesafe_id=mesafe_id,
                    kosu_tipi=str(row.get("kosu_tipi", "")) or None,
                    zemin=str(row.get("zemin", "")) or None,
                )

                # Sonuç (denormalize alanlar dahil)
                self.add_yaris_sonucu(
                    session,
                    yaris_id=yaris.id,
                    at_id=at.id,
                    jokey_id=jokey.id,
                    tarih=tarih,
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
                    At.isim,
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
                    "at": r.isim,
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
                    Jokey.isim,
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
                    "jokey": r.isim,
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
                .join(Yaris, Yaris.mesafe_id == Mesafe.id)
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
