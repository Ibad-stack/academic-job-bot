"""
Filters links that are likely to be relevant academic job postings.
"""

INCLUDE = [
    "accounting",
    "finance",
    "financial accounting",
    "managerial accounting",
    "management accounting",
    "economics",
    "business instructor",
    "business lecturer",
    "business professor",
    "business faculty",
    "mba instructor",
    "mba lecturer",
    "mba professor",
    "mba faculty",
    "adjunct",
    "sessional",
    "lecturer",
    "instructor",
    "professor",
    "associate faculty",
    "course developer",
    "course writer",
    "course facilitator",
    "facilitator",
    "subject matter expert",
    "marker",
    "grader",
    "assessor",
]

EXCLUDE = [
    "skip to",
    "faculty services",
    "faculty & staff",
    "funding opportunities",
    "staff links",
    "careers",
    "career development",
    "current employees",
    "new employees",
    "tips for applying",
    "how to apply",
    "benefits",
    "wellness",
    "testimonials",
    "contact",
    "faq",
    "eligibility",
    "directory",
    "program",
    "programs",
    "admissions",
    "student",
    "library",
    "news",
    "blog",
    "about",
    "tuition",
    "course calendar",
]


def filter_job_links(links):

    results = []
    seen = set()

    for link in links:

        title = link.get("text", "").strip()
        url = link.get("url", "").strip()

        if not title or not url:
            continue

        searchable = (
            title.lower()
            + " "
            + url.lower()
        )

        # Remove obvious non-job pages
        if any(word in searchable for word in EXCLUDE):
            continue

        # Keep only pages related to your target areas/roles
        if not any(word in searchable for word in INCLUDE):
            continue

        if url in seen:
            continue

        seen.add(url)

        results.append({
            "text": title,
            "url": url
        })

    return results