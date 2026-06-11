"""Yarış sonucu (yaris_sonuclari) tablosu."""

from __future__ import annotations

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from seb.base import Base


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
    siklet = Column(Float, nullable=True)
    siralama = Column(Integer, nullable=True)
    derece_sn = Column(Float, nullable=True)
    derece_str = Column(String(20), nullable=True)
    skos = Column(Float, nullable=True)
    hesder = Column(Float, nullable=True)
    reel = Column(Float, nullable=True)
    uyder = Column(Float, nullable=True)

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
