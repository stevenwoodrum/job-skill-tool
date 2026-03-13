import json
import re
from typing import Any

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1"

"""
Local Ollama Setup and Usage

This module sends prompts to a locally running Ollama model to perform
skill extraction from job descriptions.

Prerequisites
-------------
1. Install Ollama
   https://ollama.com/download
   (brew install ollama)

2. Start the Ollama server
   Ollama runs automatically in the background after installation.
   The API will be available at:
       http://localhost:11434

Operation
---------
This code sends HTTP POST requests to the Ollama API endpoint:

    POST http://localhost:11434/api/generate

with the payload:
    {
        "model": "<model name>",
        "prompt": "<text prompt>",
        "stream": false
    }

The model response is returned as JSON and parsed for structured skill data.

Typical Flow
------------
1. Send job description prompt to Ollama.
2. Extract raw skill candidates.
3. Run a second pass to normalize and filter skills.
4. Return cleaned structured skill results.

Notes
-----
- The Ollama server must be running locally.
- The specified model must already be downloaded.
- This implementation uses the synchronous `/api/generate` endpoint.
"""


def call_ollama(prompt: str, model: str = MODEL_NAME, timeout: int = 120) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def parse_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON in model output:\n{text}")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse JSON from model output:\n{text}") from e


def raw_skills_prompt(job_description: str) -> str:
    return f"""
Extract possible professional skills from this job description.

Include:
- technical skills
- tools/software
- domain knowledge
- certifications/licenses
- meaningful professional capabilities

Exclude:
- salary
- dates
- locations
- benefits
- company boilerplate
- application instructions

Return JSON only:

{{
  "raw_skills": [
    {{
      "skill_text": "text",
      "evidence": "short phrase",
      "confidence": 0.0
    }}
  ]
}}

Job description:
\"\"\"
{job_description}
\"\"\"
""".strip()


def clean_skills_prompt(job_description: str, raw_skills: dict) -> str:
    return f"""
Clean and normalize these extracted skills.

Rules:
- merge duplicates
- remove junk
- use standard skill names
- keep only real job-relevant skills
- confidence must be at least 0.60

Allowed types:
- technical
- domain
- soft
- certification
- tool

Return JSON only:

{{
  "skills": [
    {{
      "skill": "normalized skill name",
      "type": "technical | domain | soft | certification | tool",
      "evidence": "short phrase",
      "confidence": 0.0
    }}
  ]
}}

Job description:
\"\"\"
{job_description}
\"\"\"

Raw skills:
{json.dumps(raw_skills, indent=2)}
""".strip()


def clamp_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, round(float(value), 3)))
    except (TypeError, ValueError):
        return 0.0


def extract_skills(job_description: str, model: str = MODEL_NAME) -> dict:
    raw = parse_json(call_ollama(raw_skills_prompt(job_description), model=model))
    final = parse_json(call_ollama(clean_skills_prompt(job_description, raw), model=model))
    return final


def analyze_job_description(job_description: str) -> dict:
    if not job_description or not job_description.strip():
        return {
            "jobOverview": "",
            "skillsAnalysis": "",
            "skills": [],
        }

    skills = extract_skills(job_description)["skills"]

    if skills:
        skills_analysis = "\n".join(
            f"- {s['skill']} ({s['type']}) | evidence: {s['evidence']} | confidence: {s['confidence']}"
            for s in skills
        )
    else:
        skills_analysis = "No high-confidence skills were extracted."

    return {
        "jobOverview": "Skill extraction completed using a local Ollama model.",
        "skillsAnalysis": skills_analysis,
        "skills": skills,
    }


if __name__ == "__main__":
    job_description = """
    We are seeking a Senior Associate Attorney for our Elder Law and Estate Planning practice.
    The successful candidate will counsel clients with regard to estate planning and asset protection;
    formulate and oversee execution of Medicaid and estate plans; draft wills, revocable and irrevocable trusts,
    powers of attorney, health care proxies, and living wills; handle estate administration and trust administration;
    appear in court for estate proceedings; and supervise paralegals.

    Qualifications:
    Juris Doctor degree (J.D.) from an accredited law school
    Licensed to practice law in New York
    10-15 years of experience
    Strong communication skills
    """

    print(json.dumps(analyze_job_description(job_description), indent=2))