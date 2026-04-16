from django.urls import path

from . import views

urlpatterns = [
    path("skill-match/", views.check_skills),
    path("match-resume-job/", views.match_resume_to_job)
]