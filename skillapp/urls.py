from django.urls import path

from . import views

urlpatterns = [
    path("skill-match/", views.check_skills),
]