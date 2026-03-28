from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Create your views here.

from django.http import HttpResponse

from skillapp.services.llm_skill import analyze_job_description

@csrf_exempt
def check_skills(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        body = json.loads(request.body)
        job_description = body.get("job_description", "").strip()
        if not job_description:
            return JsonResponse({"error": "job_description is required"}, status=400)

        result = analyze_job_description(job_description)

        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)