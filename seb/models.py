"""At yarışı veri modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TrackCondition(Enum):
    """Pist durumu."""

    FIRM = "firm"
    GOOD = "good"
    SOFT = "soft"
    HEAVY = "heavy"


class Surface(Enum):
    """Pist yüzeyi."""

    TURF = "turf"
    DIRT = "dirt"
    SYNTHETIC = "synthetic"


@dataclass
class Horse:
    """At bilgisi."""

    horse_id: int
    name: str
    age: int
    weight: float
    career_wins: int = 0
    career_races: int = 0

    @property
    def win_rate(self) -> float:
        if self.career_races == 0:
            return 0.0
        return self.career_wins / self.career_races

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.age < 2:
            errors.append(f"At yaşı 2'den küçük olamaz: {self.age}")
        if self.weight <= 0:
            errors.append(f"At ağırlığı pozitif olmalı: {self.weight}")
        if self.career_wins < 0:
            errors.append(f"Kariyer galibiyeti negatif olamaz: {self.career_wins}")
        if self.career_races < 0:
            errors.append(f"Kariyer yarış sayısı negatif olamaz: {self.career_races}")
        if self.career_wins > self.career_races:
            errors.append(
                f"Galibiyet sayısı ({self.career_wins}) "
                f"yarış sayısından ({self.career_races}) fazla olamaz"
            )
        return errors


@dataclass
class Jockey:
    """Jokey bilgisi."""

    jockey_id: int
    name: str
    experience_years: int
    total_wins: int = 0
    total_races: int = 0

    @property
    def win_rate(self) -> float:
        if self.total_races == 0:
            return 0.0
        return self.total_wins / self.total_races

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.experience_years < 0:
            errors.append(f"Deneyim yılı negatif olamaz: {self.experience_years}")
        if self.total_wins < 0:
            errors.append(f"Toplam galibiyet negatif olamaz: {self.total_wins}")
        if self.total_races < 0:
            errors.append(f"Toplam yarış sayısı negatif olamaz: {self.total_races}")
        if self.total_wins > self.total_races:
            errors.append(
                f"Galibiyet sayısı ({self.total_wins}) "
                f"yarış sayısından ({self.total_races}) fazla olamaz"
            )
        return errors


@dataclass
class RaceEntry:
    """Bir yarıştaki at-jokey girişi."""

    horse: Horse
    jockey: Jockey
    post_position: int
    odds: float
    finish_position: int | None = None

    @property
    def is_winner(self) -> bool:
        return self.finish_position == 1


@dataclass
class Race:
    """Yarış bilgisi."""

    race_id: int
    name: str
    distance_meters: int
    track_condition: TrackCondition
    surface: Surface
    prize_money: float
    entries: list[RaceEntry] = field(default_factory=list)

    @property
    def num_runners(self) -> int:
        return len(self.entries)

    @property
    def winner(self) -> RaceEntry | None:
        for entry in self.entries:
            if entry.is_winner:
                return entry
        return None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.distance_meters <= 0:
            errors.append(f"Mesafe pozitif olmalı: {self.distance_meters}")
        if self.prize_money < 0:
            errors.append(f"Ödül miktarı negatif olamaz: {self.prize_money}")
        if len(self.entries) < 2:
            errors.append(f"Yarışta en az 2 at olmalı, mevcut: {len(self.entries)}")

        post_positions = [e.post_position for e in self.entries]
        if len(post_positions) != len(set(post_positions)):
            errors.append("Kulvar numaraları benzersiz olmalı")

        finish_positions = [
            e.finish_position for e in self.entries if e.finish_position is not None
        ]
        if finish_positions and len(finish_positions) != len(set(finish_positions)):
            errors.append("Bitiş sıraları benzersiz olmalı")

        return errors
