"""Jokey (jokeyler) tablosu."""

from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import relationship

from seb.base import Base


class Jokey(Base):
    """Jokey tablosu."""

    __tablename__ = "jokeyler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ad = Column(String(200), unique=True, nullable=False)
    ortsap = Column(Float, default=0.0)
    yarsay = Column(Integer, default=0)

    sonuclar = relationship("YarisSonucu", back_populates="jokey")

    def __repr__(self) -> str:
        return f"<Jokey(id={self.id}, ad='{self.ad}')>"
