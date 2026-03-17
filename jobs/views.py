from django.http import JsonResponse
from .models import Job

def search_jobs(request):
    query     = request.GET.get("title", "")
    emp_types = request.GET.getlist("type")
    settings  = request.GET.getlist("setting")
    page      = int(request.GET.get("page", 1))
    page_size = 10
    offset    = (page - 1) * page_size

    qs = Job.objects.all()
    if query:
        qs = qs.filter(title__icontains=query)
    if emp_types:
        qs = qs.filter(employment_type__in=emp_types)
    if settings:
        qs = qs.filter(work_setting__in=settings)

    total = qs.count()
    results = list(qs.values(
        "job_id", "title", "company", "location",
        "description", "employment_type", "work_setting"
    )[offset:offset + page_size])

    return JsonResponse({"results": results, "total": total})