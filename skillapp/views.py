from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import pdfplumber
from docx import Document

# Create your views here.

from django.http import HttpResponse

from skillapp.services.llm_skill import analyze_skills
from skillapp.services.skill_match import SkillMatcher, OllamaEmbeddingProvider

embedding_provider = OllamaEmbeddingProvider()
matcher = SkillMatcher(embedding_provider, threshold=0.60)

def extract_pdf_text(file_obj):
    text = ""
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_docx_text(file_obj):
    doc = Document(file_obj)
    text = "\n".join(p.text for p in doc.paragraphs)
    return text.strip()

@csrf_exempt
def check_skills(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        if request.FILES:
            uploaded_file = request.FILES.get("file")

            if not uploaded_file:
                return JsonResponse(
                    {"error": "Upload a file using field name 'file'"},
                    status=400
                )

            filename = uploaded_file.name.lower()
            extracted_text = ""

            try:
                if filename.endswith(".pdf"):
                    extracted_text = extract_pdf_text(uploaded_file)

                elif filename.endswith(".docx"):
                    extracted_text = extract_docx_text(uploaded_file)

                else:
                    return JsonResponse(
                        {"error": "Only .pdf and .docx files are supported"},
                        status=400
                    )

            except Exception:
                extracted_text = ""

            result = analyze_skills(extracted_text)
            return JsonResponse(result)

        body = json.loads(request.body)
        job_description = body.get("job_description", "").strip()

        if not job_description:
            return JsonResponse(
                {"error": "job_description is required"},
                status=400
            )

        result = analyze_skills(job_description)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def match_resume_to_job(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    try:
        body = json.loads(request.body)

        resume = body.get("resume", [])
        job = body.get("job", [])

        if not isinstance(resume, list) or not resume:
            return JsonResponse({"error": "resume must be a non-empty list"}, status=400)

        if not isinstance(job, list) or not job:
            return JsonResponse({"error": "job must be a non-empty list"}, status=400)

        resume_skills = [
            skill["skill"]
            for skill in resume[0]["skills"]
            if skill.get("skill")
        ]

        job_skills = [
            skill["skill"]
            for skill in job[0]["skills"]
            if skill.get("skill")
        ]

        job_evidence = [
            skill.get("evidence", "")
            for skill in job[0]["skills"]
            if skill.get("skill")
        ]

        report = matcher.match_skills(
            resume_skills,
            job_skills,
            job_evidence
        )

        return JsonResponse(report)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
