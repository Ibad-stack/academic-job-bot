"""
Only keep links that are likely to be job postings.
"""

TITLE_KEYWORDS = [
    "accounting",
    "finance",
    "economics",
    "cpa",
]

JOB_KEYWORDS = [
    "job",
    "jobs",
    "career",
    "careers",
    "employment",
    "position",
    "vacancy",
    "vacancies",
    "posting",
    "faculty",
    "associate faculty",
    "adjunct",
    "sessional",
    "lecturer",
    "instructor",
    "facilitator",
]


def filter_job_links(links):
    results = []
    seen = set()

    for link in links:
        text = link["text"].strip().lower()
        url = link["url"].lower()

        searchable = text + " " + url

        # Ignore obvious non-job pages
        if any(x in searchable for x in [
            "program",
            "degree",
            "mba",
            "bachelor",
            "master of",
            "directory",
            "about",
            "admissions",
            "tuition",
        ]):
            continue

        # Must contain at least one job word
        if not any(word in searchable for word in JOB_KEYWORDS):
            continue

        # Remove duplicates
        if url not in seen:
            seen.add(url)
            results.append(link)

    return results