# Resume-job matching analysis

This folder contains the scripts used to build and evaluate the resume/job matching dataset. The main assumption for running the analysis is that you already have a `training_dataset.csv` file.

## Dataset format

The training CSV should have one row per resume-job pair. The model scripts expect these columns:

```text
resume_id
job_id
jaccard_similarity
tfidf_cosine
embedding_cosine
job_skill_coverage
avg_max_skill_similarity
aggregated_target
```

The current generated files also include helpful metadata columns like `resume_title`, `job_title`, `resume_skills`, and `job_skills`.

## 1. build_training_dataset.py

Use this only if you need to recreate `training_dataset.csv` from extracted job/resume JSON files.

```bash
python3 build_training_dataset.py \
  --jobs test_jobs.json \
  --resumes test_resumes.json \
  --output training_dataset.csv
```

This script creates every resume-job pair and computes the matching features:

- `jaccard_similarity`
- `tfidf_cosine`
- `embedding_cosine`
- `job_skill_coverage`
- `avg_max_skill_similarity`
- `aggregated_target`

If Ollama embeddings are not available, run:

```bash
python3 build_training_dataset.py \
  --jobs test_jobs.json \
  --resumes test_resumes.json \
  --output training_dataset.csv \
  --skip-embeddings
```

`--skip-embeddings` sets `embedding_cosine` to `0.0`, so use it only when you want a quick run without semantic embeddings.

## 2. train_models.py

Use this to evaluate regression models that predict `aggregated_target`. You can save metrics locally using `--save-metrics`.

```bash
python3 train_models.py \
  --data training_dataset.csv \
  --save-metrics metrics.json
```

This script prints:

- dataset summary statistics
- single-feature baseline results
- ridge and gradient boosting regression results
- optional MLP results if `--use-mlp` is passed
- ridge coefficients for each experiment

It also runs feature ablations:

```text
full_features
minus_embedding_cosine
minus_embedding_and_tfidf
```

Example with the MLP enabled:

```bash
python3 train_models.py \
  --data training_dataset.csv \
  --use-mlp \
  --save-metrics metrics.json
```

## 3. top5_teacher_student_classifier.py

Use this for the teacher-student Top-K experiment.

```bash
python3 top5_teacher_student_classifier.py \
  --data training_dataset.csv \
  --top-k 5 \
  --use-smote true \
  --output-metrics top5_smote_metrics.json
```
This script treats the full-feature model as the teacher. The teacher ranks jobs for each resume and marks the Top-K jobs as positive labels. Then each student variant tries to recover those teacher Top-K jobs using fewer features or a single baseline metric.

The experiment variants are:

```text
minus_embedding
minus_tfidf
minus_tfidf_embedding
baseline_jaccard_similarity
baseline_tfidf_cosine
baseline_embedding_cosine
baseline_job_skill_coverage
baseline_avg_max_skill_similarity
```

The classifier always uses both:

- the variant's raw features
- the student or baseline score

The main metrics are:

- `accuracy`, `precision`, `recall`, `f1`, `roc_auc`
- `per_resume_ranked_topk_recall`
- `top1_agreement_pred_prob`
- `top5_containment_pred_prob`
- `top1_agreement_student_score`
- `top5_containment_student_score`

To disable SMOTE:

```bash
python3 top5_teacher_student_classifier.py \
  --data training_dataset.csv \
  --top-k 5 \
  --use-smote false
```

To run grouped cross-validation by resume:

```bash
python3 top5_teacher_student_classifier.py \
  --data training_dataset_more.csv \
  --top-k 5 \
  --use-smote true \
  --cv \
  --cv-folds 5
```

## Typical workflow

If `training_dataset.csv` is already provided, start at step 2:

```bash
python3 train_models.py \
  --data training_dataset.csv \
  --save-metrics metrics.json

python3 top5_teacher_student_classifier.py \
  --data training_dataset.csv \
  --top-k 5 \
  --use-smote true \
  --output-metrics top5_smote_metrics.json
```

If the CSV is missing, run `build_training_dataset.py` first.
