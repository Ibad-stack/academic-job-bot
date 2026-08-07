"""
Writes discovered jobs to a CSV file.
"""

import csv
from pathlib import Path


OUTPUT_FILE = Path("jobs_found.csv")


def write_jobs(jobs):

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Institution",
            "Job Title",
            "URL"
        ])

        for job in jobs:

            writer.writerow([
                job["institution"],
                job["title"],
                job["url"]
            ])

    print(f"\nSaved {len(jobs)} jobs to {OUTPUT_FILE}")