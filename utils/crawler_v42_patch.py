"""v4.2 reliability patches for the Academic Job Bot.

This module intentionally wraps v4.1 instead of replacing it.  It fixes
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
        label = (
            iframe.get("title")
            or iframe.get("aria-label")
            or "Embedded career/job board"
        )
        add(src, label)

    return out


def discovery_link_kind(u, label):
    """Be permissive about discovery; leave relevance to final classification."""
    q = clean(f"{u} {label}").lower()

    if "/job/" in q or "myworkdayjobs.com" in q:
        return "job"

    if any(x in q for x in (
        "/faculty-vacancies/", "/job-posting/", "/job-postings/",
        "/academic-job/", "/vacancies/", "/vacancy/"
    )):
        return "job"

    if re.search(r"/20\d{2}/[^/]*(?:professor|lecturer|instructor|sessional|faculty)", q, re.I):
        return "job"
    if re.search(r"/20\d{2}/[^/]*(?:accounting|finance|business|management|audit|tax)", q, re.I):
        return "job"

    if ".pdf" in q and any(x in q for x in (
        "professor", "lecturer", "instructor", "sessional", "faculty",
        "accounting", "finance", "business", "management", "audit", "tax",
        "employment", "job-posting", "job posting", "teaching"
    )):
        return "job"

    # Source-page signals deliberately include generic navigation labels.
    # These pages are inspected and then filtered by classify_opportunity().
    source_terms = (
        "career", "careers", "employment", "faculty", "academic",
        "job posting", "job postings", "job-posting", "positions",
        "position", "sessional", "adjunct", "contract instructor",
        "contract teaching", "teaching opportunity", "teaching opportunities",
        "open learning", "continuing education", "associate faculty",
        "contractor opportunities", "view positions", "view all available jobs",
        "current openings", "current opportunities", "faculty & instructors",
        "faculty instructors", "faculty positions", "faculty opportunities",
        "teaching positions", "teaching opportunities"
    )
    subject_terms = (
        "accounting", "accountancy", "finance", "financial management", "business",
        "commerce", "management", "audit", "assurance", "tax", "taxation", "cpa",
        "entrepreneurship", "marketing", "strategy", "supply chain", "mba"
    )
    teaching_terms = (
        "professor", "lecturer", "instructor", "sessional", "adjunct", "teaching",
        "faculty", "academic appointment", "open learning", "associate faculty"
    )

    source = any(x in q for x in source_terms)
    subject = any(x in q for x in subject_terms)
    teaching = any(x in q for x in teaching_terms)

    if source and (subject or teaching or "view positions" in q or "current openings" in q):
        return "source"

    return ""


def section_jobs_from_html(url, html):
    """Extract Waterloo-style jobs with surrounding metadata, including deadlines.

    University employment pages often place the deadline in a paragraph or
    list after the main heading, sometimes separated by one or more wrapper
    elements.  v4.1 stopped at the next heading and could therefore lose the
    deadline.  We collect the current section plus a small metadata window.
    """
    soup = BeautifulSoup(html, "html.parser")
    out = []
    headings = soup.find_all(["h1", "h2", "h3", "h4"])

    appointment_re = re.compile(
        r"\b(?:probationary\s+)?(?:assistant|associate|full|term)\s+professor\b|"
        r"\b(?:sessional|contract|course)\s+(?:lecturer|instructor)\b|"
        r"\bteaching\s+stream\b",
        re.I,
    )

    for h in headings:
        title = clean(h.get_text(" ", strip=True))
        if not title or len(title) > 320 or not appointment_re.search(title):
            continue

        parts = []
        node = h
        steps = 0
        deadline_seen = False

        # Walk forward through document siblings/elements. Keep the local
        # section and stop at the next appointment heading. We intentionally
        # retain metadata blocks that can sit just beyond the immediate section.
        for sibling in h.next_elements:
            if sibling is h:
                continue
            if getattr(sibling, "name", None) in ("h1", "h2", "h3", "h4"):
                other = clean(sibling.get_text(" ", strip=True))
                if other and sibling is not h:
                    if appointment_re.search(other):
                        break
                    # Non-job headings can be page navigation; don't terminate
                    # the section on those alone.
            if getattr(sibling, "name", None) in ("script", "style", "noscript"):
                continue
            text = clean(sibling.get_text(" ", strip=True)) if hasattr(sibling, "get_text") else clean(str(sibling))
            if not text:
                continue
            if text in parts[-3:]:
                continue
            parts.append(text)
            steps += 1
            if re.search(r"(?:application\s+deadline|deadline|closing\s+date|apply\s+by|applications\s+close)", text, re.I):
                deadline_seen = True
            if deadline_seen and steps > 80:
                break
            if steps > 180:
                break

        body = clean(" ".join(parts))

        # Prefer a compact body and guarantee that deadline/application text
        # survives extraction when present anywhere in the page.
        if len(body) < 120:
            continue

        # The page may use labelled metadata outside the heading's immediate
        # subtree. Search the full page text and append only the relevant lines.
        page_text = clean(soup.get_text(" ", strip=True))
        metadata = []
        for m in re.finditer(
            r"(?:application\s+deadline|deadline|closing\s+date|apply\s+by|applications\s+close)[^.]{0,180}",
            page_text,
            re.I,
        ):
            metadata.append(clean(m.group(0)))
            if len(metadata) >= 3:
                break

        if metadata:
            body += " " + " ".join(metadata)

        out.append((url, title, body))

    # Deduplicate repeated responsive/mobile headings.
    seen = set()
    result = []
    for item in out:
        key = (item[1].lower(), item[0])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def apply(crawler):
    """Monkey-patch v4.1 and return the patched module."""
    crawler.VERSION = "4.2"
    crawler.links = links
    crawler.discovery_link_kind = discovery_link_kind
    crawler.section_jobs_from_html = section_jobs_from_html
    return crawler
