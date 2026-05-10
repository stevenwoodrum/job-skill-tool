from collections import Counter
from difflib import SequenceMatcher
from typing import List, Dict, Any
import math
import re

import pandas as pd
import requests

"""
Skill matching setup and usage

By default, this module scores skill matches with a non-embedding aggregate made
from four bounded baseline features:

- token Jaccard similarity
- TF-IDF cosine similarity
- average/max skill similarity
- job skill coverage

The aggregate score is clipped to [0, 1] and preserves the existing API response
shape. The Ollama embedding provider is kept for backwards compatibility with
callers that still construct SkillMatcher with an embedding provider.
"""

BASELINE_WEIGHTS = {
    "jaccard_similarity": 0.25,
    "tfidf_cosine": 0.25,
    "avg_max_skill_similarity": 0.25,
    "skill_coverage": 0.25,
}


class OllamaEmbeddingProvider:
    """
    Legacy Ollama embedding pipeline.

    Prerequisites if this scorer is re-enabled:
    1. Install Ollama:
       https://ollama.com/download
       or `brew install ollama`
    2. Start the local Ollama server.
       The API should be available at `http://localhost:11434`.
    3. Pull the embedding model:
       `ollama pull embeddinggemma`

    This provider sends requests to:
    `POST http://localhost:11434/api/embed`
    and reads `data["embeddings"]` from the response.
    """

    def __init__(self, model="embeddinggemma", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def embed(self, texts):
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": texts
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"]

def normalize_skill(skill: str) -> str:
    skill = skill.lower().strip()
    skill = skill.replace("&", " and ")
    skill = re.sub(r"[/_\-]+", " ", skill)
    skill = re.sub(r"[^a-z0-9+.\s]", "", skill)
    return " ".join(skill.split())


def tokenize_skill(skill: str) -> List[str]:
    normalized = normalize_skill(skill)
    return normalized.split() if normalized else []


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def clipped_score(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(min(max(value, 0.0), 1.0))


def token_jaccard_similarity(skill_a: str, skill_b: str) -> float:
    tokens_a = set(tokenize_skill(skill_a))
    tokens_b = set(tokenize_skill(skill_b))
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def tfidf_cosine_similarity(skill_a: str, skill_b: str) -> float:
    docs = [tokenize_skill(skill_a), tokenize_skill(skill_b)]
    vocabulary = sorted(set(docs[0]) | set(docs[1]))
    if not vocabulary:
        return 0.0

    doc_count = len(docs)
    doc_frequencies = {
        token: sum(1 for doc in docs if token in doc)
        for token in vocabulary
    }

    vectors = []
    for doc in docs:
        counts = Counter(doc)
        total_tokens = len(doc)
        if total_tokens == 0:
            vectors.append([0.0 for _ in vocabulary])
            continue

        vector = []
        for token in vocabulary:
            term_frequency = counts[token] / total_tokens
            inverse_doc_frequency = math.log(
                (1 + doc_count) / (1 + doc_frequencies[token])
            ) + 1
            vector.append(term_frequency * inverse_doc_frequency)
        vectors.append(vector)

    return clipped_score(cosine_similarity(vectors[0], vectors[1]))


def skill_coverage(job_skill: str, resume_skill: str) -> float:
    job_tokens = set(tokenize_skill(job_skill))
    if not job_tokens:
        return 0.0
    resume_tokens = set(tokenize_skill(resume_skill))
    return len(job_tokens & resume_tokens) / len(job_tokens)


def avg_max_skill_similarity(job_skill: str, resume_skill: str) -> float:
    normalized_job = normalize_skill(job_skill)
    normalized_resume = normalize_skill(resume_skill)
    if not normalized_job or not normalized_resume:
        return 0.0
    if normalized_job == normalized_resume:
        return 1.0

    sequence_score = SequenceMatcher(
        None,
        normalized_job,
        normalized_resume,
    ).ratio()
    token_score = token_jaccard_similarity(normalized_job, normalized_resume)
    return clipped_score(max(sequence_score, token_score))


def aggregate_baseline_score(job_skill: str, resume_skill: str) -> float:
    features = {
        "jaccard_similarity": clipped_score(
            token_jaccard_similarity(job_skill, resume_skill)
        ),
        "tfidf_cosine": clipped_score(
            tfidf_cosine_similarity(job_skill, resume_skill)
        ),
        "avg_max_skill_similarity": clipped_score(
            avg_max_skill_similarity(job_skill, resume_skill)
        ),
        "skill_coverage": clipped_score(
            skill_coverage(job_skill, resume_skill)
        ),
    }
    score = sum(
        BASELINE_WEIGHTS[name] * features[name]
        for name in BASELINE_WEIGHTS
    )
    return clipped_score(score)


class SkillMatcher:
    def __init__(self, embedding_provider=None, threshold: float = 0.80):
        self.embedding_provider = embedding_provider
        self.threshold = threshold

    def match_skills(
        self,
        resume_skills: List[str],
        job_skills: List[str],
        job_evidence: List[str],
    ) -> Dict[str, Any]:
        normalized_resume = [normalize_skill(s) for s in resume_skills]
        normalized_job = [normalize_skill(s) for s in job_skills]

        # Legacy Ollama embedding setup. Re-enable this block with the legacy
        # score line below if you want embedding cosine matching again.

        # all_skills = normalized_resume + normalized_job
        # embeddings = self.embedding_provider.embed(all_skills)
        #
        # resume_embeddings = embeddings[:len(normalized_resume)]
        # job_embeddings = embeddings[len(normalized_resume):]

        matched = []
        unmatched_job_skills = []
        used_resume_indices = set()

        for job_idx, job_skill in enumerate(normalized_job):
            best_score = -1.0
            best_resume_idx = None

            for resume_idx, resume_skill in enumerate(normalized_resume):

                score = aggregate_baseline_score(job_skill, resume_skill)
                # Legacy Ollama embedding score:
                # score = cosine_similarity(
                #     job_embeddings[job_idx],
                #     resume_embeddings[resume_idx],
                # )

                if score > best_score:
                    best_score = score
                    best_resume_idx = resume_idx

            if best_resume_idx is not None and best_score >= self.threshold:
                matched.append({
                    "job_skill": job_skills[job_idx],
                    "job_evidence": job_evidence[job_idx],
                    "resume_skill": resume_skills[best_resume_idx],
                    "score": round(best_score, 4),
                    "match_strength": self.label_match_strength(best_score)
                })
                used_resume_indices.add(best_resume_idx)
            else:
                unmatched_job_skills.append(job_skills[job_idx])

        matched_resume_indices = {
            resume_skills.index(m["resume_skill"])
            for m in matched
            if m["resume_skill"] in resume_skills
        }

        unused_resume_skills = [
            resume_skills[i]
            for i in range(len(resume_skills))
            if i not in matched_resume_indices
        ]

        coverage = len(matched) / len(job_skills) if job_skills else 0.0

        return {
            "threshold": self.threshold,
            "matched": matched,
            "unmatched_job_skills": unmatched_job_skills,
            "unused_resume_skills": unused_resume_skills,
            "coverage": round(coverage, 4)
        }

    @staticmethod
    def label_match_strength(score: float) -> str:
        if score >= 0.85:
            return "strong"
        if score >= 0.75:
            return "possible"
        return "weak"

if __name__ == "__main__":
    # provider = OllamaEmbeddingProvider()
    matcher = SkillMatcher(threshold=0.60)

    from pathlib import Path
    import json

    BASE_DIR = Path(__file__).resolve().parents[3]

    resume_skills = []
    job_skills = []
    csv_path = BASE_DIR / "test_resumes.json"
    with open(csv_path, 'r') as file:
        resume = json.load(file)
        resume_skills.extend([skill['skill'] for skill in resume[0]['skills']])

    job_path = BASE_DIR / "test_jobs.json"
    with open(job_path, 'r') as file:
        data = json.load(file)

    return_df = []
    for item in data:
        job_skills = [skill['skill'] for skill in item['skills']]
        job_evidence = [skill['evidence'] for skill in item['skills']]
        report = matcher.match_skills(resume_skills, job_skills, job_evidence)
        report["matched"] = sorted(
            report["matched"],
            key=lambda x: x["score"],
            reverse=True
        )


        score = 0
        for match in report["matched"]:

            if match:
                print(item['title'])
                print(item['id'])
            score += match["score"]



            print(
                f"{match['job_skill']}  <--->  "
                f"{match['resume_skill']}  |  "
                f"score={match['score']:.4f}  |  "
                f"{match['match_strength']}"
                f"\n{match['job_evidence']}"
                f"\n{report['unmatched_job_skills']}"
            )

        dict = {}

        dict['title'] = item['title']
        dict['id'] = item['id']
        dict['score'] = score
        return_df.append(dict)
    return_df = pd.DataFrame(return_df)
    return_df.to_csv("baseline_skill.csv", index=False)
