import pandas as pd
from django.core.management.base import BaseCommand
from jobs.models import Job

class Command(BaseCommand):
    help = "Load LinkedIn jobs dataset into the database"

    def handle(self, *args, **kwargs):
        self.stdout.write("Reading CSV...")
        df = pd.read_csv("data/postings_clean.csv")

        WORK_TYPE_MAP = {
    "Full-time": "Full-time",
    "Part-time": "Part-time",
    "Contract": "Contract",
    "Internship": "Internship",
    "Temporary": "Contract",
    "Volunteer": "Contract",
    "Other": "Contract",
}
        def get_work_setting(row):
            if row.get("remote_allowed") == 1.0:
                return "Remote"
            if "hybrid" in str(row.get("location", "")).lower():
                return "Hybrid"
            return "On-site"

        df["employment_type"] = df["formatted_work_type"].map(WORK_TYPE_MAP).fillna("Full-time")
        df["work_setting"]    = df.apply(get_work_setting, axis=1)

        jobs = [
            Job(
                job_id=str(row.job_id),
                title=str(row.title),
                company=str(row.company_name),
                location=str(row.location) if str(row.location) != "nan" else "",
                description=str(row.description),
                employment_type=row.employment_type,
                work_setting=row.work_setting,
            )
            for _, row in df.iterrows()
        ]

        Job.objects.bulk_create(jobs, ignore_conflicts=True, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f"Done! Loaded {len(jobs)} jobs"))