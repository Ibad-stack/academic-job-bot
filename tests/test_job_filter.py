import unittest

from utils.job_filter import filter_job_links


class JobFilterTests(unittest.TestCase):
    def test_career_url_does_not_hide_real_posting(self):
        links = [
            {
                "text": "Assistant Professor, Accounting",
                "url": "https://example.edu/careers/assistant-professor-accounting",
            }
        ]

        results = filter_job_links(links)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Assistant Professor, Accounting")

    def test_common_academic_postings_are_detected(self):
        links = [
            {
                "text": "Associate Faculty - Accounting",
                "url": "https://ourpeople.royalroads.ca/careers/associate-faculty-accounting",
            },
            {
                "text": "Dean, Faculty of Business",
                "url": "https://www.athabascau.ca/careers/dean-faculty-of-business.html",
            },
            {
                "text": "Open Learning Faculty Member (Web): ACCT 123",
                "url": "https://tru.hua.hrsmart.com/hr/ats/Posting/view/12345",
            },
        ]

        results = filter_job_links(links)

        self.assertEqual(len(results), 3)

    def test_navigation_links_are_not_jobs(self):
        links = [
            {
                "text": "Current Openings",
                "url": "https://example.edu/careers/current-openings",
            },
            {
                "text": "Faculty Positions",
                "url": "https://example.edu/careers/faculty.html",
            },
            {
                "text": "How to Apply",
                "url": "https://example.edu/careers/how-to-apply",
            },
        ]

        self.assertEqual(filter_job_links(links), [])


if __name__ == "__main__":
    unittest.main()
