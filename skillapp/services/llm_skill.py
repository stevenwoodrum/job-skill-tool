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


def call_ollama(prompt: str, model: str = MODEL_NAME, timeout: int = 360) -> str:
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


def analyze_skills(description: str) -> dict:
    if not description or not description.strip():
        return {
            "jobOverview": "",
            "skills": [],
        }

    skills = extract_skills(description)["skills"]

    return {
        "jobOverview": "Skill extraction completed using a local Ollama model.",
        # "skillsAnalysis": skills_analysis,
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

    job_description = """
    Job Summary
    We are seeking a skilled Production Planner with a background in Food Technology to oversee our
    production processes and ensure efficient and effective manufacturing operations. The Production
    Planner will ensure the production schedule is optimized, materials are available when needed,
    and products are manufactured to meet customer demand.

    The successful candidate will work closely with the Production Team, Procurement, and Quality
    Assurance Departments to ensure production schedules are met and product quality is maintained.
    This role is onsite in Concord/Charlotte, NC.

    Responsibilities
    - Develop and maintain an effective production plan to ensure production targets are met in a
      timely and cost-effective manner.
    - Ensure the production schedule aligns with customer demand and sales forecasts and communicate
      any changes to relevant departments.
    - Monitor inventory levels and coordinate with procurement to ensure raw materials and packaging
      materials are available when required.
    - Analyze production data to identify opportunities for process improvement, reduce waste,
      and improve product quality.
    - Coordinate with maintenance and production supervisors to ensure equipment is in good
      working order.
    - Ensure compliance with all relevant health and safety regulations and company policies.
    - Maintain accurate and up-to-date production documentation.
    - Ensure all production quality measures are met.

    Requirements
    - Bachelor's degree in Food Science, Food Technology, or a related field.
    - 3–5 years of experience in production planning or a similar role within the food industry.
    - Strong analytical and problem-solving skills.
    - Ability to analyze production data and identify trends and improvement opportunities.
    - Excellent communication and interpersonal skills.
    - Knowledge of food safety regulations and quality control standards.
    - Familiarity with production planning software (SAP, MRP, MPS).
    - Strong organizational skills and ability to manage multiple priorities.
    - Understanding of production processes and supply chain management principles.
    - Ability to work independently and collaboratively.
    - Flexibility to work outside regular business hours when required.

    Physical Capabilities
    - Ability to routinely carry and lift up to 50 lbs.
    - Frequent climbing, bending, reaching, stooping, kneeling, and stretching.
    - Repeated lifting, carrying, pushing, pulling, and handling of products.
    - Extended standing or walking throughout the day.
    - Ability to operate powered industrial equipment including walkies, reach trucks, and stand-ups.
    - Ability to use computers and telephones for extended periods.
    """

    resume = """
    CONSULTANT           Career Focus    Analytical and results oriented professional with 2+ years of extensive experience in conducting, analyzing and interpreting customer, competitor and market intelligence across the marketing spectrum on customer segmentations and product categories. Excellent analytical skills and a strong sense of structure and logic. Ability to prepare high quality presentation and spreadsheet models. Passionate about providing high quality, cutting edge research and have an understanding of the complex profile of consumers and how business can tap directly into their habits, aspirations and attitudes Hands on experience working on projects encompassing market analysis, organization structures analysis, competitive benchmarking, financial analysis and other best practice studies across industries. Demonstrated ability to work effectively, both independently and in a team environment, in an atmosphere of multiple projects, shifting priorities, and deadline pressures. A confident and concise communicator with excellent relationship & team management skills. Possess a flexible & detail oriented attitude.       Summary of Skills        Familiar with SPSS software. Expert at MS Word, Excel and PowerPoint.
    Proficient in databases such as Gartner, Forrester, Datamonitor, OneSource, Factiva.              Professional Experience      Consultant    April 2012   to   April 2014     Company Name   －   City        Capgemini Consulting is the strategy and transformation consulting brand of Capgemini Group, with over 3000 business consultants serving clients across 5 continents across verticals) Key Responsibilities: Investigate & understand key business issues across verticals and providing clear, concise and timely analysis & recommendations.  Capable of designing research methods and turn research findings, market data and industry knowledge into actionable insights, providing critical thinking, insightful and forward looking statements that impact client's business.  Played a key role in redesigning the company's product offerings in response to a quickly changing market by researching the market extensively and developing comprehensive product profiles.  Employ a wide range of research tools, including primary and secondary sources alongside quantitative and qualitative consumer and business research.  Liaison directly with internal clients for project requirements and provide continued assistance through a consulting project.  Interact with personnel of multiple departments and at various levels in the organization.  Projects Executed: Strategic Research: Conducted independent in-depth and insightful research using databases and open source as a part of consulting engagement teams in developing strategies that affect businesses of global clientele.  Market Study / Competitor Analysis: Analyzing market size and growth, understanding trends and identifying key competitors and study the dynamic issues and events that affect the industry.  Engagements include leading vendor analysis of the SaaS HCM market, Big Data analytics competitor landscape study for an IT major client, market analysis for a green technology manufacturer, etc.  Conducted a vendor analysis and benchmarking study on social media monitoring tools to identify the effectiveness of each of the tools.  Best Practices Study / Benchmarking of Best Practices: Preparation of in-depth case studies of best-in-class organizations and benchmarking of costs, technologies and best practices across multiple verticals.  Projects include strategic, financial and operational benchmarking for a leading mid-stream Oil & Gas Company, social media benchmarking study for a leading pharma company, identify leading digital practices in wealth management industry etc.  Client Interface: Built client relationships as an advisor in order to solve critical business problems.  Supported client needs in a timely and efficient manner demonstrating a sense of urgency, tenacity, and commitment to quality and excellent client management.          Intern    April 2011   to   June 2011     Company Name   －   City        Pantaloon Retail is the flagship company of Future Group, India's retail pioneer, serving over 220 million customers across 85 cities and 60 rural locations through retail formats such as Big Bazaar, Central Malls and HomeTown) Customer Experience Management: Designed and implemented a marketing plan which included market research data from surveys, market analysis and revenue forecasts before and after implementation of the plan.  Commercial evaluation of Activations: Implemented sales promotion plans & new store concepts to generate sales for achievement of targets; coordinated the in-store promotional activities for new releases & special products.  Made recommendations on the financial feasibility of these activations and return on investment, based on the findings.  Activations Management: Responsible for planning and managing the activations at Bangalore Central in order to drive sales.          Intern    April 2008   to   June 2008     Company Name   －   City        The Goldman Sachs is leading global investment banking, securities and investment management firm that provides a wide range of financial services to a substantial and diversified client base that includes corporations, financial institutions, governments and high-net- worth individuals.) Investment Banking Operations: Worked with the team Treasury of Goldman Sachs to understand the key investment banking operations and studied the effectiveness of key investment banking operations.  Recommended a revision of the current threshold amount for inbound and outbound claims (interest claims, market fines and use of funds) resulting in a 58% increase in productivity of treasury team and reducing the total number of claims by 72%.          Education      Master's   :   Business Administration Marketing Management  ,   2012    Christ University      India    Business Administration Marketing Management        Bachelor's   :   Business Management  ,   2010    Christ University      India    Business Management          Additional Information      OTHER ACHIEVEMENTS: Received the 'Rewards and Recognition Award' within one year of service at Capgemini Consulting for outstanding work delivered in the month of April 2013        Skills    Benchmarking, Big Data, business research, Competitor Analysis, concise, Consulting, client management, critical thinking, clientele, Client, clients, databases, designing, financial, funds, Investment Banking, investment management, managing, Analyzing market, market analysis, marketing plan, market
    research, Market, Excel, PowerPoint, MS Word, Oil, personnel, promotion, quality, researching, Research, Retail, sales, securities, SPSS, strategy, Strategic, surveys, Treasury, wealth
    management
    """

    # json_dump = [analyze_skills(resume)]
    # json_dump[0]['type'] = "resume"
    json_dump = []

    from pathlib import Path
    import pandas as pd

    BASE_DIR = Path(__file__).resolve().parents[3]
    csv_path = BASE_DIR / "postings.csv"

    df = pd.read_csv(csv_path)

    # Take 10 random jobs
    sample_jobs = df.sample(n=30, random_state=42)

    # Convert each job posting
    for _, row in sample_jobs.iterrows():
        print(_)
        print(row['title'])
        job_text = row["description"]

        analyzed_job = analyze_skills(job_text)
        analyzed_job["type"] = "job"
        analyzed_job["title"] = row["title"]
        analyzed_job["id"] = row["job_id"]

        json_dump.append(analyzed_job)

    # Save test file
    with open("test_jobs.json", "w") as f:
        json.dump(json_dump, f, indent=4)

    # print(json.dumps(analyze_skills(resume), indent=2))