#!/usr/bin/env python3
"""Build the resume/job training CSV used by train_models.py."""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_TARGET_WEIGHTS = {
    "jaccard_similarity": 0.2,
    "tfidf_cosine": 0.20,
    "embedding_cosine": 0.2,
    "job_skill_coverage": 0.2,
    "avg_max_skill_similarity": 0.2,
}


@dataclass
class Record:
    record_id: str
    title: str
    text: str
    skills: List[str]


class OllamaEmbedder:
    def __init__(self, model_name: str, base_url: str, timeout: int = 300) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.embed_url = f"{self.base_url}/api/embed"

    def embed_text(self, text: str) -> np.ndarray:
        response = requests.post(
            self.embed_url,
            json={
                "model": self.model_name,
                "input": text,
            },
            timeout=self.timeout,
        )

        if not response.ok:
            print("Ollama error:", response.text)

        response.raise_for_status()
        payload = response.json()

        if "embeddings" in payload:
            vector = np.asarray(payload["embeddings"][0], dtype=float)
        elif "embedding" in payload:
            vector = np.asarray(payload["embedding"], dtype=float)
        else:
            raise ValueError(f"No embedding returned. Keys: {payload.keys()}")

        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        embeddings = [self.embed_text(t) for t in texts]
        return np.vstack(embeddings)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a pairwise resume-job training dataset from JSON files."
    )
    parser.add_argument("--jobs", required=True, help="Path to jobs JSON file")
    parser.add_argument("--resumes", required=True, help="Path to resumes JSON file")
    parser.add_argument("--output", required=True, help="Path to output CSV file")
    parser.add_argument(
        "--ollama-model",
        default="embeddinggemma",
        help="Local Ollama embeddings model name.",
    )
    parser.add_argument(
        "--ollama-base-url",
        default="http://localhost:11434",
        help="Base URL for local Ollama server.",
    )
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=120,
        help="Timeout in seconds for each Ollama embeddings request.",
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip Ollama embeddings and set embedding_cosine to 0.0.",
    )
    return parser.parse_args()


def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_skill(skill: str) -> str:
    skill = skill.lower().strip()
    skill = skill.replace("&", " and ")
    skill = re.sub(r"[/_\-]+", " ", skill)
    skill = re.sub(r"[^a-z0-9+.\s]", "", skill)
    skill = normalize_whitespace(skill)
    return skill


def extract_skills(item: Dict[str, Any]) -> List[str]:
    raw_skills = item.get("skills", [])
    normalized: List[str] = []

    for entry in raw_skills:
        if isinstance(entry, dict):
            skill_value = entry.get("skill", "")
        else:
            skill_value = entry

        raw_skill = "" if skill_value is None else str(skill_value)

        skill = normalize_skill(raw_skill)
        if skill:
            normalized.append(skill)

    return normalized


def build_record(item: Dict[str, Any], prefix: str) -> Record:
    skills = extract_skills(item)
    record_id_value = item.get("id")
    if record_id_value is None:
        raise ValueError(f"Missing 'id' in {prefix} record: {item}")
    record_id = str(record_id_value).strip()
    if not record_id:
        raise ValueError(f"Missing 'id' in {prefix} record: {item}")

    title = item.get("title", f"{prefix}_{record_id}").strip()
    overview = (item.get("jobOverview") or item.get("resumeOverview") or "").strip()

    text_parts = [title, overview, " ".join(skills)]
    text = normalize_whitespace(" ".join(part for part in text_parts if part))

    return Record(
        record_id=record_id,
        title=title,
        text=text,
        skills=skills,
    )


def build_records(data: Any, prefix: str) -> List[Record]:
    if not isinstance(data, list):
        raise ValueError(f"Expected top-level list for {prefix} JSON file.")

    records: List[Record] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Each {prefix} item must be a JSON object.")
        records.append(build_record(item, prefix=prefix))
    return records


def jaccard_similarity(skills_a: Sequence[str], skills_b: Sequence[str]) -> float:
    set_a = set(skills_a)
    set_b = set(skills_b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def coverage_score(resume_skills: Sequence[str], job_skills: Sequence[str]) -> float:
    job_set = set(job_skills)
    if not job_set:
        return 0.0
    resume_set = set(resume_skills)
    return len(job_set & resume_set) / len(job_set)


def token_jaccard(a: str, b: str) -> float:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def skill_similarity(skill_a: str, skill_b: str) -> float:
    if not skill_a or not skill_b:
        return 0.0
    if skill_a == skill_b:
        return 1.0

    from difflib import SequenceMatcher

    seq_ratio = SequenceMatcher(None, skill_a, skill_b).ratio()
    tok_ratio = token_jaccard(skill_a, skill_b)
    return float(max(seq_ratio, tok_ratio))


def average_max_skill_similarity(
    resume_skills: Sequence[str], job_skills: Sequence[str]
) -> float:
    if not resume_skills or not job_skills:
        return 0.0

    max_scores: List[float] = []
    for job_skill in job_skills:
        best = max(
            skill_similarity(job_skill, resume_skill)
            for resume_skill in resume_skills
        )
        max_scores.append(best)

    return float(np.mean(max_scores)) if max_scores else 0.0


def compute_tfidf_similarity_matrix(
    resumes: Sequence[Record], jobs: Sequence[Record]
) -> np.ndarray:
    all_docs = [record.text for record in resumes] + [record.text for record in jobs]
    if not any(doc.strip() for doc in all_docs):
        return np.zeros((len(resumes), len(jobs)), dtype=float)

    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(all_docs)

    n_resumes = len(resumes)
    resume_matrix = matrix[:n_resumes]
    job_matrix = matrix[n_resumes:]
    return cosine_similarity(resume_matrix, job_matrix)


def compute_embedding_similarity_matrix(
    resumes: Sequence[Record],
    jobs: Sequence[Record],
    skip_embeddings: bool,
    ollama_model: str,
    ollama_base_url: str,
    ollama_timeout: int,
) -> np.ndarray:
    if skip_embeddings:
        return np.zeros((len(resumes), len(jobs)), dtype=float)

    embedder = OllamaEmbedder(
        model_name=ollama_model,
        base_url=ollama_base_url,
        timeout=ollama_timeout,
    )
    all_texts = [record.text for record in resumes] + [record.text for record in jobs]
    embeddings = embedder.embed_texts(all_texts)

    n_resumes = len(resumes)
    resume_emb = embeddings[:n_resumes]
    job_emb = embeddings[n_resumes:]
    return cosine_similarity(resume_emb, job_emb)


def clipped_score(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(min(max(value, 0.0), 1.0))


def compute_aggregated_target(feature_row: Dict[str, float]) -> float:
    target = 0.0
    for feature_name, weight in DEFAULT_TARGET_WEIGHTS.items():
        target += weight * clipped_score(feature_row.get(feature_name, 0.0))
    return float(target)


def build_pairwise_dataset(
    resumes: Sequence[Record],
    jobs: Sequence[Record],
    skip_embeddings: bool,
    ollama_model: str,
    ollama_base_url: str,
    ollama_timeout: int,
) -> pd.DataFrame:
    tfidf_matrix = compute_tfidf_similarity_matrix(resumes, jobs)
    embedding_matrix = compute_embedding_similarity_matrix(
        resumes,
        jobs,
        skip_embeddings=skip_embeddings,
        ollama_model=ollama_model,
        ollama_base_url=ollama_base_url,
        ollama_timeout=ollama_timeout,
    )

    rows: List[Dict[str, Any]] = []

    for r_idx, resume in enumerate(resumes):
        for j_idx, job in enumerate(jobs):
            jaccard = clipped_score(jaccard_similarity(resume.skills, job.skills))
            coverage = clipped_score(coverage_score(resume.skills, job.skills))
            avg_max = clipped_score(average_max_skill_similarity(resume.skills, job.skills))
            tfidf_cos = clipped_score(float(tfidf_matrix[r_idx, j_idx]))
            emb_cos = clipped_score(float(embedding_matrix[r_idx, j_idx]))

            row: Dict[str, Any] = {
                "resume_id": resume.record_id,
                "resume_title": resume.title,
                "job_id": job.record_id,
                "job_title": job.title,
                "resume_skill_count": len(resume.skills),
                "job_skill_count": len(job.skills),
                "jaccard_similarity": jaccard,
                "tfidf_cosine": tfidf_cos,
                "embedding_cosine": emb_cos,
                "job_skill_coverage": coverage,
                "avg_max_skill_similarity": avg_max,
                "resume_skills": " | ".join(resume.skills),
                "job_skills": " | ".join(job.skills),
            }
            row["aggregated_target"] = compute_aggregated_target(row)
            rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()

    jobs_json = load_json(args.jobs)
    resumes_json = load_json(args.resumes)

    jobs = build_records(jobs_json, prefix="job")
    resumes = build_records(resumes_json, prefix="resume")

    dataset = build_pairwise_dataset(
        resumes=resumes,
        jobs=jobs,
        skip_embeddings=args.skip_embeddings,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_base_url,
        ollama_timeout=args.ollama_timeout,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False)

    print(f"Built dataset with {len(dataset)} rows")
    print(f"Resumes: {len(resumes)} | Jobs: {len(jobs)}")
    print(f"Embedding model: {'SKIPPED' if args.skip_embeddings else args.ollama_model}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
