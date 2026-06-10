"""CSV dosyalarından yarış verisi yükleme ve doğrulama."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from seb.models import (
    Horse,
    Jockey,
    Race,
    RaceEntry,
    Surface,
    TrackCondition,
)

REQUIRED_COLUMNS = [
    "race_id",
    "race_name",
    "distance_meters",
    "track_condition",
    "surface",
    "prize_money",
    "horse_id",
    "horse_name",
    "horse_age",
    "horse_weight",
    "horse_career_wins",
    "horse_career_races",
    "jockey_id",
    "jockey_name",
    "jockey_experience_years",
    "jockey_total_wins",
    "jockey_total_races",
    "post_position",
    "odds",
    "finish_position",
]


def validate_columns(df: pd.DataFrame) -> list[str]:
    """Gerekli sütunların varlığını kontrol et."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return [f"Eksik sütun: {col}" for col in missing]


def validate_data_types(df: pd.DataFrame) -> list[str]:
    """Veri tiplerini kontrol et."""
    errors: list[str] = []

    numeric_cols = [
        "race_id",
        "distance_meters",
        "prize_money",
        "horse_id",
        "horse_age",
        "horse_weight",
        "horse_career_wins",
        "horse_career_races",
        "jockey_id",
        "jockey_experience_years",
        "jockey_total_wins",
        "jockey_total_races",
        "post_position",
        "odds",
    ]

    for col in numeric_cols:
        if col in df.columns:
            non_numeric = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
            if non_numeric.any():
                bad_rows = list(non_numeric[non_numeric].index[:3])
                errors.append(f"'{col}' sütununda sayısal olmayan değerler (satırlar: {bad_rows})")

    valid_conditions = {e.value for e in TrackCondition}
    if "track_condition" in df.columns:
        invalid = df[~df["track_condition"].isin(valid_conditions)]["track_condition"].unique()
        if len(invalid) > 0:
            errors.append(
                f"Geçersiz pist durumu: {list(invalid)}. "
                f"Geçerli değerler: {sorted(valid_conditions)}"
            )

    valid_surfaces = {e.value for e in Surface}
    if "surface" in df.columns:
        invalid = df[~df["surface"].isin(valid_surfaces)]["surface"].unique()
        if len(invalid) > 0:
            errors.append(
                f"Geçersiz pist yüzeyi: {list(invalid)}. "
                f"Geçerli değerler: {sorted(valid_surfaces)}"
            )

    return errors


def parse_races(df: pd.DataFrame) -> list[Race]:
    """DataFrame'den Race nesneleri oluştur."""
    races: list[Race] = []

    for race_id, group in df.groupby("race_id"):
        first_row = group.iloc[0]

        entries: list[RaceEntry] = []
        for _, row in group.iterrows():
            horse = Horse(
                horse_id=int(row["horse_id"]),
                name=str(row["horse_name"]),
                age=int(row["horse_age"]),
                weight=float(row["horse_weight"]),
                career_wins=int(row["horse_career_wins"]),
                career_races=int(row["horse_career_races"]),
            )
            jockey = Jockey(
                jockey_id=int(row["jockey_id"]),
                name=str(row["jockey_name"]),
                experience_years=int(row["jockey_experience_years"]),
                total_wins=int(row["jockey_total_wins"]),
                total_races=int(row["jockey_total_races"]),
            )

            finish_pos = row["finish_position"]
            finish_position = None if pd.isna(finish_pos) else int(finish_pos)

            entry = RaceEntry(
                horse=horse,
                jockey=jockey,
                post_position=int(row["post_position"]),
                odds=float(row["odds"]),
                finish_position=finish_position,
            )
            entries.append(entry)

        race = Race(
            race_id=int(race_id),
            name=str(first_row["race_name"]),
            distance_meters=int(first_row["distance_meters"]),
            track_condition=TrackCondition(str(first_row["track_condition"])),
            surface=Surface(str(first_row["surface"])),
            prize_money=float(first_row["prize_money"]),
            entries=entries,
        )
        races.append(race)

    return races


def load_race_data(filepath: str | Path) -> list[Race]:
    """CSV dosyasından yarış verilerini yükle ve doğrula."""
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {filepath}")

    if not filepath.suffix.lower() == ".csv":
        raise ValueError(f"Sadece CSV dosyaları desteklenir, verilen: {filepath.suffix}")

    df = pd.read_csv(filepath)

    if df.empty:
        raise ValueError("CSV dosyası boş")

    col_errors = validate_columns(df)
    if col_errors:
        raise ValueError(f"Sütun doğrulama hatası: {'; '.join(col_errors)}")

    type_errors = validate_data_types(df)
    if type_errors:
        raise ValueError(f"Veri tipi hatası: {'; '.join(type_errors)}")

    return parse_races(df)
