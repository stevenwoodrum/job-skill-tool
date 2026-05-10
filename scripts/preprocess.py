import pandas as pd
import numpy as np

df = pd.read_csv("data/postings.csv")

print("Before cleaning:", len(df), "rows")

#drop rows missing the important stuff
df = df.dropna(subset=["title", "description", "company_name"])

# deduplicate by job ID
df = df.drop_duplicates(subset=["job_id"])

# deduplicate by title + company + location
df = df.drop_duplicates(subset=["title", "company_name", "location"], keep="first")

# standardize employment types
WORK_TYPE_MAP = {
    "Full-time": "Full-time",
    "Part-time": "Part-time",
    "Contract": "Contract",
    "Internship": "Internship",
    "Temporary": "Contract",
    "Volunteer": "Contract",
    "Other": "Contract",
}
df["formatted_work_type"] = df["formatted_work_type"].map(WORK_TYPE_MAP).fillna("Full-time")

#keep only the 7 key fields
df = df[["job_id", "title", "company_name", "location", "description", "formatted_work_type", "remote_allowed"]]

# save
df.to_csv("data/postings_clean.csv", index=False)
