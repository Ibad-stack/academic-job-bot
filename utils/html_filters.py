"""
Filters links that are likely to lead to job listings.
"""

IGNORE = [
    "benefits",
    "faq",
    "contact",
    "eligibility",
    "directory",
    "program",
    "admissions",
    "student",
    "library",
    "news",
    "wellness",
    "leave",
    "rights",
    "testimonials",
    "about",
    "privacy",
    "accessibility",
]

KEEP = [
    "career",
    "careers",
    "job",
    "jobs",
    "employment",
    "position",
    "positions",
    "posting",
    "vacancy",
    "vacancies",
    "faculty",
    "adjunct",
    "sessional",
    "instructor",
    "lecturer",
    "associate faculty",
]


def keep_link(text, url):

    value = (text + " " + url).lower()

    if any(word in value for word in IGNORE):
        return False

    if any(word in value for word in KEEP):
        return True

    return False