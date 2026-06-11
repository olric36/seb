"""Yarış (yarislar) ve Hipodrom (hipodromlar) tabloları."""

from __future__ import annotations

from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from seb.base import Base


class Hipodrom(Base):
    """Hipodrom (yarış pisti) tablosu."""

    __tablename__ = "hipodromlar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tjk_id = Column(Integer, unique=True, nullable=False)
    isim = Column(String(100), nullable=False)
    sehir = Column(String(100), nullable=False)

    sonuclar = relationship("YarisSonucu", back_populates="hipodrom")

    def __repr__(self) -> str:
        return f"<Hipodrom(id={self.id}, isim='{self.isim}', sehir='{self.sehir}')>"


class Yaris(Base):
    """Yarış tablosu."""

    __tablename__ = "yarislar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    yartar = Column(Date, nullable=False)
    il = Column(String(100), nullable=True)
    pist = Column(String(100), nullable=True)
    kosuno = Column(Integer, nullable=False)
    irk = Column(String(50), nullable=True)  # İngiliz / Arap
    mesafe = Column(Integer, nullable=True)
    ortder = Column(Float, nullable=True)
    atsay = Column(Integer, nullable=True)
    pist_durumu = Column(String(50), nullable=True)
    opn = Column(Float, nullable=True)
    sapma = Column(Float, nullable=True)
    win = Column(String(200), nullable=True)
    lost = Column(String(200), nullable=True)

    __table_args__ = (
        UniqueConstraint("yartar", "il", "kosuno", name="uq_yaris_tarih_il_kosu"),
    )

    sonuclar = relationship("YarisSonucu", back_populates="yaris")

    def __repr__(self) -> str:
        return (
            f"<Yaris(id={self.id}, yartar={self.yartar}, "
            f"il='{self.il}', kosuno={self.kosuno})>"
        )
