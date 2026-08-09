"""
Academic Job Bot - CSV Writer
Version 1.6
"""

import csv


CSV_FILE = "jobs_found.csv"


FIELDNAMES = [
    "rank",
    "match_score",
    "institution",
    "title",
    "field",
    "position_type",
    "term",
    "deadline",
    "online",
    "location",
    "reason",
    "url",
    "source_url",
]


def write_jobs(jobs):

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="ignore",
        )

        writer.writeheader()

        for job in jobs:

            row = {}

            for field in FIELDNAMES:

                row[field] = job.get(
                    field,
                    ""
                )

            writer.writerow(
                row
            )

    print(
        f"Saved {len(jobs)} "
        f"jobs to {CSV_FILE}"
    )