"""
Filters links that are likely to be relevant academic job postings.

The filter deliberately uses the link text for navigation exclusions. A
career/job URL is allowed to contain words such as "careers" or "program"
without causing a valid posting to be rejected.
"""

import re


ROLE_KEYWORDS = (
    "professor",
    "faculty",
    "lecturer",
    "instructor",
    "adjunct",
    "sessional",
    "teaching professor",
    "assistant professor",
    "associate professor",
    "course developer",
    "course writer",
    "course facilitator",
    "facilitator",
    "subject matter expert",
    "marker",
    "grader",
    "assessor",
    "tutor",
    "academic",
)

SUBJECT_KEYWORDS = (
    "accounting",
    "finance",
    "financial accounting",
    "managerial accounting",
    "management accounting",
    "economics",
    "business",
    "management",
    "mba",
)

NAV_EXCLUDE = (
    "skip to",
    "faculty services",
    "faculty & staff",
    "faculty positions",
    "faculty opportunities",
    "faculty & instructors",
    "funding opportunities",
    "staff links",
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
    "admissions",
    "student positions",
    "student career centre",
    "library",
    "news",
    "blog",
    "about",
    "tuition",
    "course calendar",
    "current openings",
    "current opportunities",
    "job postings",
    "job opportunities",
    "employment opportunities",
    "academic opportunities",
    "view all available jobs",
    "view positions",
    "associate faculty / contractor opportunities",
)

JOB_URL_HINTS = (
    "/job",
    "/jobs",
    "/posting",
    "/position",
    "/opportunity",
    "/opportunities",
    "/careers/",
    "/career/",
    "/hr/ats/",
    "workday",
    "dayforce",
    "interfolio",
)


def _clean(value):
    return re.sub(r"\s+", " ", value or "").strip().lower()


def _is_navigation_title(title):
    return any(phrase in title for phrase in NAV_EXCLUDE)


def is_job_link(link):
    """Return True when a link looks like an actual academic job posting."""

    title = _clean(link.get("text"))
    url = _clean(link.get("url"))

    if not title or not url or _is_navigation_title(title):
        return False

    role_match = any(keyword in title for keyword in ROLE_KEYWORDS)
    subject_match = any(keyword in title for keyword in SUBJECT_KEYWORDS)
    job_url_match = any(hint in url for hint in JOB_URL_HINTS)

    # A role + subject is a strong match. A role + recognizable job-board URL
    # is also useful because many postings have generic titles such as
    # "Instructor" or "Faculty Member".
    return role_match and (subject_match or job_url_match)


def filter_job_links(links):
    results = []
    seen = set()

    for link in links:
        if not is_job_link(link):
            continue

        url = link["url"].strip()
        if url in seen:
            continue

        seen.add(url)
        results.append({
            "text": link["text"].strip(),
            "url": url,
        })

    return results
