#!/usr/bin/env python3
"""Train a few match-score regressors on the generated resume/job dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS: List[str] = [
    "jaccard_similarity",
    "tfidf_cosine",
    "embedding_cosine",
    "job_skill_coverage",
    "avg_max_skill_similarity",
]
TARGET_COLUMN = "aggregated_target"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train regression models for resume-job match scoring."
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to training_dataset.csv",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of rows to reserve for test split (default: 0.2)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Ridge regularization strength (default: 1.0)",
    )
    parser.add_argument(
        "--use-mlp",
        action="store_true",
        help="Also train a small neural net regressor.",
    )
    parser.add_argument(
        "--save-metrics",
        default=None,
        help="Optional path to save metrics as JSON.",
    )
    return parser.parse_args()


def validate_columns(df: pd.DataFrame) -> None:
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    validate_columns(df)
    return df


def metric_bundle(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    return {"rmse": rmse, "mae": mae, "r2": r2}


def print_dataset_summary(df: pd.DataFrame) -> None:
    print("=" * 72)
    print("DATASET SUMMARY")
    print("=" * 72)
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print("\nNull counts for modeling columns:")
    print(df[FEATURE_COLUMNS + [TARGET_COLUMN]].isnull().sum().to_string())
    print("\nDescriptive stats:")
    print(df[FEATURE_COLUMNS + [TARGET_COLUMN]].describe().round(4).to_string())
    print("\nCorrelation matrix:")
    print(df[FEATURE_COLUMNS + [TARGET_COLUMN]].corr().round(4).to_string())
    print()


def build_ridge_model(alpha: float) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=alpha)),
        ]
    )


def build_gbr_model() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
            (
                "model",
                GradientBoostingRegressor(
                    random_state=42,
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=3,
                ),
            ),
        ]
    )


def build_mlp_model(random_state: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
            ("scaler", StandardScaler()),
            (
                "model",
                MLPRegressor(
                    hidden_layer_sizes=(16, 8),
                    activation="relu",
                    solver="adam",
                    alpha=1e-4,
                    batch_size="auto",
                    learning_rate_init=1e-3,
                    max_iter=1000,
                    early_stopping=True,
                    validation_fraction=0.1,
                    n_iter_no_change=25,
                    random_state=random_state,
                ),
            ),
        ]
    )


def train_and_evaluate_models(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    ridge_alpha: float,
    random_state: int,
    use_mlp: bool,
) -> Tuple[Dict[str, Dict[str, float]], Pipeline]:
    metrics: Dict[str, Dict[str, float]] = {}

    ridge = build_ridge_model(ridge_alpha)
    ridge.fit(X_train, y_train)
    ridge_preds = ridge.predict(X_test)
    metrics["ridge"] = metric_bundle(y_test.to_numpy(), ridge_preds)

    gbr = build_gbr_model()
    gbr.fit(X_train, y_train)
    gbr_preds = gbr.predict(X_test)
    metrics["gradient_boosting"] = metric_bundle(y_test.to_numpy(), gbr_preds)

    if use_mlp:
        mlp = build_mlp_model(random_state)
        mlp.fit(X_train, y_train)
        mlp_preds = mlp.predict(X_test)
        metrics["mlp"] = metric_bundle(y_test.to_numpy(), mlp_preds)

    return metrics, ridge


def print_metrics(metrics: Dict[str, Dict[str, float]]) -> None:
    print("=" * 72)
    print("MODEL COMPARISON")
    print("=" * 72)
    rows = []
    for model_name, vals in metrics.items():
        rows.append(
            {
                "model": model_name,
                "rmse": vals["rmse"],
                "mae": vals["mae"],
                "r2": vals["r2"],
            }
        )
    metrics_df = pd.DataFrame(rows).sort_values(by=["rmse", "mae"], ascending=True)
    print(metrics_df.round(6).to_string(index=False))
    print()


def main() -> None:
    args = parse_args()
    df = load_dataset(args.data)

    print_dataset_summary(df)

    # compare full features against smaller feature sets
    experiment_configs = {
        "full_features": FEATURE_COLUMNS,
        "minus_embedding_cosine": [
            col for col in FEATURE_COLUMNS if col != "embedding_cosine"
        ],
        "minus_embedding_and_tfidf": [
            col for col in FEATURE_COLUMNS if col not in {"embedding_cosine", "tfidf_cosine"}
        ],
    }

    all_experiment_metrics = {}

    for experiment_name, feature_cols in experiment_configs.items():
        print("=" * 72)
        print(f"EXPERIMENT: {experiment_name}")
        print("=" * 72)
        print("Features:", feature_cols)
        print()

        X = df[feature_cols].copy()
        y = df[TARGET_COLUMN].copy()

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=args.test_size,
            random_state=args.random_state,
        )

        # use each raw feature as a simple baseline score
        baseline_metrics = {}
        for col in feature_cols:
            preds = X_test[col].fillna(0.0).to_numpy()
            baseline_metrics[f"baseline_{col}"] = metric_bundle(
                y_test.to_numpy(), preds
            )

        model_metrics, ridge_pipeline = train_and_evaluate_models(
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            ridge_alpha=args.alpha,
            random_state=args.random_state,
            use_mlp=args.use_mlp,
        )

        experiment_metrics = {**baseline_metrics, **model_metrics}
        all_experiment_metrics[experiment_name] = experiment_metrics

        print_metrics(experiment_metrics)

        # ridge coefficients show which inputs moved the score most
        ridge_model: Ridge = ridge_pipeline.named_steps["model"]
        print("=" * 72)
        print(f"RIDGE COEFFICIENTS: {experiment_name}")
        print("=" * 72)
        coef_df = pd.DataFrame(
            {
                "feature": feature_cols,
                "coefficient": ridge_model.coef_,
            }
        ).sort_values(by="coefficient", ascending=False)
        print(coef_df.round(6).to_string(index=False))
        print(f"\nIntercept: {ridge_model.intercept_:.6f}")
        print()

    if args.save_metrics:
        out_path = Path(args.save_metrics)
        out_path.write_text(json.dumps(all_experiment_metrics, indent=2))
        print(f"Saved metrics to: {args.save_metrics}")


if __name__ == "__main__":
    main()
