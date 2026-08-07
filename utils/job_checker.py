"""
Checks whether a page is likely to be an actual job posting.
"""

JOB_WORDS = [
    "responsibilities",
    "qualifications",
    "salary",
    "posting date",
    "apply now",
    "position summary",
    "employment type",
    "faculty",
    "instructor",
    "lecturer",
    "adjunct",
    "sessional",
]


def is_job_posting(html):

    text = html.lower()

    score = 0

    for word in JOB_WORDS:

        if word in text:
            score += 1

    return score >= 4