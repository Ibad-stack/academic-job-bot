"""
Filters links that are likely to be teaching jobs.
"""

KEYWORDS = [
    "accounting",
    "financial accounting",
    "managerial accounting",
    "finance",
    "business",
    "economics",
    "mba",
    "cpa",
    "faculty",
    "associate faculty",
    "adjunct",
    "sessional",
    "lecturer",
    "instructor",
    "facilitator",
    "course developer",
    "course writer",
    "marker",
    "grader",
    "teaching",
]


def filter_job_links(links):

    results = []
    seen = set()

    for link in links:

        text = link["text"].strip()

        if len(text) < 3:
            continue

        searchable = (
            text.lower()
            + " "
            + link["url"].lower()
        )

        if any(keyword in searchable for keyword in KEYWORDS):

            if link["url"] not in seen:
                seen.add(link["url"])
                results.append(link)

    return results