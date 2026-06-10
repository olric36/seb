"""models.py modülü için unit testler."""

from __future__ import annotations

import pytest

from seb.models import (
    Horse,
    Jockey,
    Race,
    RaceEntry,
    Surface,
    TrackCondition,
)


class TestHorse:
    def test_win_rate_with_races(self):
        horse = Horse(horse_id=1, name="STORM", age=3, weight=57.0, career_wins=5, career_races=20)
        assert horse.win_rate == pytest.approx(0.25)

    def test_win_rate_no_races(self):
        horse = Horse(horse_id=1, name="NEWBIE", age=2, weight=55.0)
        assert horse.win_rate == 0.0

    def test_validate_valid_horse(self):
        horse = Horse(horse_id=1, name="OK", age=3, weight=57.0, career_wins=2, career_races=5)
        assert horse.validate() == []

    def test_validate_young_age(self):
        horse = Horse(horse_id=1, name="BABY", age=1, weight=50.0)
        errors = horse.validate()
        assert len(errors) == 1
        assert "yaş" in errors[0].lower() or "2" in errors[0]

    def test_validate_negative_weight(self):
        horse = Horse(horse_id=1, name="BAD", age=3, weight=-1.0)
        errors = horse.validate()
        assert any("ağırlık" in e.lower() or "pozitif" in e.lower() for e in errors)

    def test_validate_wins_exceed_races(self):
        horse = Horse(horse_id=1, name="BAD", age=3, weight=57.0, career_wins=10, career_races=5)
        errors = horse.validate()
        assert len(errors) > 0


class TestJockey:
    def test_win_rate(self):
        jockey = Jockey(
            jockey_id=1, name="A.CELIK", experience_years=10,
            total_wins=100, total_races=500,
        )
        assert jockey.win_rate == pytest.approx(0.2)

    def test_win_rate_no_races(self):
        jockey = Jockey(jockey_id=1, name="ROOKIE", experience_years=0)
        assert jockey.win_rate == 0.0

    def test_validate_valid(self):
        jockey = Jockey(jockey_id=1, name="OK", experience_years=5, total_wins=10, total_races=50)
        assert jockey.validate() == []

    def test_validate_negative_experience(self):
        jockey = Jockey(jockey_id=1, name="BAD", experience_years=-1)
        errors = jockey.validate()
        assert len(errors) > 0


class TestRaceEntry:
    def test_is_winner_true(self):
        horse = Horse(horse_id=1, name="WINNER", age=3, weight=57.0)
        jockey = Jockey(jockey_id=1, name="JOKEY", experience_years=5)
        entry = RaceEntry(horse=horse, jockey=jockey, post_position=1, odds=3.5, finish_position=1)
        assert entry.is_winner is True

    def test_is_winner_false(self):
        horse = Horse(horse_id=1, name="LOSER", age=3, weight=57.0)
        jockey = Jockey(jockey_id=1, name="JOKEY", experience_years=5)
        entry = RaceEntry(horse=horse, jockey=jockey, post_position=2, odds=10.0, finish_position=3)
        assert entry.is_winner is False

    def test_no_finish(self):
        horse = Horse(horse_id=1, name="DNF", age=3, weight=57.0)
        jockey = Jockey(jockey_id=1, name="JOKEY", experience_years=5)
        entry = RaceEntry(horse=horse, jockey=jockey, post_position=1, odds=5.0)
        assert entry.is_winner is False


class TestRace:
    def _make_race(self, num_entries=3, with_results=True):
        entries = []
        for i in range(num_entries):
            horse = Horse(horse_id=i + 1, name=f"HORSE_{i}", age=3, weight=57.0)
            jockey = Jockey(jockey_id=i + 1, name=f"JOCKEY_{i}", experience_years=5)
            finish = (i + 1) if with_results else None
            entry = RaceEntry(
                horse=horse, jockey=jockey, post_position=i + 1,
                odds=float(i + 2), finish_position=finish,
            )
            entries.append(entry)
        return Race(
            race_id=1, name="Test Koşusu", distance_meters=1200,
            track_condition=TrackCondition.GOOD, surface=Surface.TURF,
            prize_money=50000.0, entries=entries,
        )

    def test_num_runners(self):
        race = self._make_race(num_entries=5)
        assert race.num_runners == 5

    def test_winner(self):
        race = self._make_race()
        winner = race.winner
        assert winner is not None
        assert winner.horse.name == "HORSE_0"

    def test_no_winner(self):
        race = self._make_race(with_results=False)
        assert race.winner is None

    def test_validate_valid(self):
        race = self._make_race()
        assert race.validate() == []

    def test_validate_too_few_entries(self):
        race = self._make_race(num_entries=1)
        errors = race.validate()
        assert any("en az 2" in e.lower() or "2" in e for e in errors)

    def test_validate_negative_distance(self):
        race = self._make_race()
        race.distance_meters = -100
        errors = race.validate()
        assert len(errors) > 0


class TestEnums:
    def test_track_conditions(self):
        assert TrackCondition.FIRM.value == "firm"
        assert TrackCondition.GOOD.value == "good"
        assert TrackCondition.SOFT.value == "soft"
        assert TrackCondition.HEAVY.value == "heavy"

    def test_surfaces(self):
        assert Surface.TURF.value == "turf"
        assert Surface.DIRT.value == "dirt"
        assert Surface.SYNTHETIC.value == "synthetic"
