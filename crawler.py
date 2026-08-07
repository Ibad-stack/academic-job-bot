"""
Academic Job Bot
Version 0.4

Main entry point.
"""

from utils.institution_loader import load_institutions
from utils.downloader import download
from utils.platform_detector import detect_platform
from utils.link_extractor import extract_links
from utils.job_filter import filter_job_links
from utils.job_checker import is_job_posting
from utils.csv_writer import write_jobs


def print_header():
    print()
    print("=" * 80)
    print(" Academic Job Bot ")
    print("=" * 80)
    print()

def check_institution(institution):

    print("=" * 80)
    print(institution.institution)
    print("=" * 80)

    result = download(institution.career_page)

    if not result["success"]:
        print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
        print()
        return []

    platform = detect_platform(
        result["html"],
        result["url"]
    )

    print(f"Platform : {platform}")

    links = extract_links(
        result["html"],
        result["url"]
    )

    print(f"Links Found : {len(links)}")

    candidate_links = filter_job_links(links)

    print(f"Potential Job Links : {len(candidate_links)}")

    jobs = []

    for candidate in candidate_links:

        job = {
            "institution": institution.institution,
            "title": candidate["text"].strip(),
            "url": candidate["url"]
        }

        jobs.append(job)

        print("✓ Possible Job")
        print(f"Title : {job['title']}")
        print(f"URL   : {job['url']}")
        print()

    if len(jobs) == 0:
        print("No possible jobs found.")

    print()

    return jobs

def main():

    print_header()

    institutions = load_institutions()

    print(f"Searching {len(institutions)} institutions...")
    print()

    all_jobs = []

    for institution in institutions:

        jobs = check_institution(institution)

        all_jobs.extend(jobs)

    print()
    print("=" * 80)
    print(" SUMMARY ")
    print("=" * 80)
    print()

    print(f"Total Jobs Found : {len(all_jobs)}")
    print()

    if all_jobs:

        for job in all_jobs:

            print(job["institution"])
            print(job["title"])
            print(job["url"])
            print()

    else:

        print("No teaching jobs found.")

    # Save results to CSV
    write_jobs(all_jobs)

    print()
    print("=" * 80)
    print(" Finished ")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()