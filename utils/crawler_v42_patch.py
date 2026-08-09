"""v4.2 reliability patches for the Academic Job Bot.

This module intentionally wraps v4.1 instead of replacing it. It fixes
pipeline-level discovery/extraction problems while keeping v4.1's relevance
classifier and institution-specific crawlers intact.
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag
import re


def norm(url):
    return urldefrag((url or '').strip())[0]


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def links(base, html):
    """Extract normal links AND embedded job-board iframes."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    seen = set()

    def add(url, label):
        url = norm(urljoin(base, url))
        if url and url not in seen:
            seen.add(url)
            out.append((url, clean(label)))

    for anchor in soup.find_all("a", href=True):
        add(anchor["href"], anchor.get_text(" ", strip=True))

    for iframe in soup.find_all("iframe", src=True):
        src = iframe.get("src", "")
        label = iframe.get("title") or iframe.get("aria-label") or "Embedded career/job board"
        add(src, label)

    return out


def discovery_link_kind(u, label):
    """Be permissive about discovery; leave relevance to final classification."""
    q = clean(f"{u} {label}").lower()

    if "/job/" in q or "myworkdayjobs.com" in q:
        return "job"
    if any(x in q for x in ("/faculty-vacancies/", "/job-posting/", "/job-postings/", "/academic-job/", "/vacancies/", "/vacancy/")):
        return "job"
    if re.search(r"/20\d{2}/[^/]*(?:professor|lecturer|instructor|sessional|faculty)", q, re.I):
        return "job"
    if re.search(r"/20\d{2}/[^/]*(?:accounting|finance|business|management|audit|tax)", q, re.I):
        return "job"
    if ".pdf" in q and any(x in q for x in ("professor", "lecturer", "instructor", "sessional", "faculty", "accounting", "finance", "business", "management", "audit", "tax", "employment", "job-posting", "job posting", "teaching")):
        return "job"

    source_terms = (
        "career", "careers", "employment", "faculty", "academic", "job posting", "job postings", "job-posting",
        "positions", "position", "sessional", "adjunct", "contract instructor", "contract teaching",
        "teaching opportunity", "teaching opportunities", "open learning", "continuing education",
        "associate faculty", "contractor opportunities", "view positions", "view all available jobs",
        "current openings", "current opportunities", "faculty & instructors", "faculty instructors",
        "faculty positions", "faculty opportunities", "teaching positions", "teaching opportunities"
    )
    subject_terms = (
        "accounting", "accountancy", "finance", "financial management", "business", "commerce", "management",
        "audit", "assurance", "tax", "taxation", "cpa", "entrepreneurship", "marketing", "strategy",
        "supply chain", "mba"
    )
    teaching_terms = (
        "professor", "lecturer", "instructor", "sessional", "adjunct", "teaching", "faculty",
        "academic appointment", "open learning", "associate faculty"
    )
    source = any(x in q for x in source_terms)
    subject = any(x in q for x in subject_terms)
    teaching = any(x in q for x in teaching_terms)
    if source and (subject or teaching or "view positions" in q or "current openings" in q):
        return "source"
    return ""


def section_jobs_from_html(url, html):
    """Extract Waterloo-style jobs and preserve exact posting metadata."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    appointment_re = re.compile(
        r"\b(?:probationary\s+)?(?:assistant|associate|full|term)\s+professor\b|"
        r"\b(?:sessional|contract|course)\s+(?:lecturer|instructor)\b|\bteaching\s+stream\b", re.I
    )

    for h in headings:
        title = clean(h.get_text(" ", strip=True))
        if not title or len(title) > 320 or not appointment_re.search(title):
            continue

        # Work from the parent section rather than h.next_elements. This avoids
        # accidentally stopping on nested navigation headings and captures the
        # full posting, including compensation and deadline.
        section = h.parent
        while section is not None and len(clean(section.get_text(" ", strip=True))) < 500:
            section = section.parent
        body = clean(section.get_text(" ", strip=True) if section is not None else "")

        # If the parent is the entire page, isolate text between this heading
        # and the next appointment heading.
        if section is None or len(body) > 25000:
            parts = []
            for node in h.next_elements:
                if getattr(node, "name", None) in ("h1", "h2", "h3", "h4") and node is not h:
                    other = clean(node.get_text(" ", strip=True))
                    if appointment_re.search(other):
                        break
                if getattr(node, "name", None) in ("script", "style", "noscript"):
                    continue
                if hasattr(node, "get_text"):
                    text = clean(node.get_text(" ", strip=True))
                    if text and text not in parts[-3:]:
                        parts.append(text)
            body = clean(" ".join(parts))

        # Normalize Waterloo's literal HTML superscript extraction, e.g.
        # "July 10^{th}, 2026" -> "July 10th, 2026".
        body = re.sub(r"\s*\^\s*\{\s*(st|nd|rd|th)\s*\}", r"\1", body, flags=re.I)
        body = re.sub(r"\s*\^\s*\{\s*(st|nd|rd|th)\s*\}", r"\1", title, flags=re.I) + " " + body

        if len(body) < 120:
            continue
        out.append((url, title, body))

    seen = set()
    result = []
    for item in out:
        key = (item[1].lower(), item[0])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def deadline_v42(text):
    """Robust deadline parser for superscript HTML/PDF date forms."""
    text = clean(text)
    if not text:
        return ""
    normalized = re.sub(r"\s*\^\s*\{\s*(st|nd|rd|th)\s*\}", r"\1", text, flags=re.I)
    normalized = re.sub(r"\s*\^\s*(st|nd|rd|th)\b", r"\1", normalized, flags=re.I)
    patterns = [
        r"(?:application\s+deadline|closing\s+date|applications?\s+close|apply\s+by|deadline)\s*[:\-]?\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*20\d{2})",
        r"(?:application\s+deadline|closing\s+date|applications?\s+close|apply\s+by|deadline)\s*[:\-]?\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+20\d{2})",
    ]
    for pattern in patterns:
        m = re.search(pattern, normalized, re.I)
        if m:
            return clean(m.group(1))
    return ""


def field_v42(text):
    """Prefer explicit title/subject evidence over university boilerplate."""
    text = clean(text)
    lower = text.lower()
    # The first sentence/title is highly discriminative for a posting.
    title = lower[:500]
    if re.search(r"\b(financial accounting|managerial accounting|management accounting|accounting|accountancy|audit|auditing|tax|taxation|assurance)\b", title):
        return "Accounting"
    if re.search(r"\b(corporate finance|financial management|entrepreneurial finance|finance|investments)\b", title):
        return "Finance"
    if re.search(r"\b(business administration|business|commerce|management|strategy|marketing|entrepreneurship|mba|economics)\b", title):
        return "Business"
    return None


def salary_v42(text):
    """Capture annual salary ranges as well as course-based pay."""
    text = clean(text)
    m = re.search(r"\$[\d,]+(?:\.\d{2})?\s*(?:to|[-–—])\s*\$[\d,]+(?:\.\d{2})?", text, re.I)
    if m and any(x in text[max(0, m.start()-180):m.end()+180].lower() for x in ("salary", "compensation", "starting")):
        return clean(m.group(0))
    return ""


def apply(crawler):
    """Monkey-patch v4.1 and return the patched module."""
    crawler.VERSION = "4.2"
    crawler.links = links
    crawler.discovery_link_kind = discovery_link_kind
    crawler.section_jobs_from_html = section_jobs_from_html

    # Fix three v4.1 extraction weaknesses without touching crawler.py.
    old_make = crawler.make
    def make_v42(inst, url, title, body, source):
        normalized_body = re.sub(r"\s*\^\s*\{\s*(st|nd|rd|th)\s*\}", r"\1", clean(body), flags=re.I)
        result = old_make(inst, url, title, normalized_body, source)
        if result:
            parsed_deadline = deadline_v42(normalized_body)
            if parsed_deadline:
                result["deadline"] = parsed_deadline
                try:
                    dt = crawler.parse_date_string(parsed_deadline)
                    if dt and dt < crawler.date.today():
                        result["application_status"] = "EXPIRED"
                    elif result.get("application_status") == "EXPIRED":
                        result["application_status"] = "Application available"
                except Exception:
                    pass
            annual_salary = salary_v42(normalized_body)
            if annual_salary and not result.get("salary"):
                result["salary"] = annual_salary
            explicit_field = field_v42(title)
            if explicit_field:
                result["field"] = explicit_field
        return result
    crawler.make = make_v42
    return crawler
