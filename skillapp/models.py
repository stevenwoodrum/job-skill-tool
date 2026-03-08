"""
Three-step guide to making model changes:

1. Change your models (in models.py).

2. Run python manage.py makemigrations to create migrations for those changes

3. Run python manage.py migrate to apply those changes to the database.
"""


from django.db import models

class Job(models.Model):
	job_title = models.CharField(max_length=200)

	def __str__(self):
		return self.job_title

class Resume(models.Model):
	person_name = models.CharField(max_length=200)

class Skill(models.Model):
	skill_name = models.CharField(max_length=200)



