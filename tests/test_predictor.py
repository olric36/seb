"""predictor.py modülü için unit testler."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from seb.predictor import HorseRacingPredictor


@pytest.fixture
def sample_data():
    """Eğitim için örnek veri seti oluştur."""
    np.random.seed(42)
    n = 100
    X = pd.DataFrame(
        {
            "horse_age": np.random.randint(2, 8, n).astype(float),
            "horse_weight": np.random.uniform(50, 60, n),
            "horse_win_rate": np.random.uniform(0, 0.5, n),
            "jockey_win_rate": np.random.uniform(0, 0.4, n),
            "odds": np.random.uniform(1.5, 50, n),
            "distance": np.random.choice([1000, 1200, 1600, 2000], n).astype(float),
        }
    )
    y = pd.Series(np.random.choice([0, 1], n, p=[0.8, 0.2]), name="is_winner")
    return X, y


@pytest.fixture
def fitted_predictor(sample_data):
    X, y = sample_data
    predictor = HorseRacingPredictor(n_estimators=10, random_state=42)
    predictor.fit(X, y)
    return predictor


class TestHorseRacingPredictor:
    def test_init(self):
        predictor = HorseRacingPredictor(n_estimators=50, max_depth=5)
        assert predictor.n_estimators == 50
        assert predictor.max_depth == 5
        assert predictor.is_fitted is False

    def test_fit(self, sample_data):
        X, y = sample_data
        predictor = HorseRacingPredictor(n_estimators=10)
        result = predictor.fit(X, y)
        assert predictor.is_fitted is True
        assert result is predictor  # fluent interface

    def test_fit_empty_data(self):
        predictor = HorseRacingPredictor()
        with pytest.raises(ValueError, match="boş"):
            predictor.fit(pd.DataFrame(), pd.Series(dtype=int))

    def test_fit_single_class(self):
        X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        y = pd.Series([0, 0, 0])
        predictor = HorseRacingPredictor()
        with pytest.raises(ValueError, match="sınıf"):
            predictor.fit(X, y)

    def test_fit_mismatched_lengths(self):
        X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        y = pd.Series([0, 1])
        predictor = HorseRacingPredictor()
        with pytest.raises(ValueError, match="eşleşmiyor"):
            predictor.fit(X, y)

    def test_predict(self, fitted_predictor, sample_data):
        X, _ = sample_data
        predictions = fitted_predictor.predict(X)
        assert len(predictions) == len(X)
        assert set(predictions).issubset({0, 1})

    def test_predict_proba(self, fitted_predictor, sample_data):
        X, _ = sample_data
        probas = fitted_predictor.predict_proba(X)
        assert probas.shape == (len(X), 2)
        assert np.allclose(probas.sum(axis=1), 1.0)

    def test_predict_not_fitted(self, sample_data):
        X, _ = sample_data
        predictor = HorseRacingPredictor()
        with pytest.raises(RuntimeError, match="eğitilmedi"):
            predictor.predict(X)

    def test_feature_importances(self, fitted_predictor):
        importances = fitted_predictor.feature_importances()
        assert isinstance(importances, dict)
        assert len(importances) == 6
        assert all(v >= 0 for v in importances.values())

    def test_feature_names(self, fitted_predictor):
        names = fitted_predictor.feature_names
        assert "horse_age" in names
        assert "odds" in names

    def test_save_and_load(self, fitted_predictor, sample_data, tmp_path):
        X, _ = sample_data
        model_path = tmp_path / "model.joblib"

        fitted_predictor.save(model_path)
        assert model_path.exists()

        loaded = HorseRacingPredictor.load(model_path)
        assert loaded.is_fitted is True

        # Aynı tahminleri üretmeli
        orig_preds = fitted_predictor.predict(X)
        loaded_preds = loaded.predict(X)
        np.testing.assert_array_equal(orig_preds, loaded_preds)

    def test_load_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HorseRacingPredictor.load(tmp_path / "nonexistent.joblib")

    def test_predict_missing_features(self, fitted_predictor):
        X = pd.DataFrame({"horse_age": [3.0], "odds": [5.0]})
        with pytest.raises(ValueError, match="Eksik"):
            fitted_predictor.predict(X)

    def test_evaluate(self, sample_data):
        X, y = sample_data
        predictor = HorseRacingPredictor(n_estimators=10)
        metrics = predictor.evaluate(X, y, cv=3)
        assert "accuracy_mean" in metrics
        assert "precision_mean" in metrics
        assert "recall_mean" in metrics
        assert 0 <= metrics["accuracy_mean"] <= 1
