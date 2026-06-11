"""Mesafe (mesafeler) tablosu."""

from __future__ import annotations

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from seb.base import Base


class Mesafe(Base):
    """Mesafe tablosu."""

    __tablename__ = "mesafeler"

    id = Column(Integer, primary_key=True, autoincrement=True)
    il = Column(String(100), nullable=True)
    irk = Column(String(50), nullable=True)  # İngiliz / Arap
    pist = Column(String(100), nullable=True)
    mesafe = Column(Integer, nullable=False)
    yarsay = Column(Integer, default=0)
    ortder = Column(Float, nullable=True)
    s100 = Column(Float, nullable=True)
    nmesafe = Column(Float, nullable=True)
    vc = Column(Float, nullable=True)
    win = Column(Float, nullable=True)
    lost = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("il", "irk", "pist", "mesafe", name="uq_mesafe_il_irk_pist_mesafe"),
    )

    def __repr__(self) -> str:
        return f"<Mesafe(id={self.id}, il='{self.il}', mesafe={self.mesafe})>"
