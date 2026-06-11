"""At (atlar) tablosu."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from seb.base import Base


class At(Base):
    """At tablosu."""

    __tablename__ = "atlar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad = Column(String(200), nullable=False)
    irk = Column(String(50), nullable=True)  # "İngiliz" veya "Arap"
    yaris_sayisi = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("ad", "irk", name="uq_at_ad_irk"),)

    sonuclar = relationship("YarisSonucu", back_populates="at")

    def __repr__(self) -> str:
        return f"<At(id={self.id}, ad='{self.ad}', irk='{self.irk}')>"
