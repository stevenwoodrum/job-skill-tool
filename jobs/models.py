from django.db import models

class Job(models.Model):
    job_id          = models.CharField(max_length=50, unique=True)
    title           = models.CharField(max_length=255)
    company         = models.CharField(max_length=255)
    location        = models.CharField(max_length=255)
    description     = models.TextField()
    employment_type = models.CharField(max_length=50)
    work_setting    = models.CharField(max_length=50)
