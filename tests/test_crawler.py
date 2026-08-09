import unittest
from unittest.mock import patch

from crawler import extract_tru_postings, looks_like_career_page, check_institution
from models.institution import Institution


class CrawlerTests(unittest.TestCase):
    def test_tru_postings_keep_anchor_titles(self):
        html = """
        <html>
          <body>
            <a href="https://tru.hua.hrsmart.com/hr/ats/Posting/view/28086">
              Open Learning Faculty Member (Web): NRSC 3201: Silviculture - (03027.494)
            </a>
            <a href="/hr/ats/Posting/view/28087">Open Learning Faculty Member (Web): ACCT 101</a>
          </body>
        </html>
        """

        jobs = extract_tru_postings(html)

        self.assertEqual(len(jobs), 2)
        self.assertIn("NRSC 3201", jobs[0]["title"])
        self.assertEqual(
            jobs[1]["url"],
            "https://tru.hua.hrsmart.com/hr/ats/Posting/view/28087",
        )

    def test_embedded_job_board_is_a_crawl_target(self):
        link = {
            "text": "Embedded career/job board",
            "url": "https://jobs.example.com/board",
            "type": "iframe",
        }

        self.assertTrue(looks_like_career_page(link))

    @patch("crawler.download")
    def test_initial_page_direct_job_links_are_collected(self, mock_download):
        institution = Institution(
            institution="Test University",
            country="Canada",
            platform="Custom",
            career_page="https://example.edu/careers",
            priority=1,
        )

        mock_download.return_value = {
            "success": True,
            "status": 200,
            "url": "https://example.edu/careers",
            "html": """
                <a href="/careers/assistant-professor-accounting">
                    Assistant Professor, Accounting
                </a>
            """,
        }

        jobs = check_institution(institution)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Assistant Professor, Accounting")
        self.assertEqual(
            jobs[0]["url"],
            "https://example.edu/careers/assistant-professor-accounting",
        )


if __name__ == "__main__":
    unittest.main()
