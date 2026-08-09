"""
Academic Job Bot
Job Filter / Job Analyzer
Version 1.8

Designed for:
    Accounting
    Finance
    Business
    Economics
    CPA education

The goal is NOT simply to find anything containing
"business" or "professor".

The goal is to identify academic teaching opportunities
that are realistically relevant to an Accounting / Finance /
Business instructor.
"""

import re


# =========================================================
# TARGET SUBJECTS
# =========================================================

ACCOUNTING_TERMS = [
    "accounting",
    "accountancy",
    "financial accounting",
    "management accounting",
    "managerial accounting",
    "auditing",
    "audit",
    "tax accounting",
    "taxation",
    "forensic accounting",
    "accounting information systems",
    "accounting education",
    "financial reporting",
    "cpa",
    "chartered professional accountant",
]

FINANCE_TERMS = [
    "finance",
    "financial management",
    "corporate finance",
    "investments",
    "investment management",
    "portfolio management",
    "financial markets",
    "banking",
    "risk management",
    "financial economics",
]

BUSINESS_TERMS = [
    "business administration",
    "business management",
    "business",
    "management",
    "strategic management",
    "strategy",
    "entrepreneurship",
    "organizational behaviour",
    "organizational behavior",
    "marketing",
    "human resources",
    "operations management",
    "supply chain",
]

ECONOMICS_TERMS = [
    "economics",
    "economic",
    "microeconomics",
    "macroeconomics",
]


# =========================================================
# VERY STRONG NEGATIVE FIELDS
# =========================================================

NEGATIVE_FIELDS = [

    "nursing",
    "clinical psychology",
    "psychology",
    "chemistry",
    "physics",
    "biology",
    "engineering",
    "mechanical engineering",
    "electrical engineering",
    "computer science",
    "software engineering",
    "social work",
    "speech-language",
    "speech language",
    "kinesiology",
    "health sciences",
    "medicine",
    "epidemiology",
    "public health",
    "fine arts",
    "music",
    "history",
    "politics",
    "political science",
    "french",
    "linguistics",
    "literature",
    "geography",
    "mathematics",
    "statistics",
    "curriculum",
    "education",
    "school mental health",
    "journalism",
    "communications",
    "communication studies",
    "earth sciences",
    "geology",
    "mineral exploration",
]


# =========================================================
# FALSE-POSITIVE MANAGEMENT TERMS
#
# These words frequently cause unrelated jobs to be
# incorrectly classified as Business.
# =========================================================

FALSE_BUSINESS_CONTEXTS = [

    "resource management",
    "natural resource management",
    "mineral resource management",
    "resource management in earth sciences",
    "health management",
    "healthcare management",
    "laboratory management",
    "research management",
    "project management in engineering",
    "construction management",
    "environmental management",
    "water management",
    "forest management",
    "wildlife management",
]


# =========================================================
# GENERIC PAGES
# =========================================================

GENERIC_TITLES = [

    "faculty positions",
    "faculty opportunities",
    "faculty careers",
    "faculty recruitment",
    "faculty resources",
    "faculty affairs",
    "faculty hiring",
    "academic careers",
    "academic opportunities",
    "academic positions",
    "career opportunities",
    "career portal",
    "current opportunities",
    "current openings",
    "job opportunities",
    "job postings",
    "employment opportunities",
    "how to apply",
    "application information",
    "contract instructors",
    "contract instructor hiring",
    "hiring examples",
    "frequently asked questions",
    "faq",
    "our instructors",
    "meet our faculty",
    "faculty website",
    "faculty and staff",
    "non-academic positions",
    "career opportunities with york",
    "explore career opportunities with york",
    "career opportunities",
    "sessional positions",
    "faculty positions",
]


# =========================================================
# JOB TITLE PREFIXES THAT ARE NOT THE ACTUAL TITLE
# =========================================================

BAD_TITLE_PREFIXES = [

    "read news post",
    "more info",
    "more information",
    "click here",
    "view details",
    "learn more",
]


# =========================================================
# POSITION TYPES
# =========================================================

POSITION_PATTERNS = [

    (
        "Sessional",
        [
            "sessional",
            "sessional member",
            "sessional lecturer",
        ],
    ),

    (
        "Contract Instructor",
        [
            "contract instructor",
            "contract lecturer",
            "contract professor",
            "contract faculty",
        ],
    ),

    (
        "Adjunct",
        [
            "adjunct",
        ],
    ),

    (
        "Teaching Professor",
        [
            "teaching professor",
            "assistant teaching professor",
            "associate teaching professor",
            "teaching stream",
            "teaching-stream",
        ],
    ),

    (
        "Lecturer",
        [
            "lecturer",
        ],
    ),

    (
        "Instructor",
        [
            "instructor",
        ],
    ),

    (
        "Course Developer",
        [
            "course developer",
            "course writer",
            "course facilitator",
        ],
    ),

    (
        "Academic Assessor / Marker",
        [
            "academic assessor",
            "marker",
            "grader",
        ],
    ),

    (
        "Tenure-track Professor",
        [
            "tenure-track",
            "tenure track",
        ],
    ),

]


# =========================================================
# NORMALIZE
# =========================================================

def normalize(text):

    if not text:
        return ""

    text = str(text)

    text = text.replace(
        "\xa0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip().lower()


# =========================================================
# CLEAN TITLE
# =========================================================

def clean_title(title):

    title = str(
        title or ""
    ).strip()

    # Collapse whitespace.
    title = re.sub(
        r"\s+",
        " ",
        title
    )

    lower = title.lower()

    for prefix in BAD_TITLE_PREFIXES:

        if lower.startswith(prefix):

            title = title[
                len(prefix):
            ].strip()

            break

    # Remove common junk separators.
    title = title.strip(
        " -:|"
    )

    return title


# =========================================================
# GENERIC PAGE?
# =========================================================

def is_generic_page(title):

    title = normalize(
        clean_title(title)
    )

    if title in GENERIC_TITLES:

        return True

    # Very short navigation titles.
    if title in {
        "faculty",
        "professor",
        "instructor",
        "lecturer",
        "sessional",
        "adjunct",
        "contract",
    }:

        return True

    return False


# =========================================================
# NEGATIVE FIELD
# =========================================================

def find_negative_field(
    title,
    body,
    url,
):

    title = normalize(title)

    body = normalize(body)

    url = normalize(url)

    # Title is strongest.
    for term in NEGATIVE_FIELDS:

        if term in title:

            return term

    # URL is also strong.
    for term in NEGATIVE_FIELDS:

        if term in url:

            return term

    return ""


# =========================================================
# DETECT SUBJECT
# =========================================================

def detect_subject(
    title,
    body,
    url,
):

    title = normalize(title)

    body = normalize(body)

    url = normalize(url)

    # -----------------------------------------------------
    # First: hard reject unrelated titles.
    # -----------------------------------------------------

    negative = find_negative_field(
        title,
        body,
        url,
    )

    if negative:

        return (
            "",
            0,
            f"Unrelated field in title/URL: {negative}"
        )

    # -----------------------------------------------------
    # Score target disciplines.
    # -----------------------------------------------------

    scores = {

        "Accounting": 0,
        "Finance": 0,
        "Business": 0,
        "Economics": 0,

    }

    # -----------------------------------------------------
    # Accounting
    # -----------------------------------------------------

    for term in ACCOUNTING_TERMS:

        if term in title:

            scores[
                "Accounting"
            ] += 50

        elif term in url:

            scores[
                "Accounting"
            ] += 35

        elif term in body:

            scores[
                "Accounting"
            ] += min(
                body.count(term) * 3,
                15
            )

    # -----------------------------------------------------
    # Finance
    # -----------------------------------------------------

    for term in FINANCE_TERMS:

        if term in title:

            scores[
                "Finance"
            ] += 50

        elif term in url:

            scores[
                "Finance"
            ] += 35

        elif term in body:

            scores[
                "Finance"
            ] += min(
                body.count(term) * 3,
                15
            )

    # -----------------------------------------------------
    # Business
    # -----------------------------------------------------

    for term in BUSINESS_TERMS:

        if term in title:

            scores[
                "Business"
            ] += 35

        elif term in url:

            scores[
                "Business"
            ] += 20

        elif term in body:

            scores[
                "Business"
            ] += min(
                body.count(term) * 2,
                10
            )

    # -----------------------------------------------------
    # Economics
    # -----------------------------------------------------

    for term in ECONOMICS_TERMS:

        if term in title:

            scores[
                "Economics"
            ] += 40

        elif term in url:

            scores[
                "Economics"
            ] += 30

        elif term in body:

            scores[
                "Economics"
            ] += min(
                body.count(term) * 3,
                12
            )

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # "Resource Management" etc. should NOT become
    # Business merely because "management" appears.
    # -----------------------------------------------------

    for false_context in FALSE_BUSINESS_CONTEXTS:

        if false_context in title:

            scores[
                "Business"
            ] = 0

    # Earth Sciences etc. are always rejected unless
    # Accounting / Finance / Business is explicitly in
    # the actual title.
    if any(
        field in title
        for field in NEGATIVE_FIELDS
    ):

        explicit_business = any(
            term in title
            for term in (
                ACCOUNTING_TERMS
                + FINANCE_TERMS
            )
        )

        if not explicit_business:

            return (
                "",
                0,
                "Unrelated academic discipline"
            )

    best_subject = max(
        scores,
        key=scores.get
    )

    best_score = scores[
        best_subject
    ]

    # -----------------------------------------------------
    # Require meaningful evidence.
    # -----------------------------------------------------

    if best_score < 20:

        return (
            "",
            0,
            "No Accounting / Finance / Business subject detected"
        )

    return (
        best_subject,
        best_score,
        "Target discipline detected"
    )


# =========================================================
# POSITION TYPE
# =========================================================

def detect_position_type(
    title,
    body,
    url,
):

    title = normalize(title)

    body = normalize(body)

    url = normalize(url)

    # -----------------------------------------------------
    # Sessional MUST be checked before professor.
    # -----------------------------------------------------

    if (
        "sessional" in title
        or "sessional" in url
    ):

        return "Sessional"

    # -----------------------------------------------------
    # Contract
    # -----------------------------------------------------

    if any(
        term in title
        for term in [
            "contract instructor",
            "contract lecturer",
            "contract professor",
            "contract faculty",
        ]
    ):

        return "Contract Instructor"

    # -----------------------------------------------------
    # Teaching stream
    # -----------------------------------------------------

    if any(
        term in title
        for term in [
            "teaching stream",
            "teaching-stream",
            "teaching professor",
            "assistant teaching professor",
            "associate teaching professor",
        ]
    ):

        return "Teaching Professor"

    # -----------------------------------------------------
    # Adjunct
    # -----------------------------------------------------

    if "adjunct" in title:

        return "Adjunct"

    # -----------------------------------------------------
    # Explicit tenure-track
    # -----------------------------------------------------

    if (
        "tenure-track" in title
        or "tenure track" in title
    ):

        return "Tenure-track Professor"

    # -----------------------------------------------------
    # TERM APPOINTMENT
    #
    # This is critical:
    #
    # "Term Assistant Professor" is NOT tenure-track.
    # -----------------------------------------------------

    if re.search(
        r"\bterm\s+(assistant|associate|full)\s+professor\b",
        title,
        flags=re.IGNORECASE
    ):

        return "Term Professor"

    # -----------------------------------------------------
    # Lecturer
    # -----------------------------------------------------

    if "lecturer" in title:

        return "Lecturer"

    # -----------------------------------------------------
    # Instructor
    # -----------------------------------------------------

    if "instructor" in title:

        return "Instructor"

    # -----------------------------------------------------
    # Professor
    # -----------------------------------------------------

    if any(
        term in title
        for term in [
            "assistant professor",
            "associate professor",
            "full professor",
            "professor",
        ]
    ):

        return "Professor"

    # -----------------------------------------------------
    # Course development
    # -----------------------------------------------------

    if any(
        term in title
        for term in [
            "course developer",
            "course writer",
            "course facilitator",
        ]
    ):

        return "Course Developer"

    return "Academic / Teaching"


# =========================================================
# COURSE / TEACHING FIT
# =========================================================

def detect_course_fit(
    title,
    body,
):

    text = normalize(
        title
        + " "
        + body
    )

    matches = []

    course_terms = [

        "financial accounting",
        "introductory accounting",
        "introductory financial accounting",
        "managerial accounting",
        "management accounting",
        "auditing",
        "taxation",
        "tax",
        "financial reporting",
        "corporate finance",
        "finance",
        "investments",
        "financial management",
        "business administration",
        "business management",
        "mba",
        "accounting",
        "cpa",
        "economics",
        "management",
        "strategy",
        "marketing",
        "organizational behaviour",
        "organizational behavior",

    ]

    for term in course_terms:

        if term in text:

            matches.append(
                term
            )

    # Preserve order while removing duplicates.
    result = []

    seen = set()

    for item in matches:

        if item not in seen:

            seen.add(item)

            result.append(
                item
            )

    return result[:12]


# =========================================================
# ONLINE
# =========================================================

def detect_online(
    title,
    body,
):

    text = normalize(
        title
        + " "
        + body
    )

    terms = [

        "online",
        "remote",
        "distance education",
        "distance learning",
        "open learning",
        "online teaching",
        "online course",
        "virtual",

    ]

    return any(
        term in text
        for term in terms
    )


# =========================================================
# TERM
# =========================================================

def detect_term(
    text
):

    text = normalize(
        text
    )

    terms = [

        "fall 2026",
        "fall/winter 2026/2027",
        "fall/winter 2026",
        "winter 2027",
        "winter 2026",
        "spring 2027",
        "summer 2027",
        "summer 2026",
        "2026/2027",
        "2026-2027",

    ]

    for term in terms:

        if term in text:

            return term.title()

    return ""


# =========================================================
# DEADLINE
# =========================================================

def detect_deadline(
    text
):

    text = normalize(
        text
    )

    patterns = [

        r"(?:application deadline|applications? due|apply by|closing date|deadline)"
        r"\s*[:\-]?\s*"
        r"([a-z]+\s+\d{1,2},?\s+\d{4})",

        r"(?:application deadline|applications? due|apply by|closing date|deadline)"
        r"\s*[:\-]?\s*"
        r"(\d{1,2}\s+[a-z]+\s+\d{4})",

        r"(?:application deadline|applications? due|apply by|closing date|deadline)"
        r"\s*[:\-]?\s*"
        r"(\d{4}-\d{2}-\d{2})",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            return match.group(
                1
            ).strip()

    return ""


# =========================================================
# SCORE
# =========================================================

def calculate_score(
    field,
    position_type,
    title,
    course_fit,
    online,
):

    title = normalize(
        title
    )

    score = 0

    # -----------------------------------------------------
    # FIELD
    # -----------------------------------------------------

    if field == "Accounting":

        score += 50

    elif field == "Finance":

        score += 48

    elif field == "Business":

        score += 35

    elif field == "Economics":

        score += 30

    # -----------------------------------------------------
    # EXACT TITLE FIT
    # -----------------------------------------------------

    if "accounting" in title:

        score += 15

    elif "finance" in title:

        score += 14

    elif "financial" in title:

        score += 12

    elif "business" in title:

        score += 8

    # -----------------------------------------------------
    # POSITION
    # -----------------------------------------------------

    position_points = {

        "Sessional": 25,

        "Contract Instructor": 25,

        "Adjunct": 24,

        "Teaching Professor": 22,

        "Lecturer": 21,

        "Instructor": 21,

        "Term Professor": 18,

        "Professor": 12,

        "Tenure-track Professor": 10,

        "Course Developer": 20,

        "Academic Assessor / Marker": 18,

    }

    score += position_points.get(
        position_type,
        8
    )

    # -----------------------------------------------------
    # COURSE FIT
    # -----------------------------------------------------

    if course_fit:

        accounting_fit = any(
            term in course_fit
            for term in [
                "financial accounting",
                "introductory accounting",
                "introductory financial accounting",
                "managerial accounting",
                "management accounting",
                "accounting",
                "cpa",
                "auditing",
                "taxation",
                "financial reporting",
            ]
        )

        finance_fit = any(
            term in course_fit
            for term in [
                "corporate finance",
                "finance",
                "financial management",
                "investments",
            ]
        )

        if accounting_fit:

            score += 10

        elif finance_fit:

            score += 9

        else:

            score += 4

    # -----------------------------------------------------
    # ONLINE
    # -----------------------------------------------------

    if online:

        score += 3

    return min(
        score,
        100
    )


# =========================================================
# MAIN ANALYZER
# =========================================================

def analyze_job(
    title,
    url,
    page_text="",
    url_text="",
):

    title = clean_title(
        title
    )

    url = str(
        url or ""
    )

    page_text = str(
        page_text or ""
    )

    url_text = str(
        url_text or ""
    )

    # -----------------------------------------------------
    # Generic pages
    # -----------------------------------------------------

    if is_generic_page(
        title
    ):

        return {

            "relevant": False,

            "match_score": 0,

            "field": "",

            "position_type": "",

            "course_fit": [],

            "term": "",

            "deadline": "",

            "online": "No",

            "reason":
                "Generic career/information page",

        }

    # -----------------------------------------------------
    # Subject
    # -----------------------------------------------------

    (
        field,
        subject_score,
        reason,
    ) = detect_subject(

        title,
        page_text,
        url_text,

    )

    if not field:

        return {

            "relevant": False,

            "match_score": 0,

            "field": "",

            "position_type": "",

            "course_fit": [],

            "term": "",

            "deadline": "",

            "online": "No",

            "reason": reason,

        }

    # -----------------------------------------------------
    # Position
    # -----------------------------------------------------

    position_type = detect_position_type(

        title,
        page_text,
        url_text,

    )

    # -----------------------------------------------------
    # Course fit
    # -----------------------------------------------------

    course_fit = detect_course_fit(

        title,
        page_text,

    )

    # -----------------------------------------------------
    # Details
    # -----------------------------------------------------

    combined = " ".join(

        [
            title,
            url_text,
            page_text,
        ]

    )

    term = detect_term(
        combined
    )

    deadline = detect_deadline(
        combined
    )

    online = detect_online(
        title,
        page_text,
    )

    # -----------------------------------------------------
    # Score
    # -----------------------------------------------------

    score = calculate_score(

        field=field,

        position_type=position_type,

        title=title,

        course_fit=course_fit,

        online=online,

    )

    # Subject evidence bonus.
    score += min(
        subject_score // 10,
        10
    )

    score = min(
        score,
        100
    )

    return {

        "relevant": True,

        "match_score": score,

        "field": field,

        "position_type":
            position_type,

        "course_fit":
            course_fit,

        "term":
            term,

        "deadline":
            deadline,

        "online":
            "Yes" if online else "No",

        "reason":
            reason,

    }