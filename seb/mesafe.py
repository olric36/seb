"""Mesafe (mesafeler) tablosu."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from seb.base import Base

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


class Mesafe(Base):
    """Mesafe tablosu."""

    __tablename__ = "mesafeler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metre = Column(Integer, unique=True, nullable=False)
    kategori = Column(String(50), nullable=False)  # sprint / kısa / orta / uzun

    yarislar = relationship("Yaris", back_populates="mesafe")

    def __repr__(self) -> str:
        return f"<Mesafe(id={self.id}, metre={self.metre}, kategori='{self.kategori}')>"
