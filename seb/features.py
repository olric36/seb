"""Özellik mühendisliği — yarış verilerinden ML özellikleri çıkarma."""

from __future__ import annotations

import pandas as pd

from seb.models import Race, RaceEntry, Surface, TrackCondition


def entry_to_features(entry: RaceEntry, race: Race) -> dict[str, float]:
    """Tek bir yarış girişini özellik sözlüğüne dönüştür."""
    features: dict[str, float] = {}

    # At özellikleri
    features["horse_age"] = float(entry.horse.age)
    features["horse_weight"] = entry.horse.weight
    features["horse_win_rate"] = entry.horse.win_rate
    features["horse_career_races"] = float(entry.horse.career_races)
    features["horse_career_wins"] = float(entry.horse.career_wins)

    # Jokey özellikleri
    features["jockey_experience_years"] = float(entry.jockey.experience_years)
    features["jockey_win_rate"] = entry.jockey.win_rate
    features["jockey_total_races"] = float(entry.jockey.total_races)
    features["jockey_total_wins"] = float(entry.jockey.total_wins)

    # Yarış özellikleri
    features["post_position"] = float(entry.post_position)
    features["odds"] = entry.odds
    features["distance_meters"] = float(race.distance_meters)
    features["num_runners"] = float(race.num_runners)
    features["prize_money"] = race.prize_money

    # Pist durumu (one-hot encoding)
    for condition in TrackCondition:
        features[f"track_{condition.value}"] = 1.0 if race.track_condition == condition else 0.0

    # Pist yüzeyi (one-hot encoding)
    for surface in Surface:
        features[f"surface_{surface.value}"] = 1.0 if race.surface == surface else 0.0

    return features


def build_feature_matrix(races: list[Race]) -> tuple[pd.DataFrame, pd.Series]:
    """Yarış listesinden özellik matrisi ve hedef değişken oluştur.

    Returns:
        (X, y): Özellik DataFrame'i ve kazanan/kaybeden binary serisi.
    """
    rows: list[dict[str, float]] = []
    labels: list[int] = []

    for race in races:
        for entry in race.entries:
            if entry.finish_position is None:
                continue
            features = entry_to_features(entry, race)
            rows.append(features)
            labels.append(1 if entry.is_winner else 0)

    if not rows:
        return pd.DataFrame(), pd.Series(dtype=int)

    X = pd.DataFrame(rows)
    y = pd.Series(labels, name="is_winner")

    return X, y


def compute_horse_stats(races: list[Race]) -> pd.DataFrame:
    """Tüm yarışlardan at bazlı istatistik tablosu oluştur."""
    stats: dict[int, dict[str, object]] = {}

    for race in races:
        for entry in race.entries:
            hid = entry.horse.horse_id
            if hid not in stats:
                stats[hid] = {
                    "horse_id": hid,
                    "horse_name": entry.horse.name,
                    "races": 0,
                    "wins": 0,
                    "places": 0,
                    "total_odds": 0.0,
                }

            record = stats[hid]
            record["races"] = int(record["races"]) + 1
            record["total_odds"] = float(record["total_odds"]) + entry.odds

            if entry.finish_position is not None:
                if entry.finish_position == 1:
                    record["wins"] = int(record["wins"]) + 1
                if entry.finish_position <= 3:
                    record["places"] = int(record["places"]) + 1

    if not stats:
        return pd.DataFrame()

    df = pd.DataFrame(stats.values())
    df["win_rate"] = df["wins"] / df["races"]
    df["place_rate"] = df["places"] / df["races"]
    df["avg_odds"] = df["total_odds"] / df["races"]

    return df.sort_values("win_rate", ascending=False).reset_index(drop=True)


def compute_jockey_stats(races: list[Race]) -> pd.DataFrame:
    """Tüm yarışlardan jokey bazlı istatistik tablosu oluştur."""
    stats: dict[int, dict[str, object]] = {}

    for race in races:
        for entry in race.entries:
            jid = entry.jockey.jockey_id
            if jid not in stats:
                stats[jid] = {
                    "jockey_id": jid,
                    "jockey_name": entry.jockey.name,
                    "races": 0,
                    "wins": 0,
                    "places": 0,
                }

            record = stats[jid]
            record["races"] = int(record["races"]) + 1

            if entry.finish_position is not None:
                if entry.finish_position == 1:
                    record["wins"] = int(record["wins"]) + 1
                if entry.finish_position <= 3:
                    record["places"] = int(record["places"]) + 1

    if not stats:
        return pd.DataFrame()

    df = pd.DataFrame(stats.values())
    df["win_rate"] = df["wins"] / df["races"]
    df["place_rate"] = df["places"] / df["races"]

    return df.sort_values("win_rate", ascending=False).reset_index(drop=True)


def normalize_features(X: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalizasyon uygula."""
    if X.empty:
        return X

    result = X.copy()
    for col in result.columns:
        col_min = result[col].min()
        col_max = result[col].max()
        if col_max - col_min > 0:
            result[col] = (result[col] - col_min) / (col_max - col_min)
        else:
            result[col] = 0.0

    return result
