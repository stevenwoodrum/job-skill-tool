import argparse
import json
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor

FEATURES_ALL = [
    "jaccard_similarity",
    "tfidf_cosine",
    "embedding_cosine",
    "job_skill_coverage",
    "avg_max_skill_similarity",
]

FEATURE_SETS: Dict[str, List[str]] = {
    "minus_embedding": [
        "jaccard_similarity",
        "tfidf_cosine",
        "job_skill_coverage",
        "avg_max_skill_similarity",
    ],
    "minus_tfidf": [
        "jaccard_similarity",
        "embedding_cosine",
        "job_skill_coverage",
        "avg_max_skill_similarity",
    ],
    "minus_tfidf_embedding": [
        "jaccard_similarity",
        "job_skill_coverage",
        "avg_max_skill_similarity",
    ],
}

BASELINE_METRICS = [
    "jaccard_similarity",
    "tfidf_cosine",
    "embedding_cosine",
    "job_skill_coverage",
    "avg_max_skill_similarity",
]

TARGET = "aggregated_target"


def build_regressor(name: str):
    name = name.lower()
    if name == "ridge":
        return Ridge(alpha=1.0)
    if name == "gradient_boosting":
        return GradientBoostingRegressor(random_state=42)
    if name == "mlp":
        return MLPRegressor(
            hidden_layer_sizes=(32, 16),
            max_iter=2000,
            random_state=42,
        )
    raise ValueError(f"Unsupported regressor: {name}")


def build_classifier(name: str):
    name = name.lower()
    if name == "logistic":
        return LogisticRegression(max_iter=2000, random_state=42)
    if name == "gradient_boosting":
        return GradientBoostingClassifier(random_state=42)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=300, random_state=42)
    raise ValueError(f"Unsupported classifier: {name}")


def get_variants() -> Dict[str, List[str]]:
    variants = dict(FEATURE_SETS)
    variants.update({f"baseline_{metric}": [metric] for metric in BASELINE_METRICS})
    return variants


def validate_columns(df: pd.DataFrame) -> None:
    required = ["resume_id", "job_id"] + FEATURES_ALL + [TARGET]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def parse_bool(value: str) -> bool:
    value = value.lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("Expected true or false.")


def train_test_split_by_resume(
    df: pd.DataFrame, test_size: float, random_state: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # split on resumes so jobs from one resume stay together
    resumes = np.array(sorted(df["resume_id"].unique()))
    rng = np.random.default_rng(random_state)
    shuffled = resumes.copy()
    rng.shuffle(shuffled)

    n_test = max(1, int(round(len(shuffled) * test_size)))

    test_resumes = set(shuffled[:n_test])
    train_resumes = set(shuffled[n_test:])

    train_df = df[df["resume_id"].isin(train_resumes)].copy()
    test_df = df[df["resume_id"].isin(test_resumes)].copy()
    return train_df, test_df


def add_teacher_scores(
    train_df: pd.DataFrame, test_df: pd.DataFrame, model_name: str, top_k: int
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # train the full feature teacher model
    teacher_regressor = build_regressor(model_name)
    teacher_regressor.fit(train_df[FEATURES_ALL], train_df[TARGET])

    teacher_train = train_df.copy()
    teacher_test = test_df.copy()
    teacher_train["full_score"] = teacher_regressor.predict(
        teacher_train[FEATURES_ALL]
    )
    teacher_test["full_score"] = teacher_regressor.predict(
        teacher_test[FEATURES_ALL]
    )

    teacher_train = add_teacher_topk_labels(teacher_train, "full_score", top_k)
    teacher_test = add_teacher_topk_labels(teacher_test, "full_score", top_k)
    return teacher_train, teacher_test


def add_teacher_topk_labels(df: pd.DataFrame, score_col: str, top_k: int) -> pd.DataFrame:
    out = df.copy()
    out["teacher_topk_label"] = 0
    out["teacher_rank"] = 0

    # mark the teacher model's top jobs for each resume
    for _, idx in out.groupby("resume_id").groups.items():
        group = out.loc[idx].sort_values(score_col, ascending=False)
        top_idx = group.head(top_k).index
        out.loc[top_idx, "teacher_topk_label"] = 1
        ranks = pd.Series(range(1, len(group) + 1), index=group.index)
        out.loc[group.index, "teacher_rank"] = ranks.values

    out["teacher_rank"] = out["teacher_rank"].astype(int)
    out["teacher_topk_label"] = out["teacher_topk_label"].astype(int)
    return out


def per_resume_ranked_topk_recall(
    df: pd.DataFrame, ranking_col: str, teacher_label_col: str, top_k: int
) -> float:
    # compare ranked top-k jobs against the teacher top-k labels
    recalls = []
    for _, group in df.groupby("resume_id"):
        true_jobs = set(group.loc[group[teacher_label_col] == 1, "job_id"])
        pred_jobs = set(
            group.sort_values(ranking_col, ascending=False)
            .head(top_k)["job_id"]
        )
        if len(true_jobs) == 0:
            continue
        recalls.append(len(true_jobs & pred_jobs) / len(true_jobs))
    return float(np.mean(recalls)) if recalls else float("nan")


def top_resume_agreement(
    df: pd.DataFrame, ranking_col: str, teacher_col: str, top_k: int
) -> Tuple[float, float, pd.DataFrame]:
    # check whether the student ranking keeps the teacher's best job near the top
    top1_match_count = 0
    topk_contains_teacher_top1 = 0
    per_resume_rows = []

    for resume_id, group in df.groupby("resume_id"):
        teacher_sorted = group.sort_values(teacher_col, ascending=False)
        pred_sorted = group.sort_values(ranking_col, ascending=False)

        teacher_top1_job = teacher_sorted.iloc[0]["job_id"]
        predicted_top1_job = pred_sorted.iloc[0]["job_id"]
        predicted_topk_jobs = pred_sorted.head(top_k)["job_id"].tolist()

        top1_match = int(teacher_top1_job == predicted_top1_job)
        topk_hit = int(teacher_top1_job in predicted_topk_jobs)

        top1_match_count += top1_match
        topk_contains_teacher_top1 += topk_hit

        per_resume_rows.append(
            {
                "resume_id": resume_id,
                "teacher_top1_job": teacher_top1_job,
                "predicted_top1_job": predicted_top1_job,
                f"predicted_top{top_k}_jobs": predicted_topk_jobs,
                "top1_match": top1_match,
                f"top{top_k}_contains_teacher_top1": topk_hit,
            }
        )

    n_test_resumes = df["resume_id"].nunique()
    top1_resume_agreement = (
        top1_match_count / n_test_resumes if n_test_resumes else float("nan")
    )
    topk_resume_containment = (
        topk_contains_teacher_top1 / n_test_resumes if n_test_resumes else float("nan")
    )
    return top1_resume_agreement, topk_resume_containment, pd.DataFrame(per_resume_rows)


def safe_roc_auc(y_true: pd.Series, y_score: pd.Series) -> float:
    if y_true.nunique() < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def apply_smote(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int,
    enable_smote: bool,
) -> Tuple[pd.DataFrame, pd.Series]:
    # only resample when smote has enough minority examples to work with
    class_counts = Counter(y_train.tolist())

    if not enable_smote:
        return X_train, y_train

    if len(class_counts) < 2:
        return X_train, y_train

    minority_count = min(class_counts.values())
    if minority_count < 2:
        return X_train, y_train

    k_neighbors = min(5, minority_count - 1)
    if k_neighbors < 1:
        return X_train, y_train

    sampler = SMOTE(random_state=random_state, k_neighbors=k_neighbors)
    X_resampled, y_resampled = sampler.fit_resample(X_train, y_train)
    X_resampled_df = pd.DataFrame(X_resampled, columns=X_train.columns)
    y_resampled_series = pd.Series(y_resampled, name=y_train.name)
    return X_resampled_df, y_resampled_series


def run_variant(
    variant_name: str,
    variant_features: List[str],
    teacher_train: pd.DataFrame,
    teacher_test: pd.DataFrame,
    classifier_name: str,
    regressor_name: str,
    top_k: int,
    use_smote: bool,
    random_state: int,
) -> Dict:
    train_scored = teacher_train.copy()
    test_scored = teacher_test.copy()

    # baselines use one metric directly while variants train a student regressor
    if variant_name.startswith("baseline_"):
        metric = variant_features[0]
        score_col = f"{variant_name}_score"
        train_scored[score_col] = train_scored[metric]
        test_scored[score_col] = test_scored[metric]
    else:
        regressor = build_regressor(regressor_name)
        score_col = f"{variant_name}_score"
        regressor.fit(train_scored[variant_features], train_scored[TARGET])
        train_scored[score_col] = regressor.predict(train_scored[variant_features])
        test_scored[score_col] = regressor.predict(test_scored[variant_features])

    clf_features = list(variant_features) + [score_col]

    # train the classifier to predict teacher top-k labels
    X_train_clf = train_scored[clf_features].copy()
    y_train_clf = train_scored["teacher_topk_label"].copy()
    X_train_fit, y_train_fit = apply_smote(
        X_train_clf, y_train_clf, random_state=random_state, enable_smote=use_smote
    )

    classifier = build_classifier(classifier_name)
    classifier.fit(X_train_fit, y_train_fit)

    test_scored["pred_label"] = classifier.predict(test_scored[clf_features])
    if hasattr(classifier, "predict_proba"):
        test_scored["pred_prob"] = classifier.predict_proba(test_scored[clf_features])[:, 1]
    else:
        test_scored["pred_prob"] = classifier.decision_function(test_scored[clf_features])

    accuracy = accuracy_score(test_scored["teacher_topk_label"], test_scored["pred_label"])
    precision = precision_score(
        test_scored["teacher_topk_label"],
        test_scored["pred_label"],
        zero_division=0,
    )
    recall = recall_score(
        test_scored["teacher_topk_label"],
        test_scored["pred_label"],
        zero_division=0,
    )
    f1 = f1_score(
        test_scored["teacher_topk_label"],
        test_scored["pred_label"],
        zero_division=0,
    )
    roc_auc = safe_roc_auc(test_scored["teacher_topk_label"], test_scored["pred_prob"])
    ranked_topk_recall = per_resume_ranked_topk_recall(
        test_scored, "pred_prob", "teacher_topk_label", top_k
    )

    # compare the teacher ranking to jobs ranked by classifier probability
    top1_agreement_prob, topk_containment_prob, per_resume_prob = top_resume_agreement(
        test_scored, "pred_prob", "full_score", top_k
    )
    # compare the teacher ranking to jobs ranked by student or baseline score
    top1_agreement_score, topk_containment_score, _ = top_resume_agreement(
        test_scored, score_col, "full_score", top_k
    )

    metrics = {
        "variant": variant_name,
        "variant_features": variant_features,
        "classifier_input": "both",
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc) if not np.isnan(roc_auc) else None,
        "per_resume_ranked_topk_recall": float(ranked_topk_recall),
        "top1_resume_agreement_using_pred_prob": float(top1_agreement_prob),
        f"top{top_k}_containment_of_teacher_top1_using_pred_prob": float(
            topk_containment_prob
        ),
        "top1_resume_agreement_using_student_score": float(top1_agreement_score),
        f"top{top_k}_containment_of_teacher_top1_using_student_score": float(
            topk_containment_score
        ),
        "confusion_matrix": confusion_matrix(
            test_scored["teacher_topk_label"], test_scored["pred_label"]
        ).tolist(),
        "classification_report": classification_report(
            test_scored["teacher_topk_label"],
            test_scored["pred_label"],
            digits=4,
            zero_division=0,
            output_dict=True,
        ),
    }

    return {
        "metrics": metrics,
        "per_resume_summary": per_resume_prob.to_dict(orient="records"),
    }


def run_cross_validation(
    df: pd.DataFrame,
    n_splits: int,
    classifier_name: str,
    regressor_name: str,
    top_k: int,
    use_smote: bool,
    random_state: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    variants = get_variants()

    gkf = GroupKFold(n_splits=n_splits)
    groups = df["resume_id"]

    all_rows = []

    for fold, (train_idx, test_idx) in enumerate(
        gkf.split(df, groups=groups), start=1
    ):
        teacher_train, teacher_test = add_teacher_scores(
            df.iloc[train_idx].copy(),
            df.iloc[test_idx].copy(),
            # keep cv teacher fixed for comparable folds
            model_name="ridge",
            top_k=top_k,
        )

        for variant_name, variant_features in variants.items():
            result = run_variant(
                variant_name=variant_name,
                variant_features=variant_features,
                teacher_train=teacher_train,
                teacher_test=teacher_test,
                classifier_name=classifier_name,
                regressor_name=regressor_name,
                top_k=top_k,
                use_smote=use_smote,
                random_state=random_state,
            )

            m = result["metrics"]

            all_rows.append(
                {
                    "fold": fold,
                    "variant": variant_name,
                    "accuracy": m["accuracy"],
                    "precision": m["precision"],
                    "recall": m["recall"],
                    "f1": m["f1"],
                    "roc_auc": m["roc_auc"],
                    "top1": m["top1_resume_agreement_using_student_score"],
                    f"top{top_k}_containment": m[
                        f"top{top_k}_containment_of_teacher_top1_using_student_score"
                    ],
                }
            )

    cv_df = pd.DataFrame(all_rows)

    print("\n" + "=" * 88)
    print("CROSS-VALIDATION RESULTS (MEAN ± STD)")
    print("=" * 88)

    summary = (
        cv_df.groupby("variant")
        .agg(
            accuracy_mean=("accuracy", "mean"),
            accuracy_std=("accuracy", "std"),
            precision_mean=("precision", "mean"),
            recall_mean=("recall", "mean"),
            f1_mean=("f1", "mean"),
            roc_auc_mean=("roc_auc", "mean"),
            top1_mean=("top1", "mean"),
            topk_mean=(f"top{top_k}_containment", "mean"),
        )
        .reset_index()
        .sort_values("f1_mean", ascending=False)
    )

    print(summary.round(4).to_string(index=False))
    return cv_df, summary


def summarize_variant(metrics: Dict, top_k: int) -> Dict:
    return {
        "variant": metrics["variant"],
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "roc_auc": metrics["roc_auc"],
        "per_resume_ranked_topk_recall": metrics["per_resume_ranked_topk_recall"],
        "top1_agreement_pred_prob": metrics[
            "top1_resume_agreement_using_pred_prob"
        ],
        f"top{top_k}_containment_pred_prob": metrics[
            f"top{top_k}_containment_of_teacher_top1_using_pred_prob"
        ],
        "top1_agreement_student_score": metrics[
            "top1_resume_agreement_using_student_score"
        ],
        f"top{top_k}_containment_student_score": metrics[
            f"top{top_k}_containment_of_teacher_top1_using_student_score"
        ],
    }


def print_run_header(args, teacher_train: pd.DataFrame, teacher_test: pd.DataFrame) -> None:
    print("=" * 88)
    print("TOP-K TEACHER-STUDENT CLASSIFICATION: ABLATIONS + BASELINES")
    print("=" * 88)
    print(
        f"Train resumes: {teacher_train['resume_id'].nunique()} | "
        f"Test resumes: {teacher_test['resume_id'].nunique()}"
    )
    print(f"Teacher regressor: {args.full_model}")
    print(f"Student regressor (for non-baseline variants): {args.student_model}")
    print(f"Classifier: {args.classifier}")
    print("Classifier input: both")
    print(f"Top-K: {args.top_k}")
    print(f"Use SMOTE: {args.use_smote}")


def print_variant_report(
    variant_name: str, variant_features: List[str], metrics: Dict, top_k: int
) -> None:
    roc_auc_display = "nan" if metrics["roc_auc"] is None else f"{metrics['roc_auc']:.4f}"
    prob_topk_key = f"top{top_k}_containment_of_teacher_top1_using_pred_prob"
    score_topk_key = f"top{top_k}_containment_of_teacher_top1_using_student_score"

    print("\n" + "-" * 88)
    print(f"VARIANT: {variant_name}")
    print("-" * 88)
    print(f"Features: {variant_features}")

    for label, value in [
        ("Accuracy", f"{metrics['accuracy']:.4f}"),
        ("Precision", f"{metrics['precision']:.4f}"),
        ("Recall", f"{metrics['recall']:.4f}"),
        ("F1", f"{metrics['f1']:.4f}"),
        ("ROC-AUC", roc_auc_display),
        (
            f"Per-resume ranked Top-{top_k} recall",
            f"{metrics['per_resume_ranked_topk_recall']:.4f}",
        ),
    ]:
        print(f"{label}: {value}")

    print(
        "Top-1 agreement (pred_prob ranking): "
        f"{metrics['top1_resume_agreement_using_pred_prob']:.4f}"
    )
    print(
        f"Top-{top_k} containment of teacher top-1 (pred_prob ranking): "
        f"{metrics[prob_topk_key]:.4f}"
    )
    print(
        "Top-1 agreement (student score ranking): "
        f"{metrics['top1_resume_agreement_using_student_score']:.4f}"
    )
    print(
        f"Top-{top_k} containment of teacher top-1 (student score ranking): "
        f"{metrics[score_topk_key]:.4f}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Teacher-student top-k classification across ablations."
    )
    parser.add_argument("--data", required=True, help="Path to training_dataset.csv")
    parser.add_argument(
        "--full-model",
        default="ridge",
        choices=["ridge", "gradient_boosting", "mlp"],
    )
    parser.add_argument(
        "--student-model",
        default="ridge",
        choices=["ridge", "gradient_boosting", "mlp"],
    )
    parser.add_argument(
        "--classifier",
        default="logistic",
        choices=["logistic", "gradient_boosting", "random_forest"],
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--use-smote",
        type=parse_bool,
        default=True,
        choices=[True, False],
        help="Apply SMOTE to classifier training data.",
    )
    parser.add_argument("--output-metrics", default=None)
    parser.add_argument(
        "--cv",
        action="store_true",
        help="Run GroupKFold cross-validation.",
    )
    parser.add_argument("--cv-folds", type=int, default=5)
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    validate_columns(df)

    if df["resume_id"].nunique() < 2:
        raise ValueError(
            "Need at least 2 unique resumes for a resume-level train/test split."
        )
    if args.cv:
        run_cross_validation(
            df=df,
            n_splits=args.cv_folds,
            classifier_name=args.classifier,
            regressor_name=args.student_model,
            top_k=args.top_k,
            use_smote=args.use_smote,
            random_state=args.random_state,
        )
        return

    train_df, test_df = train_test_split_by_resume(
        df, test_size=args.test_size, random_state=args.random_state
    )
    teacher_train, teacher_test = add_teacher_scores(
        train_df, test_df, model_name=args.full_model, top_k=args.top_k
    )
    variants = get_variants()
    all_results = []
    summary_rows = []

    print_run_header(args, teacher_train, teacher_test)

    # run the same teacher comparison for each ablation and baseline
    for variant_name, variant_features in variants.items():
        result = run_variant(
            variant_name=variant_name,
            variant_features=variant_features,
            teacher_train=teacher_train,
            teacher_test=teacher_test,
            classifier_name=args.classifier,
            regressor_name=args.student_model,
            top_k=args.top_k,
            use_smote=args.use_smote,
            random_state=args.random_state,
        )
        metrics = result["metrics"]
        all_results.append(result)
        summary_rows.append(summarize_variant(metrics, args.top_k))
        print_variant_report(variant_name, variant_features, metrics, args.top_k)

    summary_df = pd.DataFrame(summary_rows).sort_values(
        ["f1", "roc_auc", "accuracy"], ascending=False
    )

    print("\n" + "=" * 88)
    print("SUMMARY TABLE")
    print("=" * 88)
    print(summary_df.to_string(index=False))

    if args.output_metrics:
        payload = {
            "train_resumes": int(teacher_train["resume_id"].nunique()),
            "test_resumes": int(teacher_test["resume_id"].nunique()),
            "teacher_regressor": args.full_model,
            "student_regressor": args.student_model,
            "classifier": args.classifier,
            "classifier_input": "both",
            "top_k": int(args.top_k),
            "use_smote": bool(args.use_smote),
            "summary_table": summary_rows,
            "variant_results": all_results,
        }
        with open(args.output_metrics, "w") as f:
            json.dump(payload, f, indent=2)


if __name__ == "__main__":
    main()
