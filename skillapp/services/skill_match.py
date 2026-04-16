from typing import List, Dict, Any, Protocol
import math

import pandas as pd
import requests

"""
Local Ollama Setup and Usage

This module sends embedding requests to a locally running Ollama model to perform
skill matches.

Prerequisites
-------------
1. Install Ollama
   https://ollama.com/download
   (brew install ollama)

2. Start the Ollama server
   Ollama runs automatically in the background after installation.
   The API will be available at:
       http://localhost:11434

3. Pull Ollama embedding model
    ollama pull embeddinggemma

Operation
---------
This code sends HTTP POST requests to the Ollama API endpoint:

    POST http://localhost:11434/api/embeddings
    
where we pull the data["embeddings"].

Notes
- The Ollama server must be running locally.
- The specified model must already be downloaded.
- This implementation uses the synchronous `/api/generate` endpoint.
"""

class OllamaEmbeddingProvider:
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
    return " ".join(skill.lower().strip().split())

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

class SkillMatcher:
    def __init__(self, embedding_provider, threshold: float = 0.80):
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

        all_skills = normalized_resume + normalized_job
        embeddings = self.embedding_provider.embed(all_skills)

        resume_embeddings = embeddings[:len(normalized_resume)]
        job_embeddings = embeddings[len(normalized_resume):]

        matched = []
        unmatched_job_skills = []
        used_resume_indices = set()

        for job_idx, job_skill in enumerate(normalized_job):
            best_score = -1.0
            best_resume_idx = None

            for resume_idx, resume_skill in enumerate(normalized_resume):

                score = cosine_similarity(job_embeddings[job_idx], resume_embeddings[resume_idx])

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
    provider = OllamaEmbeddingProvider()
    matcher = SkillMatcher(provider, threshold=0.80)

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
                f"\n{report["unmatched_job_skills"]}"
            )

        dict = {}

        dict['title'] = item['title']
        dict['id'] = item['id']
        dict['score'] = score
        return_df.append(dict)
    return_df = pd.DataFrame(return_df)
    return_df.to_csv("baseline_skill.csv", index=False)



