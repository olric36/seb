"""Yarış (yarislar) ve Hipodrom (hipodromlar) tabloları."""

from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from seb.base import Base


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
