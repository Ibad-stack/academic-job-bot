"""
Academic Job Bot
Crawls institutional academic-career pages and extracts relevant teaching jobs.

Version 2.0
"""

import re
from collections import deque
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from utils.institution_loader import load_institutions
from utils.downloader import download
from utils.link_extractor import extract_links
from utils.job_filter import filter_job_links
from utils.csv_writer import write_jobs


MAX_CRAWL_DEPTH = 2
MAX_CRAWL_PAGES = 30

CAREER_PAGE_WORDS = (
    "open learning",
    "current openings",
    "current opportunities",
    "job postings",
    "job opportunities",
    "employment opportunities",
    "faculty positions",
    "faculty opportunities",
    "faculty & instructors",
    "academic positions",
    "academic opportunities",
    "associate faculty",
    "contract faculty",
    "part-time faculty",
    "part time faculty",
    "adjunct opportunities",
    "sessional opportunities",
    "instructor positions",
    "faculty openings",
    "teaching opportunities",
    "view all available jobs",
    "view positions",
)

EMBEDDED_JOB_URL_HINTS = (
    "job",
    "career",
    "workday",
    "dayforce",
    "interfolio",
    "talent",
    "recruit",
    "ats",
)

TRU_HOST = "tru.hua.hrsmart.com"
TRU_POSTING_RE = re.compile(r"/hr/ats/Posting/view/(\d+)", re.IGNORECASE)


def print_header():
    print()
    print("=" * 80)
    print(" Academic Job Bot ")
    print("=" * 80)
    print()


def looks_like_career_page(link):
    text = link.get("text", "").lower()
    url = link.get("url", "").lower()

    if link.get("type") == "iframe":
        return any(hint in url for hint in EMBEDDED_JOB_URL_HINTS)

    searchable = f"{text} {url}"
    return any(word in searchable for word in CAREER_PAGE_WORDS)


def is_tru_hrsmart(url):
    parsed = urlparse(url)
    return (
        parsed.hostname
        and parsed.hostname.lower() == TRU_HOST
        and "/hr/ats/" in parsed.path.lower()
    )


def is_tru_posting(url):
    if not is_tru_hrsmart(url):
        return False
    return TRU_POSTING_RE.search(urlparse(url).path) is not None


def _title_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for selector in ("h1", "h2", "title"):
        node = soup.select_one(selector)
        if not node:
            continue

        title = node.get_text(" ", strip=True)
        if not title:
            continue

        title = re.sub(
            r"^Deltek Talent Management\s*-\s*",
            "",
            title,
            flags=re.IGNORECASE,
        )
        return title.strip()

    return ""


def extract_tru_postings(html):
    """Extract TRU HRSmart posting links and their anchor titles."""

    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        match = TRU_POSTING_RE.search(href)
        if not match:
            continue

        posting_id = match.group(1)
        url = f"https://{TRU_HOST}/hr/ats/Posting/view/{posting_id}"

        if url in seen:
            continue

        seen.add(url)
        title = (
            anchor.get_text(" ", strip=True)
            or "TRU Open Learning / Faculty Posting"
        )

        jobs.append({
            "institution": "Thompson Rivers University",
            "title": title,
            "url": url,
        })

    # Fallback for HTML/JS that contains posting URLs without anchors.
    for posting_id in TRU_POSTING_RE.findall(html):
        url = f"https://{TRU_HOST}/hr/ats/Posting/view/{posting_id}"
        if url in seen:
            continue

        seen.add(url)
        jobs.append({
            "institution": "Thompson Rivers University",
            "title": "TRU Open Learning / Faculty Posting",
            "url": url,
        })

    return jobs


def _add_job(jobs, seen_urls, institution_name, title, url):
    title = re.sub(r"\s+", " ", title or "").strip()
    url = url.strip()

    if not title or not url or url in seen_urls:
        return False

    jobs.append({
        "institution": institution_name,
        "title": title,
        "url": url,
    })
    seen_urls.add(url)
    return True


def _enrich_tru_job(job):
    if "TRU Open Learning / Faculty Posting" not in job["title"]:
        return job

    page = download(job["url"])
    if page["success"]:
        title = _title_from_html(page["html"])
        if title:
            job["title"] = title

    return job


def check_institution(institution):
    print("=" * 80)
    print(institution.institution)
    print("=" * 80)

    jobs = []
    seen_job_urls = set()
    visited_pages = set()
    queued_pages = {institution.career_page}
    queue = deque([(institution.career_page, 0)])

    while queue and len(visited_pages) < MAX_CRAWL_PAGES:
        page_url, depth = queue.popleft()

        if page_url in visited_pages:
            continue

        visited_pages.add(page_url)

        print()
        print(f"Checking depth {depth}: {page_url}")

        page = download(page_url)
        if not page["success"]:
            print(
                f"Could not download (HTTP {page.get('status')}): "
                f"{page.get('error')}"
            )
            continue

        final_url = page["url"]
        visited_pages.add(final_url)
        print(f"HTTP: {page['status']}")

        # A direct TRU posting is itself a job.
        if is_tru_posting(final_url):
            title = (
                _title_from_html(page["html"])
                or "TRU Open Learning / Faculty Posting"
            )
            if _add_job(
                jobs,
                seen_job_urls,
                institution.institution,
                title,
                final_url,
            ):
                print(f"✓ {title}")
            continue

        # TRU listing pages often contain posting URLs that do not behave
        # like normal HTML job links.
        if is_tru_hrsmart(final_url):
            tru_jobs = extract_tru_postings(page["html"])
            for job in tru_jobs:
                job["institution"] = institution.institution
                job = _enrich_tru_job(job)
                if _add_job(
                    jobs,
                    seen_job_urls,
                    job["institution"],
                    job["title"],
                    job["url"],
                ):
                    print(f"✓ {job['title']}")
            continue

        links = extract_links(page["html"], final_url)
        print(f"Links found: {len(links)}")

        # First inspect direct job links on the current page. The old crawler
        # only inspected links after navigating to a second-level career page,
        # which caused sites such as Athabasca to be skipped entirely.
        for candidate in filter_job_links(links):
            title = candidate["text"]
            url = candidate["url"]

            if is_tru_posting(url):
                candidate_job = {
                    "institution": institution.institution,
                    "title": title,
                    "url": url,
                }
                candidate_job = _enrich_tru_job(candidate_job)
                title = candidate_job["title"]
                url = candidate_job["url"]

            if _add_job(
                jobs,
                seen_job_urls,
                institution.institution,
                title,
                url,
            ):
                print(f"✓ {title}")
                print(f"  {url}")

        # Follow only links that look like career/job-listing pages. This
        # keeps the crawler focused while allowing two levels of navigation.
        if depth >= MAX_CRAWL_DEPTH:
            continue

        for link in links:
            if not looks_like_career_page(link):
                continue

            next_url = link["url"].strip()
            if not next_url or next_url in visited_pages or next_url in queued_pages:
                continue

            queued_pages.add(next_url)
            queue.append((next_url, depth + 1))

    print()
    print(f"Pages inspected: {len(visited_pages)}")
    print(f"Total possible jobs found: {len(jobs)}")
    print()

    return jobs


def main():
    print_header()

    institutions = load_institutions()
    print(f"Searching {len(institutions)} institutions...")
    print()

    all_jobs = []

    for institution in institutions:
        all_jobs.extend(check_institution(institution))

    unique_jobs = []
    seen_urls = set()

    for job in all_jobs:
        if job["url"] in seen_urls:
            continue

        seen_urls.add(job["url"])
        unique_jobs.append(job)

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total possible jobs: {len(unique_jobs)}")
    print()

    write_jobs(unique_jobs)

    print()
    print("Finished.")
    print()


if __name__ == "__main__":
    main()
