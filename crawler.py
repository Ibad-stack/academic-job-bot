"""
Academic Job Bot
Simple personal job finder.

Version 1.2

- Searches institutional career pages
- Follows relevant career/job pages
- Recognizes TRU HRSmart/Deltek job systems
- Extracts actual job posting links
- Saves results to jobs_found.csv
"""

import re

from utils.institution_loader import load_institutions
from utils.downloader import download
from utils.link_extractor import extract_links
from utils.job_filter import filter_job_links
from utils.csv_writer import write_jobs


CAREER_PAGE_WORDS = [
    "open learning",
    "current openings",
    "job postings",
    "job opportunities",
    "faculty positions",
    "faculty opportunities",
    "academic positions",
    "academic opportunities",
    "associate faculty",
    "contract faculty",
    "part-time faculty",
    "part time faculty",
    "adjunct",
    "sessional",
    "instructor positions",
    "faculty openings",
    "teaching opportunities",
]


def print_header():
    print()
    print("=" * 80)
    print(" Academic Job Bot ")
    print("=" * 80)
    print()


def looks_like_career_page(link):

    text = link.get("text", "").lower()
    url = link.get("url", "").lower()

    searchable = text + " " + url

    return any(
        word in searchable
        for word in CAREER_PAGE_WORDS
    )


def is_tru_hrsmart(url):

    return (
        "tru.hua.hrsmart.com" in url.lower()
        and "/hr/ats/" in url.lower()
    )


def extract_tru_postings(html):

    """
    Extract TRU HRSmart posting IDs from the page.

    Example:

    /hr/ats/Posting/view/28086

    becomes:

    https://tru.hua.hrsmart.com/hr/ats/Posting/view/28086
    """

    pattern = r"/hr/ats/Posting/view/(\d+)"

    matches = re.findall(pattern, html)

    posting_ids = []

    for posting_id in matches:

        if posting_id not in posting_ids:
            posting_ids.append(posting_id)

    jobs = []

    for posting_id in posting_ids:

        jobs.append(
            {
                "institution": "Thompson Rivers University",
                "title": "TRU Open Learning / Faculty Posting",
                "url": (
                    "https://tru.hua.hrsmart.com"
                    f"/hr/ats/Posting/view/{posting_id}"
                )
            }
        )

    return jobs


def check_institution(institution):

    print("=" * 80)
    print(institution.institution)
    print("=" * 80)

    result = download(institution.career_page)

    if not result["success"]:

        print(
            f"ERROR: HTTP {result.get('status')} - "
            f"{result.get('error')}"
        )

        print()

        return []

    print(f"Page: {result['url']}")
    print(f"HTTP: {result['status']}")

    jobs = []

    # ---------------------------------------------------------
    # SPECIAL CASE: TRU HRSMART
    # ---------------------------------------------------------

    if is_tru_hrsmart(result["url"]):

        print("Detected TRU HRSmart job system.")

        jobs = extract_tru_postings(
            result["html"]
        )

        print(
            f"TRU postings found: {len(jobs)}"
        )

        for job in jobs:

            print()
            print(f"• {job['title']}")
            print(f"  {job['url']}")

        print()

        return jobs

    # ---------------------------------------------------------
    # LEVEL 1
    # ---------------------------------------------------------

    links = extract_links(
        result["html"],
        result["url"]
    )

    print(
        f"Level 1 links: {len(links)}"
    )

    # ---------------------------------------------------------
    # FIND SECOND-LEVEL CAREER PAGES
    # ---------------------------------------------------------

    second_level_pages = []

    for link in links:

        if looks_like_career_page(link):

            second_level_pages.append(link)

    # Remove duplicate URLs.

    unique_pages = []
    seen = set()

    for link in second_level_pages:

        url = link["url"]

        if url not in seen:

            seen.add(url)
            unique_pages.append(link)

    print(
        f"Career/job pages to inspect: "
        f"{len(unique_pages)}"
    )

    # ---------------------------------------------------------
    # LEVEL 2
    # ---------------------------------------------------------

    for page_link in unique_pages[:10]:

        print()
        print(
            f"Checking: "
            f"{page_link['text'].strip()}"
        )

        print(
            page_link["url"]
        )

        page = download(
            page_link["url"]
        )

        if not page["success"]:

            print(
                f"Could not download "
                f"(HTTP {page.get('status')})"
            )

            continue

        # -----------------------------------------------------
        # TRU HRSMART MAY APPEAR AT LEVEL 2
        # -----------------------------------------------------

        if is_tru_hrsmart(page["url"]):

            print(
                "Detected TRU HRSmart job system."
            )

            tru_jobs = extract_tru_postings(
                page["html"]
            )

            print(
                f"TRU postings found: "
                f"{len(tru_jobs)}"
            )

            jobs.extend(tru_jobs)

            continue

        # -----------------------------------------------------
        # NORMAL HTML PAGE
        # -----------------------------------------------------

        second_links = extract_links(
            page["html"],
            page["url"]
        )

        print(
            f"Links on page: "
            f"{len(second_links)}"
        )

        candidate_links = filter_job_links(
            second_links
        )

        print(
            f"Relevant job links: "
            f"{len(candidate_links)}"
        )

        for candidate in candidate_links:

            title = candidate["text"].strip()

            if not title:
                continue

            job = {
                "institution": institution.institution,
                "title": title,
                "url": candidate["url"]
            }

            if any(
                existing["url"] == job["url"]
                for existing in jobs
            ):
                continue

            jobs.append(job)

            print()
            print(
                f"✓ {job['title']}"
            )

            print(
                f"  {job['url']}"
            )

    print()
    print(
        f"Total possible jobs found: "
        f"{len(jobs)}"
    )

    print()

    return jobs


def main():

    print_header()

    institutions = load_institutions()

    print(
        f"Searching "
        f"{len(institutions)} institutions..."
    )

    print()

    all_jobs = []

    for institution in institutions:

        jobs = check_institution(
            institution
        )

        all_jobs.extend(jobs)

    # ---------------------------------------------------------
    # REMOVE DUPLICATES
    # ---------------------------------------------------------

    unique_jobs = []
    seen_urls = set()

    for job in all_jobs:

        if job["url"] in seen_urls:
            continue

        seen_urls.add(job["url"])
        unique_jobs.append(job)

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print()

    print(
        f"Total possible jobs: "
        f"{len(unique_jobs)}"
    )

    print()

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------

    write_jobs(unique_jobs)

    print()
    print("Finished.")
    print()


if __name__ == "__main__":
    main()