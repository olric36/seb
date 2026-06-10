"""Makine öğrenmesi ile at yarışı tahmini."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler


class HorseRacingPredictor:
    """Random Forest tabanlı at yarışı tahmin modeli."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int | None = 10,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state

        self._model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            class_weight="balanced",
        )
        self._scaler = StandardScaler()
        self._is_fitted = False
        self._feature_names: list[str] = []

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names.copy()

    def fit(self, X: pd.DataFrame, y: pd.Series) -> HorseRacingPredictor:
        """Modeli eğit."""
        if X.empty or y.empty:
            raise ValueError("Eğitim verisi boş olamaz")
        if len(X) != len(y):
            raise ValueError(
                f"X ve y uzunlukları eşleşmiyor: {len(X)} != {len(y)}"
            )
        if y.nunique() < 2:
            raise ValueError("Hedef değişkende en az 2 farklı sınıf olmalı")

        self._feature_names = list(X.columns)
        X_scaled = self._scaler.fit_transform(X)
        self._model.fit(X_scaled, y)
        self._is_fitted = True

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Tahmin yap (0 veya 1)."""
        self._check_fitted()
        self._check_features(X)

        X_scaled = self._scaler.transform(X)
        return self._model.predict(X_scaled)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Kazanma olasılıklarını döndür."""
        self._check_fitted()
        self._check_features(X)

        X_scaled = self._scaler.transform(X)
        return self._model.predict_proba(X_scaled)

    def evaluate(self, X: pd.DataFrame, y: pd.Series, cv: int = 5) -> dict[str, float]:
        """Çapraz doğrulama ile model performansını değerlendir."""
        if X.empty or y.empty:
            raise ValueError("Değerlendirme verisi boş olamaz")

        X_scaled = self._scaler.fit_transform(X)

        accuracy_scores = cross_val_score(self._model, X_scaled, y, cv=cv, scoring="accuracy")
        precision_scores = cross_val_score(self._model, X_scaled, y, cv=cv, scoring="precision")
        recall_scores = cross_val_score(self._model, X_scaled, y, cv=cv, scoring="recall")

        return {
            "accuracy_mean": float(accuracy_scores.mean()),
            "accuracy_std": float(accuracy_scores.std()),
            "precision_mean": float(precision_scores.mean()),
            "precision_std": float(precision_scores.std()),
            "recall_mean": float(recall_scores.mean()),
            "recall_std": float(recall_scores.std()),
        }

    def feature_importances(self) -> dict[str, float]:
        """Özellik önem sıralamasını döndür."""
        self._check_fitted()

        importances = self._model.feature_importances_
        return dict(
            sorted(
                zip(self._feature_names, importances),
                key=lambda x: x[1],
                reverse=True,
            )
        )

    def save(self, filepath: str | Path) -> None:
        """Modeli dosyaya kaydet."""
        self._check_fitted()
        filepath = Path(filepath)

        data = {
            "model": self._model,
            "scaler": self._scaler,
            "feature_names": self._feature_names,
            "params": {
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "random_state": self.random_state,
            },
        }
        joblib.dump(data, filepath)

    @classmethod
    def load(cls, filepath: str | Path) -> HorseRacingPredictor:
        """Kaydedilmiş modeli yükle."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Model dosyası bulunamadı: {filepath}")

        data = joblib.load(filepath)

        predictor = cls(**data["params"])
        predictor._model = data["model"]
        predictor._scaler = data["scaler"]
        predictor._feature_names = data["feature_names"]
        predictor._is_fitted = True

        return predictor

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError("Model henüz eğitilmedi. Önce fit() çağırın.")

    def _check_features(self, X: pd.DataFrame) -> None:
        missing = set(self._feature_names) - set(X.columns)
        if missing:
            raise ValueError(f"Eksik özellikler: {missing}")
